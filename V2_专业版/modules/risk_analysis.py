"""
财务风险分析引擎 — V2（全新）
六大风险维度评分 + Altman Z 判别 + 流动性阶梯 + 多情景压力测试 + 风险传导链
"""
from __future__ import annotations
from typing import Optional, Sequence
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from modules import finance_core as fc
from modules.data_loader import get_industry_benchmarks
from config import C, RISK_DIMENSIONS, RISK_LEVELS

_DASH = "—"


def _f(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):,.{dec}f}"


def _p(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):.{dec}f}%"


def _sg(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):+,.{dec}f}"


def _risk_score(v, safe, risky, higher_is_risk: bool = True) -> Optional[float]:
    """
    把指标映射到 0-100 风险分。
    higher_is_risk=True：v<=safe → 0分；v>=risky → 100分
    higher_is_risk=False：v>=safe → 0分；v<=risky → 100分（越高越安全）
    """
    if v is None or v != v or safe == risky:
        return None
    if higher_is_risk:
        if v <= safe:
            return 0.0
        if v >= risky:
            return 100.0
        return (v - safe) / (risky - safe) * 100
    if v >= safe:
        return 0.0
    if v <= risky:
        return 100.0
    return (safe - v) / (safe - risky) * 100


def _agg(items: Sequence[tuple]) -> Optional[float]:
    """items: [(score, weight)]，忽略 None"""
    tot, w = 0.0, 0.0
    for s, wt in items:
        if s is not None:
            tot += s * wt
            w += wt
    return tot / w if w else None


def _trend_penalty(arr: Sequence, worse_when_up: bool = True) -> Optional[float]:
    """趋势恶化加分（0-25）：连续两年恶化 → 更高风险"""
    vals = [v for v in arr if v is not None]
    if len(vals) < 3:
        return None
    d1 = vals[-1] - vals[-2]
    d2 = vals[-2] - vals[-3]
    bad = 0.0
    if worse_when_up:
        if d1 > 0:
            bad += 12.5
        if d2 > 0:
            bad += 6.0
    else:
        if d1 < 0:
            bad += 12.5
        if d2 < 0:
            bad += 6.0
    return bad


