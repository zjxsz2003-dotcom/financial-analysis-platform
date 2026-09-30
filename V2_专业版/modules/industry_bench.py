"""
行业对标 — V2（通用化）
不再硬编码单一行业：支持切换行业预设、自定义基准、上传同业数据做分位排名
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from modules import finance_core as fc
from modules.data_loader import (get_industry_benchmarks, get_industry_name,
                                 get_peer_data)
from config import C

_DASH = "—"


def _f(v, dec=2):
    return _DASH if v is None or v != v else f"{float(v):,.{dec}f}"


def benchmark_records(snap: dict) -> list:
    """生成对标记录"""
    out = []
    for dim, items in snap.items():
        for key, d in items.items():
            out.append({
                "dim": dim, "name": d["name"], "unit": d["unit"],
                "cur": d["current"], "bench": d["bench"],
                "diff": d["diff"], "better": d["better"],
                "pct": (d["diff"] / abs(d["bench"]) * 100)
                        if (d["diff"] is not None and d["bench"]) else None,
                "dec": d["dec"], "status": d["status"],
                "values": d["values"],
            })
    return out


def radar_scores(snap: dict) -> tuple:
    """
    把各指标折算成 0-100 的相对得分（50 = 与基准持平），方向敏感
    返回 (维度名, 本公司得分, 基准得分)
    """
    dims = list(snap.keys())
    comp, base = [], []
    for dim in dims:
        vs, bs = [], []
        for key, d in snap[dim].items():
            if d["current"] is None or d["bench"] is None:
                continue
            b = abs(d["bench"]) or 1
            rel = (d["current"] - d["bench"]) / b * 100     # 相对偏离 %
            s = 50 + np.clip(rel * (1 if d["direction"] > 0 else -1), -50, 50) / 2
            vs.append(float(s))
            bs.append(50.0)
        comp.append(float(np.mean(vs)) if vs else 0.0)
        base.append(50.0)
    return dims, comp, base


def radar_chart(snap: dict, height=340) -> go.Figure:
    dims, comp, base = radar_scores(snap)
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=comp + [comp[0]], theta=dims + [dims[0]], fill="toself", name="本公司",
        line=dict(color=C["primary"], width=2), fillcolor="rgba(27,79,138,0.18)"))
    fig.add_trace(go.Scatterpolar(
        r=base + [base[0]], theta=dims + [dims[0]], fill="toself", name="行业基准(50)",
        line=dict(color=C["accent_l"], width=1.6, dash="dash"),
        fillcolor="rgba(91,155,213,0.10)"))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], gridcolor=C["line2"],
                                   tickfont=dict(size=10)),
                   angularaxis=dict(tickfont=dict(size=11.5, color=C["text"]))),
        showlegend=True, height=height, margin=dict(l=40, r=40, t=26, b=34),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.14, font=dict(size=11)),
        font=dict(family="Source Han Sans SC, Microsoft YaHei, sans-serif", size=12,
                  color=C["text2"]),
    )
    return fig


def scatter_vs_bench(snap: dict, height=300) -> go.Figure:
    """偏离度条形图：相对行业基准的偏离 %"""
    rows = []
    for dim, items in snap.items():
        for key, d in items.items():
            if d["current"] is None or d["bench"] is None or not d["bench"]:
                continue
            rel = (d["current"] - d["bench"]) / abs(d["bench"]) * 100
            rel = rel * (1 if d["direction"] > 0 else -1)
            rows.append({"name": d["name"], "rel": rel, "dim": dim})
    if not rows:
        return go.Figure()
    df = pd.DataFrame(rows).sort_values("rel")
    colors = [C["good"] if v >= 0 else C["bad"] for v in df["rel"]]
    fig = go.Figure(go.Bar(y=df["name"], x=df["rel"], orientation="h",
                           marker_color=colors,
                           text=[f"{v:+.0f}%" for v in df["rel"]],
                           textposition="outside", textfont=dict(size=10)))
    fig.add_vline(x=0, line_color=C["muted"], line_width=1)
    fig.update_layout(
        xaxis=dict(title="相对行业基准（正=优于基准）", zeroline=True,
                   zerolinecolor=C["line"]),
        height=max(280, 26 * len(df) + 80), margin=dict(l=8, r=30, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Source Han Sans SC, Microsoft YaHei, sans-serif", size=11.5,
                  color=C["text2"]),
    )
    return fig


def peer_percentile(peer_df: pd.DataFrame, snap: dict) -> Optional[pd.DataFrame]:
    """
    若上传了同业数据，计算本公司分位排名。
    peer_df 期望列：'公司' + 指标名（与 KPI_META 中文名一致）
    """
    if peer_df is None or peer_df.empty:
        return None
    name_col = None
    for c in peer_df.columns:
        if str(c).strip() in ("公司", "公司名称", "名称", "证券简称"):
            name_col = c
            break
    if name_col is None:
        return None
    rows = []
    for dim, items in snap.items():
        for key, d in items.items():
            col = None
            for c in peer_df.columns:
                if str(c).strip() == d["name"] or str(c).strip() == key:
                    col = c
                    break
            if col is None or d["current"] is None:
                continue
            vals = pd.to_numeric(peer_df[col], errors="coerce").dropna()
            if len(vals) < 2:
                continue
            pct_rank = float((vals < d["current"]).sum()) / len(vals) * 100
            if d["direction"] < 0:
                pct_rank = 100 - pct_rank
            rows.append({
                "维度": dim, "指标": d["name"], "本公司": d["current"],
                "同业中位数": float(vals.median()), "同业均值": float(vals.mean()),
                "同业家数": len(vals), "分位(%)": pct_rank,
            })
    return pd.DataFrame(rows) if rows else None


def industry_summary(snap: dict) -> dict:
    """总体对标结论：优于/低于基准的指标数量与最突出项"""
    better, worse = [], []
    for dim, items in snap.items():
        for key, d in items.items():
            if d["better"] is True:
                better.append((d["name"], d["diff"], d["unit"]))
            elif d["better"] is False:
                worse.append((d["name"], d["diff"], d["unit"]))
    better.sort(key=lambda x: abs(x[1]) if x[1] else 0, reverse=True)
    worse.sort(key=lambda x: abs(x[1]) if x[1] else 0, reverse=True)
    return {"better": better, "worse": worse,
            "n_better": len(better), "n_worse": len(worse),
            "industry": get_industry_name()}
