"""
战略目标追踪 — V2
进度测算 + KPI 分解树贡献归因 + 多维 What-if 情景模拟 + 目标缺口反推
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from modules import finance_core as fc
from modules.data_loader import get_strategy
from config import C

_DASH = "—"


def _f(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):,.{dec}f}"


def _p(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):.{dec}f}%"


def _sg(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):+,.{dec}f}"


# ════════════════════════════════════════════════════════════
# 进度
# ════════════════════════════════════════════════════════════
def progress(targets: list, time_progress: float = 50.0) -> list:
    out = []
    for t in targets:
        cur, tgt = t.get("current_value"), t.get("target_value")
        if cur is None or tgt in (None, 0):
            out.append({**t, "progress": None, "status": "na", "gap": None})
            continue
        lower_better = t.get("lower_better", False)
        if lower_better:
            # 越低越好：完成度 = 目标/当前（不超过100）
            prog = min(tgt / cur * 100, 100) if cur else None
        else:
            prog = min(cur / tgt * 100, 100)
        gap = tgt - cur
        if prog is None:
            status = "na"
        elif lower_better:
            status = "normal" if cur <= tgt else ("warning" if cur <= tgt * 1.1 else "danger")
        else:
            if prog >= time_progress + 10:
                status = "normal"
            elif prog >= time_progress - 8:
                status = "warning"
            else:
                status = "danger"
        out.append({**t, "progress": prog, "status": status, "gap": gap})
    return out


def progress_chart(data: list, time_progress: float = 50.0, height=300) -> go.Figure:
    names = [d["name"][:18] for d in data]
    vals = [(d["progress"] or 0) for d in data]
    colors = {"normal": C["good"], "warning": C["warn"], "danger": C["bad"],
              "na": C["faint"]}
    fig = go.Figure(go.Bar(
        y=names, x=vals, orientation="h",
        marker_color=[colors.get(d["status"], C["accent"]) for d in data],
        text=[f"{v:.0f}%" for v in vals], textposition="outside",
        textfont=dict(size=11)))
    fig.add_vline(x=time_progress, line_dash="dash", line_color=C["primary"],
                  annotation_text=f"时间进度 {time_progress:.0f}%",
                  annotation_font=dict(size=10, color=C["primary"]))
    fig.update_layout(
        xaxis=dict(range=[0, 118], title="完成率(%)"),
        height=max(240, 40 * len(data) + 90), margin=dict(l=8, r=30, t=10, b=34),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Source Han Sans SC, Microsoft YaHei, sans-serif", size=12,
                  color=C["text2"]),
        showlegend=False,
    )
    return fig


def kpi_tree_gap(target: dict) -> pd.DataFrame:
    """
    KPI 分解树：按权重把目标缺口归因到子指标
    """
    tree = target.get("kpi_tree", {}) or {}
    rows = []
    for name, info in tree.items():
        cur, tgt, w = info.get("current"), info.get("target"), info.get("weight", 0)
        sub_prog = (cur / tgt) if (cur is not None and tgt) else None
        rows.append({
            "子指标": name, "权重": w, "当前": cur, "目标": tgt,
            "子目标完成率(%)": (sub_prog * 100) if sub_prog is not None else None,
            "缺口": None if (cur is None or tgt is None) else tgt - cur,
            "加权缺口贡献": None if (cur is None or tgt is None)
                            else (tgt - cur) * w,
            "状态": "na" if sub_prog is None else (
                "normal" if sub_prog >= 1 else ("warning" if sub_prog >= 0.85 else "danger")),
        })
    df = pd.DataFrame(rows)
    if not df.empty and df["加权缺口贡献"].notna().any():
        df = df.sort_values("加权缺口贡献", key=lambda s: s.abs(), ascending=False)
    return df


# ════════════════════════════════════════════════════════════
# 多维 What-if 情景模拟
# ════════════════════════════════════════════════════════════
def what_if(model: dict, d_rev=0.0, d_gm=0.0, d_fee_rate=0.0,
            d_dso=0.0, d_debt=0.0, tax_rate=None) -> dict:
    """
    d_rev:      收入变动 %
    d_gm:       毛利率变动 pp
    d_fee_rate: 期间费用率变动 pp（负=降费）
    d_dso:      DSO 变动天数（正=延长）
    d_debt:     有息负债变动（亿元）
    """
    i = model["n"] - 1
    rev = model["revenue"][i] or 0
    gm = model["gross_margin"][i] or 0
    ebit = model["ebit"][i] or 0
    ni = model["net_profit"][i] or 0
    equity = model["equity"][i] or 0
    ibd = model["ibd"][i] or 0
    interest = model["interest"][i] or 0
    ocf = model["ocf"][i] or 0
    capex = model["capex"][i] or 0
    pretax = model["pretax"][i]
    tax = model["tax"][i]
    cash = model["cash"][i]

    if tax_rate is None:
        tax_rate = (tax / pretax) if (pretax and tax is not None) else 0.15
    tax_rate = float(np.clip(tax_rate, 0.0, 0.40))

    ol = fc.operating_leverage(model)
    cmr = (ol.get("cmr") / 100) if ol.get("ok") and ol.get("cmr") else (gm / 100)

    new_rev = rev * (1 + d_rev / 100)
    new_gp = new_rev * ((gm + d_gm) / 100)
    d_gp = new_gp - rev * (gm / 100)
    d_fee = new_rev * (d_fee_rate / 100)
    new_ebit = ebit + d_gp - d_fee
    new_ibd = ibd + d_debt
    rate = (interest / ibd) if ibd else 0.05
    new_interest = new_ibd * rate
    new_ni = (new_ebit - new_interest) * (1 - tax_rate)
    new_roe = new_ni / equity * 100 if equity else None
    occ = rev / 365 * max(d_dso, 0)
    new_cash = (cash or 0) - occ
    new_fcf = (ocf + (new_ni - ni) * 0.6) - capex
    new_ic = new_ebit / new_interest if new_interest else None

    return {
        "基准": {"营业收入": rev, "毛利率(%)": gm, "EBIT": ebit, "净利润": ni,
                 "ROE(%)": (ni / equity * 100) if equity else None,
                 "自由现金流": ocf - capex, "利息保障倍数": (ebit / interest) if interest else None,
                 "现金": cash},
        "模拟": {"营业收入": new_rev, "毛利率(%)": gm + d_gm, "EBIT": new_ebit,
                 "净利润": new_ni, "ROE(%)": new_roe, "自由现金流": new_fcf,
                 "利息保障倍数": new_ic, "现金": new_cash},
        "变动": {"营业收入": new_rev - rev, "毛利率(%)": d_gm, "EBIT": new_ebit - ebit,
                 "净利润": new_ni - ni,
                 "ROE(%)": (new_roe - (ni / equity * 100)) if (equity and new_roe is not None) else None,
                 "自由现金流": new_fcf - (ocf - capex),
                 "现金": new_cash - (cash or 0)},
        "assumption": {"边际贡献率": cmr * 100, "所得税率": tax_rate * 100,
                       "债务利率": rate * 100, "资金成本": 5.0},
    }


def what_if_rows(res: dict) -> pd.DataFrame:
    keys = ["营业收入", "毛利率(%)", "EBIT", "净利润", "ROE(%)", "利息保障倍数",
            "自由现金流", "现金"]
    rows = []
    for k in keys:
        b, s, d = res["基准"].get(k), res["模拟"].get(k), res["变动"].get(k)
        rows.append({"指标": k, "基准": b, "模拟情景": s, "变动": d,
                     "变动率(%)": (d / abs(b) * 100) if (b and d is not None) else None})
    return pd.DataFrame(rows)


# ════════════════════════════════════════════════════════════
# 目标缺口反推：要达成目标，还需要在哪些方面改善
# ════════════════════════════════════════════════════════════
def gap_actions(model: dict, target: dict) -> str:
    cur, tgt = target.get("current_value"), target.get("target_value")
    unit = target.get("unit", "")
    if cur is None or tgt is None:
        return "数据不足，无法测算缺口。"
    gap = tgt - cur
    rev = fc._last(model["revenue"]) or 0
    gm = fc._last(model["gross_margin"]) or 0
    name = target.get("name", "")
    if "ROE" in name:
        equity = fc._last(model["equity"]) or 1
        need_ni = tgt / 100 * equity
        cur_ni = fc._last(model["net_profit"]) or 0
        d_ni = need_ni - cur_ni
        need_gm = gm + (d_ni / rev * 100) if rev else None
        return (f"当前 ROE {_p(cur)}，目标 {_p(tgt)}，缺口 {_sg(gap)}pp。"
                f"按当前权益规模 {_f(equity)} 亿元测算，需净利润达到 {_f(need_ni)} 亿元"
                f"（当前 {_f(cur_ni)} 亿元，缺口 {_f(d_ni)} 亿元）。"
                f"若仅通过毛利率改善实现，需毛利率从 {_p(gm)} 提升至 {_p(need_gm)}（+{_f(d_ni/rev*100 if rev else None,2)}pp）；"
                f"也可通过提升周转率或优化资本结构分担。")
    if "收入" in name:
        return (f"当前 {_f(cur)} {unit}，目标 {_f(tgt)} {unit}，缺口 {_f(gap)} {unit}"
                f"（需增长 {_p(gap/cur*100 if cur else None)}）。"
                + (f"按当前毛利率 {_p(gm)}，达成后增量毛利约 {_f(gap*gm/100)} 亿元。" if gap else ""))
    if "现金流" in name:
        ni = fc._last(model["net_profit"]) or 0
        ocf = fc._last(model["ocf"]) or 0
        need_ocf = tgt * ni
        return (f"当前经营现金流/净利润 {_f(cur)}，目标 {_f(tgt)}。按当前净利润 {_f(ni)} 亿元，"
                f"经营现金流需达到 {_f(need_ocf)} 亿元（当前 {_f(ocf)} 亿元，缺口 {_f(need_ocf-ocf)} 亿元），"
                f"主要通过压缩应收与存货占用实现。")
    if "负债率" in name:
        assets = fc._last(model["assets"])
        liab = fc._last(model["liab"])
        if assets and liab is not None:
            need_liab = tgt / 100 * assets
            return (f"当前资产负债率 {_p(cur)}，目标 {_p(tgt)}。"
                    f"在总资产 {_f(assets)} 亿元不变的情况下，总负债需从 {_f(liab)} 亿元降至 {_f(need_liab)} 亿元"
                    f"（压降 {_f(liab-need_liab)} 亿元），或通过增资扩股做大分母。")
    return f"当前 {_f(cur)}{unit}，目标 {_f(tgt)}{unit}，缺口 {_sg(gap)}{unit}。"