# ════════════════════════════════════════════════════════════
# 1. 六大维度风险评分卡
# ════════════════════════════════════════════════════════════
def risk_scorecard(model: dict) -> dict:
    L = lambda k: fc._last(model.get(k, []))
    F = lambda k: fc._prev(model.get(k, []))
    bench = get_industry_benchmarks()

    cr, qr = L("current_ratio"), L("quick_ratio")
    c2sd = L("cash_to_short_debt")
    dr = L("debt_ratio")
    ic = L("interest_cover")
    ibd, ebitda, ocf, ni = L("ibd"), L("ebitda"), L("ocf"), L("net_profit")
    ocf_ni, fcf, capex_i = L("ocf_to_ni"), L("fcf"), L("capex_intensity")
    accr, crr, nonrec = L("accrual_ratio"), L("cash_recovery"), L("nonrecurring_ratio")
    gm_std = fc._pct_std(model["gross_margin"])
    dso, dio, ccc = L("dso"), L("dio"), L("ccc")
    rg, ng = L("rev_growth"), L("np_growth")
    ol = fc.operating_leverage(model)

    # ── 流动性 ──
    liq_items = [
        ("流动比率", _risk_score(cr, 1.6, 1.0, higher_is_risk=False), 0.35, cr, "倍"),
        ("速动比率", _risk_score(qr, 1.0, 0.6, higher_is_risk=False), 0.30, qr, "倍"),
        ("现金/短期有息负债", _risk_score(c2sd, 1.5, 0.6, higher_is_risk=False), 0.35, c2sd, "倍"),
    ]
    liq = _agg([(s, w) for _, s, w, _, _ in liq_items])
    liq = min(100, (liq or 0) + (_trend_penalty(model["current_ratio"], worse_when_up=False) or 0))

    # ── 偿债 ──
    de_ratio = (ibd / ebitda) if (ibd is not None and ebitda not in (None, 0)) else None
    debt_items = [
        ("资产负债率", _risk_score(dr, 50.0, 78.0), 0.35, dr, "%"),
        ("利息保障倍数", _risk_score(ic, 5.0, 1.5, higher_is_risk=False), 0.35, ic, "倍"),
        ("有息负债/EBITDA", _risk_score(de_ratio, 2.0, 5.0), 0.30, de_ratio, "倍"),
    ]
    sol = _agg([(s, w) for _, s, w, _, _ in debt_items])
    sol = min(100, (sol or 0) + (_trend_penalty(model["debt_ratio"], worse_when_up=True) or 0))

    # ── 现金流 ──
    cf_items = [
        ("经营现金流/净利润", _risk_score(ocf_ni, 1.0, 0.3, higher_is_risk=False), 0.30, ocf_ni, "倍"),
        ("自由现金流(亿元)", _risk_score(fcf, 3.0, -10.0, higher_is_risk=False), 0.30, fcf, "亿元"),
        ("资本开支/经营现金流", _risk_score(capex_i, 60.0, 120.0), 0.25, capex_i, "%"),
        ("经营现金流/有息负债", _risk_score((ocf / ibd) if (ocf and ibd) else None,
                                            0.35, 0.12, higher_is_risk=False), 0.15,
         (ocf / ibd) if (ocf and ibd) else None, "倍"),
    ]
    cash = _agg([(s, w) for _, s, w, _, _ in cf_items])

    # ── 盈利质量 ──
    eq_items = [
        ("应计利润率", _risk_score(accr, 1.0, 8.0), 0.28, accr, "%"),
        ("销售收现比", _risk_score(crr, 105.0, 85.0, higher_is_risk=False), 0.24, crr, "%"),
        ("非经常性损益占比", _risk_score(nonrec, 1.0, 15.0), 0.20, nonrec, "%"),
        ("毛利率波动系数", _risk_score(gm_std, 1.5, 12.0), 0.28, gm_std, "%"),
    ]
    qual = _agg([(s, w) for _, s, w, _, _ in eq_items])

    # ── 营运效率 ──
    op_items = [
        ("应收周转天数 DSO", _risk_score(dso, 60.0, 120.0), 0.35, dso, "天"),
        ("存货周转天数 DIO", _risk_score(dio, 60.0, 120.0), 0.30, dio, "天"),
        ("现金转换周期 CCC", _risk_score(ccc, 60.0, 150.0), 0.35, ccc, "天"),
    ]
    oper = _agg([(s, w) for _, s, w, _, _ in op_items])
    oper = min(100, (oper or 0) + (_trend_penalty(model["ccc"], worse_when_up=True) or 0))

    # ── 经营波动 ──
    rev_std = fc._pct_std(model["rev_growth"])
    vol_items = [
        ("收入增速", _risk_score(rg, 5.0, -10.0, higher_is_risk=False), 0.30, rg, "%"),
        ("净利润增速", _risk_score(ng, 5.0, -20.0, higher_is_risk=False), 0.25, ng, "%"),
        ("收入增速波动", _risk_score(rev_std, 30.0, 120.0), 0.20, rev_std, "%"),
        ("经营杠杆 DOL", _risk_score(ol.get("dol") if ol.get("ok") else None, 2.0, 5.0), 0.25,
         ol.get("dol") if ol.get("ok") else None, "倍"),
    ]
    vol = _agg([(s, w) for _, s, w, _, _ in vol_items])

    dims = {
        "流动性风险": {"score": liq, "weight": RISK_DIMENSIONS["流动性风险"], "items": liq_items},
        "偿债风险": {"score": sol, "weight": RISK_DIMENSIONS["偿债风险"], "items": debt_items},
        "现金流风险": {"score": cash, "weight": RISK_DIMENSIONS["现金流风险"], "items": cf_items},
        "盈利质量风险": {"score": qual, "weight": RISK_DIMENSIONS["盈利质量风险"], "items": eq_items},
        "营运效率风险": {"score": oper, "weight": RISK_DIMENSIONS["营运效率风险"], "items": op_items},
        "经营波动风险": {"score": vol, "weight": RISK_DIMENSIONS["经营波动风险"], "items": vol_items},
    }
    total = _agg([(v["score"], v["weight"]) for v in dims.values()])
    return {"dims": dims, "total": total, "bench": bench}


def risk_level(score: float):
    if score is None:
        return "数据不足", "na"
    for lo, hi, name, stt in RISK_LEVELS:
        if lo <= score < hi:
            return name, stt
    return "高风险", "danger"


def scorecard_df(rs: dict) -> pd.DataFrame:
    rows = []
    for name, d in rs["dims"].items():
        lv, stt = risk_level(d["score"])
        rows.append({"风险维度": name, "风险分": d["score"], "权重": d["weight"],
                     "等级": lv, "status": stt,
                     "加权贡献": (d["score"] or 0) * d["weight"]})
    return pd.DataFrame(rows).sort_values("加权贡献", ascending=False)


def radar_chart(rs: dict, height=340) -> go.Figure:
    names = list(rs["dims"].keys())
    vals = [(rs["dims"][n]["score"] or 0) for n in names]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals + [vals[0]], theta=names + [names[0]],
        fill="toself", name="本公司风险分",
        line=dict(color=C["bad"], width=2), fillcolor="rgba(192,57,43,0.15)"))
    fig.add_trace(go.Scatterpolar(
        r=[45] * (len(names) + 1), theta=names + [names[0]],
        name="中等风险参考线(45)", line=dict(color=C["accent"], width=1.5, dash="dash")))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], gridcolor=C["line2"],
                                   tickfont=dict(size=10)),
                   angularaxis=dict(tickfont=dict(size=11.5, color=C["text"]))),
        showlegend=True, height=height,
        margin=dict(l=40, r=40, t=30, b=30),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, font=dict(size=11)),
        font=dict(family="Source Han Sans SC, Microsoft YaHei, sans-serif", size=12,
                  color=C["text2"]),
    )
    return fig


# ════════════════════════════════════════════════════════════
# 2. Altman Z-Score
# ════════════════════════════════════════════════════════════
def altman_detail(model: dict) -> Optional[dict]:
    i = model["n"] - 1
    a = model["assets"][i]
    if not a:
        return None
    ca, cl = model["cur_assets"][i], model["cur_liab"][i]
    re_ = model["retained"][i] or 0
    ebit = model["ebit"][i] or 0
    eq = model["equity"][i] or 0
    liab = model["liab"][i] or 0
    rev = model["revenue"][i] or 0
    if not liab:
        return None
    x1 = ((ca - cl) / a) if (ca is not None and cl is not None) else None
    x2 = re_ / a
    x3 = ebit / a
    x4 = eq / liab
    x5 = rev / a
    if x1 is None:
        return None
    z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
    zp = 0.717 * x1 + 0.847 * x2 + 3.107 * x3 + 0.420 * x4 + 0.998 * x5
    if z >= 2.99:
        zone = ("安全区（Z ≥ 2.99）", "normal")
    elif z >= 1.81:
        zone = ("灰色区（1.81 ≤ Z < 2.99）", "warning")
    else:
        zone = ("困境区（Z < 1.81）", "danger")
    if zp >= 2.90:
        zone_p = ("安全区（Z' ≥ 2.90）", "normal")
    elif zp >= 1.23:
        zone_p = ("灰色区（1.23 ≤ Z' < 2.90）", "warning")
    else:
        zone_p = ("困境区（Z' < 1.23）", "danger")
    return {
        "x1": x1 * 100, "x2": x2 * 100, "x3": x3 * 100, "x4": x4, "x5": x5,
        "z": z, "zp": zp, "zone": zone, "zone_p": zone_p,
        "series": {"z": model["z_public"], "zp": model["z_private"]},
        "years": model["years"],
    }


# ════════════════════════════════════════════════════════════
# 3. 流动性阶梯 / 债务期限结构
# ════════════════════════════════════════════════════════════
def liquidity_profile(model: dict) -> dict:
    i = model["n"] - 1
    cash = model["cash"][i]
    st = model["st_debt"][i] or 0
    st1 = model["st_debt1"][i] or 0
    lt = model["lt_debt"][i] or 0
    bonds = model["bonds"][i] or 0
    ibd = model["ibd"][i]
    ca, cl = model["cur_assets"][i], model["cur_liab"][i]
    ocf = model["ocf"][i]
    capex = model["capex"][i]

    short_total = st + st1
    long_total = lt + bonds
    cover_short = (cash / short_total) if short_total else None
    cover_all = (cash / ibd) if ibd else None
    # 现金 + 年度经营现金流能否覆盖短债
    cover_with_ocf = ((cash + (ocf or 0)) / short_total) if short_total else None
    # 自由现金流覆盖短债年数
    years_to_repay = (short_total / model["fcf"][i]) if (short_total and model["fcf"][i] and model["fcf"][i] > 0) else None

    return {
        "cash": cash, "short_total": short_total, "long_total": long_total, "ibd": ibd,
        "short_share": (short_total / ibd * 100) if ibd else None,
        "cover_short": cover_short, "cover_all": cover_all,
        "cover_with_ocf": cover_with_ocf, "years_to_repay": years_to_repay,
        "ocf": ocf, "capex": capex, "fcf": model["fcf"][i],
        "ca": ca, "cl": cl, "wc": model["wc"][i],
        "st": st, "st1": st1, "lt": lt, "bonds": bonds,
    }


def cash_waterfall(model: dict) -> Optional[dict]:
    """经营现金流 → 覆盖资本开支/利息/税后 → 自由现金流 → 筹资补充"""
    i = model["n"] - 1
    ocf = model["ocf"][i]
    capex = model["capex"][i]
    interest = model["interest"][i]
    if ocf is None or capex is None:
        return None
    after_capex = ocf - capex
    after_int = after_capex - (interest or 0)
    fin = model["fcf_fin"][i] or 0
    net = after_int + fin
    return {"ocf": ocf, "capex": capex, "after_capex": after_capex,
            "interest": interest, "after_int": after_int, "fin": fin, "net": net}


# ════════════════════════════════════════════════════════════
# 4. 多情景压力测试
# ════════════════════════════════════════════════════════════
def stress_test(model: dict, d_rev: float = 0.0, d_gm: float = 0.0,
                d_dso: float = 0.0, d_dio: float = 0.0,
                d_rate_bp: float = 0.0, tax_rate: float = None) -> dict:
    """
    d_rev:    收入变动 %
    d_gm:     毛利率变动 pp
    d_dso:    DSO 增加天数
    d_dio:    DIO 增加天数
    d_rate_bp: 融资成本上升基点
    返回基准 vs 压力下的 净利润/ROE/EBIT/利息保障倍数/流动比率/FCF
    """
    i = model["n"] - 1
    rev = model["revenue"][i] or 0
    cogs = model["cogs"][i] or 0
    gm = model["gross_margin"][i] or 0
    ebit = model["ebit"][i]
    ni = model["net_profit"][i] or 0
    pretax = model["pretax"][i]
    tax = model["tax"][i]
    equity = model["equity"][i] or 0
    assets = model["assets"][i] or 0
    cur_a = model["cur_assets"][i]
    cur_l = model["cur_liab"][i]
    ibd = model["ibd"][i] or 0
    interest = model["interest"][i] or 0
    ocf = model["ocf"][i] or 0
    capex = model["capex"][i] or 0
    da = model["da"][i] or 0
    cash = model["cash"][i] or 0

    if tax_rate is None:
        tax_rate = (tax / pretax) if (pretax and tax is not None) else 0.15
    tax_rate = float(np.clip(tax_rate, 0.0, 0.40))

    ol = fc.operating_leverage(model)
    cmr = (ol.get("cmr") / 100) if ol.get("ok") and ol.get("cmr") else (gm / 100)

    new_rev = rev * (1 + d_rev / 100)
    # 毛利：规模变动按边际贡献率传导 + 毛利率变动按新收入
    new_gp = rev * (gm / 100) + (rev * d_rev / 100) * cmr + new_rev * (d_gm / 100)
    # EBIT 变动 = 毛利变动（期间费用假设刚性不变）
    d_ebit = (new_gp - rev * (gm / 100))
    new_ebit = (ebit or 0) + d_ebit

    d_interest = ibd * (d_rate_bp / 10000)
    new_interest = interest + d_interest

    # 营运资本占用（DSO/DIO 恶化占用现金，按 5% 资金成本）
    occ = (rev / 365) * max(d_dso, 0) + (cogs / 365) * max(d_dio, 0)
    carrying = occ * 0.05

    new_pretax = new_ebit - new_interest
    new_ni = new_pretax * (1 - tax_rate) - carrying
    new_roe = new_ni / equity * 100 if equity else None
    new_ic = new_ebit / new_interest if new_interest else None
    new_cash = cash - occ
    new_cr = (cur_a + occ - occ) / cur_l if (cur_a and cur_l) else None   # 应收/存货增、现金减，流动资产净增 occ-occ=0
    new_cr = ((cur_a + occ - occ)) / cur_l if (cur_a and cur_l) else None
    new_fcf = (ocf + (new_ni - ni) * 0.6) - capex   # 粗略：经营现金流随利润同向变动
    new_gm = new_gp / new_rev * 100 if new_rev else None

    base = {
        "营业收入": rev, "毛利率(%)": gm, "EBIT": ebit, "利息费用": interest,
        "净利润": ni, "ROE(%)": (ni / equity * 100) if equity else None,
        "利息保障倍数": (ebit / interest) if interest else None,
        "流动比率": (cur_a / cur_l) if (cur_a and cur_l) else None,
        "自由现金流": ocf - capex, "营运资金占用": 0.0,
    }
    stressed = {
        "营业收入": new_rev, "毛利率(%)": new_gm, "EBIT": new_ebit, "利息费用": new_interest,
        "净利润": new_ni, "ROE(%)": new_roe,
        "利息保障倍数": new_ic, "流动比率": new_cr,
        "自由现金流": new_fcf, "营运资金占用": occ,
    }
    rows = []
    for k in base:
        b, s = base[k], stressed[k]
        rows.append({"指标": k, "基准": b, "压力情景": s,
                     "变动": None if (b is None or s is None) else s - b,
                     "变动率(%)": None if (b is None or s is None or not b) else (s - b) / abs(b) * 100})
    return {"base": base, "stressed": stressed, "rows": pd.DataFrame(rows),
            "tax_rate": tax_rate * 100, "cmr": cmr * 100, "occ": occ, "carrying": carrying}


PRESET_SCENARIOS = {
    "轻度下行": dict(d_rev=-5, d_gm=-0.5, d_dso=5, d_rate_bp=50),
    "中度下行": dict(d_rev=-10, d_gm=-1.5, d_dso=15, d_dio=10, d_rate_bp=100),
    "重度下行": dict(d_rev=-20, d_gm=-3.0, d_dso=30, d_dio=20, d_rate_bp=200),
    "通胀情景": dict(d_rev=5, d_gm=-2.0, d_dio=15, d_rate_bp=150),
    "扩产情景": dict(d_rev=15, d_gm=-0.5, d_dio=20, d_rate_bp=100),
}


def scenario_compare(model: dict) -> pd.DataFrame:
    rows = []
    for name, kw in PRESET_SCENARIOS.items():
        try:
            r = stress_test(model, **kw)
        except Exception:
            continue
        rows.append({
            "情景": name,
            "收入变动(%)": kw.get("d_rev", 0),
            "毛利率变动(pp)": kw.get("d_gm", 0),
            "DSO+天数": kw.get("d_dso", 0),
            "利率+BP": kw.get("d_rate_bp", 0),
            "压力后净利润(亿元)": r["stressed"]["净利润"],
            "较基准变动(亿元)": r["stressed"]["净利润"] - (r["base"]["净利润"] or 0),
            "压力后ROE(%)": r["stressed"]["ROE(%)"],
            "压力后利息保障倍数": r["stressed"]["利息保障倍数"],
            "压力后自由现金流(亿元)": r["stressed"]["自由现金流"],
        })
    return pd.DataFrame(rows)


# ════════════════════════════════════════════════════════════
# 5. 风险传导链：指标 → 业务根因 → 财务后果 → 管理动作
# ════════════════════════════════════════════════════════════
TRANSMISSION = {
    "流动比率": ("短债占比上升 / 现金储备下降 / 经营现金流回笼变慢",
                "短期偿付压力上升，可能需要续贷或紧急融资，融资成本上行",
                "拉长债务久期、建立 12 个月现金流滚动预测、锁定备用授信"),
    "速动比率": ("存货占流动资产比重偏高，资产变现能力弱",
                "一旦销售不及预期，存货难快速变现，流动性缓冲不足",
                "控制存货水位、推进 VMI/寄售、对长库龄物料专项消化"),
    "现金短债比": ("现金不足以覆盖一年内到期有息负债",
                  "存在再融资风险，一旦信贷收紧将出现偿付缺口",
                  "提前 6-12 个月安排再融资、用长期资金替换短债、保留最低现金余额红线"),
    "资产负债率": ("扩张主要依靠负债融资，权益增厚不足",
                  "财务弹性下降，评级与融资成本承压，抗周期能力减弱",
                  "控制资本开支节奏、引入股权融资或引入战略投资者、提升内源融资比例"),
    "利息保障倍数": ("EBIT 下滑和/或利率上行、有息负债规模扩张",
                    "利润对利率敏感，加息周期中利润被侵蚀",
                    "置换高息负债、适度固定利率对冲、提升 EBIT  margins"),
    "应收周转率": ("客户回款变慢 / 信用政策放宽 / 渠道压货",
                  "资金占用上升、坏账计提增加，净利润含金量下降",
                  "客户信用分级、超期应收专人催收、考虑保理贴现"),
    "存货周转率": ("备货策略激进 / 需求预测偏差 / 产品滞销",
                  "跌价准备计提上升、仓储与资金成本增加",
                  "建立库龄看板、按需生产、优化安全库存模型"),
    "现金转换周期": ("应收与存货占用上升、对上游议价能力下降",
                    "营运资本吞噬经营现金流，扩张越多现金越紧",
                    "CCC 拆解到事业部、推行预收款、优化付款账期"),
    "ROE": ("净利率、周转率或杠杆三者之一走弱",
            "股东回报下降，再融资与估值承压",
            "用杜邦五因素定位短板，针对性改善盈利 / 周转 / 资本结构"),
    "毛利率": ("售价下行 / 原材料涨价 / 产品结构下移",
               "盈利空间收窄，费用率被动抬升",
               "成本对标、产品结构升级、价格联动条款"),
    "净利率": ("毛利下滑或期间费用率上行",
               "盈利质量下降，抗风险能力减弱",
               "费用零基预算、毛利与费用双红线管理"),
    "收入增长率": ("需求走弱 / 份额流失 / 价格竞争",
                  "规模效应减弱，固定成本摊薄不足",
                  "新客户与新市场开拓、产品差异化、提升客户留存"),
    "净利增长率": ("毛利与费用双向挤压，或存在一次性损益扰动",
                  "成长性受质疑，估值与融资条件恶化",
                  "剔除非经常项看核心盈利、建立可持续增长模型"),
    "经营现金流/净利润": ("利润未转化为现金：应收/存货占用上升",
                         "账面盈利但现金紧张，存在「有利润无现金」风险",
                         "强化回款与库存管理、把 OCF/NI 纳入考核"),
    "自由现金流": ("资本开支强度高于经营现金流创造能力",
                  "扩张依赖外部融资，财务杠杆被动上升",
                  "重排资本开支优先级、分期投入、以 FCF 为投资准入门槛"),
    "收现比": ("销售回款质量下降，存在票据结算或渠道占款",
               "收入真实性需验证，现金流与收入背离",
               "核查回款政策、票据与应收账款结构、渠道库存"),
    "资本开支强度": ("产能扩张 / 技改投入处于高位",
                    "若需求不及预期将形成折旧压力与产能闲置",
                    "项目后评估机制、分阶段投资决策、设置投资回收期门槛"),
}


def transmission_rows(snap: dict) -> pd.DataFrame:
    rows = []
    for dim, items in snap.items():
        for key, d in items.items():
            if d["status"] not in ("warning", "danger"):
                continue
            t = TRANSMISSION.get(key)
            if not t:
                continue
            rows.append({
                "维度": dim, "指标": d["name"], "当前值": d["current"],
                "单位": d["unit"], "状态": d["status"],
                "业务根因": t[0], "财务后果": t[1], "管理动作": t[2],
            })
    return pd.DataFrame(rows)
