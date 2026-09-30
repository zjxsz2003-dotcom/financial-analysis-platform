"""
财务核心引擎 — V2
从三张报表推导全部指标：杜邦五因素、量价结构分解、现金转换周期、
经营杠杆与盈亏平衡、盈利质量、Altman Z、自由现金流桥

设计原则：
  * 全部由数据推导，不写死任何公司 / 行业口径
  * 缺项用 None 表示，下游分析优雅降级
"""
from __future__ import annotations
from typing import Optional, Sequence
import numpy as np
import pandas as pd
import streamlit as st

from modules.data_loader import (get_income, get_balance, get_cashflow, get_years,
                                 get_segments, get_extra)


# ════════════════════════════════════════════════════════════
# 基础工具
# ════════════════════════════════════════════════════════════
def _col(df: pd.DataFrame, key: str, n: int) -> list:
    """取列 → list[float|None]"""
    if df is None or df.empty or key not in df.columns:
        return [None] * n
    s = pd.to_numeric(df[key], errors="coerce")
    return [None if pd.isna(v) else float(v) for v in s.tolist()]


def _avg(arr: Sequence) -> list:
    """期初期末平均（首期用自身）"""
    out = []
    for i, v in enumerate(arr):
        p = arr[i - 1] if i > 0 else None
        if v is None:
            out.append(None)
        elif p is None:
            out.append(float(v))
        else:
            out.append((float(v) + float(p)) / 2)
    return out


def _d(a, b):
    """安全除法"""
    try:
        if a is None or b is None or b == 0 or b != b or a != a:
            return None
        return float(a) / float(b)
    except (TypeError, ZeroDivisionError):
        return None


def _map(fn, *arrs):
    return [fn(*vals) if all(v is not None for v in vals) else None for vals in zip(*arrs)]


def _growth(arr: Sequence) -> list:
    out = [None]
    for i in range(1, len(arr)):
        if arr[i] is None or arr[i - 1] is None or arr[i - 1] == 0:
            out.append(None)
        else:
            out.append((float(arr[i]) / float(arr[i - 1]) - 1) * 100)
    return out


def _last(arr: Sequence, default=None):
    for v in reversed(list(arr)):
        if v is not None and v == v:
            return float(v)
    return default


def _prev(arr: Sequence, default=None):
    vals = [v for v in arr if v is not None and v == v]
    return float(vals[-2]) if len(vals) >= 2 else default


# ════════════════════════════════════════════════════════════
# 主模型
# ════════════════════════════════════════════════════════════
def build_model(force: bool = False) -> dict:
    if not force and st.session_state.get("model_cache"):
        return st.session_state.model_cache

    inc, bs, cf = get_income(), get_balance(), get_cashflow()
    years = get_years()
    n = len(years)
    if n == 0 or inc is None or inc.empty:
        return {}

    # ── 利润表 ──
    revenue = _col(inc, "营业收入", n)
    cogs = _col(inc, "营业成本", n)
    tax_surcharge = _col(inc, "税金及附加", n)
    sell = _col(inc, "销售费用", n)
    admin = _col(inc, "管理费用", n)
    rd = _col(inc, "研发费用", n)
    fin = _col(inc, "财务费用", n)
    op_profit = _col(inc, "营业利润", n)
    pretax = _col(inc, "利润总额", n)
    tax = _col(inc, "所得税费用", n)
    net_profit = _col(inc, "净利润", n)
    np_parent = _col(inc, "归母净利润", n)
    nonop_inc = _col(inc, "营业外收入", n)
    nonop_exp = _col(inc, "营业外支出", n)

    # ── 资产负债表 ──
    assets = _col(bs, "资产总计", n)
    cur_assets = _col(bs, "流动资产合计", n)
    cash = _col(bs, "货币资金", n)
    ar = _col(bs, "应收账款净额", n)
    inv = _col(bs, "存货净额", n)
    fixed = _col(bs, "固定资产净额", n)
    cip = _col(bs, "在建工程净额", n)
    intang = _col(bs, "无形资产净额", n)
    liab = _col(bs, "负债合计", n)
    cur_liab = _col(bs, "流动负债合计", n)
    st_debt = _col(bs, "短期借款", n)
    st_debt1 = _col(bs, "一年内到期非流动负债", n)
    ap = _col(bs, "应付账款", n)
    lt_debt = _col(bs, "长期借款", n)
    bonds = _col(bs, "应付债券", n)
    equity = _col(bs, "股东权益合计", n)
    equity_p = _col(bs, "归母权益", n)
    retained = _col(bs, "未分配利润", n)

    # ── 现金流 ──
    ocf = _col(cf, "经营现金流量净额", n)
    icf = _col(cf, "投资现金流量净额", n)
    fcf_fin = _col(cf, "筹资现金流量净额", n)
    capex = _col(cf, "资本开支", n)
    cash_sales = _col(cf, "销售商品收到的现金", n)
    da = _col(cf, "折旧摊销", n)

    # ── 派生 ──
    gross_profit = _map(lambda r, c: r - c, revenue, cogs)
    # EBIT = 营业利润 + 财务费用（财务费用含利息支出/汇兑，作为近似）
    ebit = _map(lambda o, f: o + (f or 0), op_profit, fin)
    ebitda = _map(lambda e, d: e + d, ebit, da)
    fcf = _map(lambda o, c: o - c, ocf, capex)
    ibd = _map(lambda a, b, c: (a or 0) + (b or 0) + (c or 0), st_debt, st_debt1, lt_debt)
    ibd = _map(lambda x, y: (x or 0) + (y or 0), ibd, bonds)
    net_debt = _map(lambda d, c: d - c, ibd, cash)
    avg_assets = _avg(assets)
    avg_equity = _avg(equity)
    avg_ar = _avg(ar)
    avg_inv = _avg(inv)
    avg_ap = _avg(ap)

    # ── 比率 ──
    gross_margin = [_d(g, r) and g / r * 100 for g, r in zip(gross_profit, revenue)]
    gross_margin = _map(lambda g, r: g / r * 100, gross_profit, revenue)
    ebit_margin = _map(lambda e, r: e / r * 100, ebit, revenue)
    net_margin = _map(lambda p, r: p / r * 100, net_profit, revenue)
    npm_parent = _map(lambda p, r: p / r * 100, np_parent, revenue)
    roe = _map(lambda p, e: p / e * 100, net_profit, avg_equity)
    roa = _map(lambda p, a: p / a * 100, net_profit, avg_assets)
    roa_ebit = _map(lambda e, a: e / a * 100, ebit, avg_assets)

    asset_turnover = _map(lambda r, a: r / a, revenue, avg_assets)
    equity_multiplier = _map(lambda a, e: a / e, avg_assets, avg_equity)
    current_ratio = _map(lambda ca, cl: ca / cl, cur_assets, cur_liab)
    quick_ratio = _map(lambda ca, iv, cl: (ca - iv) / cl, cur_assets, inv, cur_liab)
    cash_ratio = _map(lambda c, cl: c / cl, cash, cur_liab)
    cash_to_short_debt = _map(lambda c, s: c / s, cash, ibd)
    cash_to_st_debt_only = _map(lambda c, s: c / s, cash, st_debt)
    debt_ratio = _map(lambda l, a: l / a * 100, liab, assets)
    ibd_ratio = _map(lambda d, a: d / a * 100, ibd, assets)

    interest = [abs(f) if f is not None and f > 0 else (abs(f) if f else None) for f in fin]
    interest_cover = _map(lambda e, i: e / i if i else None, ebit, interest)

    ar_turnover = _map(lambda r, a: r / a, revenue, avg_ar)
    inv_turnover = _map(lambda c, v: c / v, cogs, avg_inv)
    ap_turnover = _map(lambda c, p: c / p, cogs, avg_ap)
    dso = _map(lambda a, r: a / r * 365, ar, revenue)
    dio = _map(lambda v, c: v / c * 365, inv, cogs)
    dpo = _map(lambda p, c: p / c * 365, ap, cogs)
    ccc = _map(lambda a, b, c: a + b - c, dso, dio, dpo)

    rev_growth = _growth(revenue)
    np_growth = _growth(net_profit)
    npp_growth = _growth(np_parent)

    ocf_to_ni = _map(lambda o, p: o / p, ocf, net_profit)
    fcf_to_rev = _map(lambda f, r: f / r * 100, fcf, revenue)
    capex_intensity = _map(lambda c, o: c / o * 100, capex, ocf)
    cash_recovery = _map(lambda s, r: s / r * 100, cash_sales, revenue)
    accrual_ratio = _map(lambda p, o, a: (p - o) / a * 100, net_profit, ocf, avg_assets)
    da_ratio = _map(lambda d, r: d / r * 100, da, revenue)
    sell_ratio = _map(lambda s, r: s / r * 100, sell, revenue)
    admin_ratio = _map(lambda a, r: a / r * 100, admin, revenue)
    rd_ratio = _map(lambda x, r: x / r * 100, rd, revenue)
    fin_ratio = _map(lambda f, r: f / r * 100, fin, revenue)
    period_expense_ratio = _map(
        lambda s, a, f, r: ((s or 0) + (a or 0) + (f or 0)) / r * 100, sell, admin, fin, revenue)

    # 非经常性损益近似（营业外收支净额/利润总额）
    nonop_net = _map(lambda i, e: (i or 0) - (e or 0), nonop_inc, nonop_exp)
    nonrecurring_ratio = _map(lambda x, p: x / p * 100 if p else None, nonop_net, pretax)

    # 杜邦五因素
    tax_burden = _map(lambda p, t: p / t, net_profit, pretax)      # 税负负担
    interest_burden = _map(lambda t, e: t / e, pretax, ebit)       # 利息负担
    roe_5f = _map(lambda a, b, c, d, e: a * b * (c / 100) * d * e,
                  tax_burden, interest_burden, ebit_margin, asset_turnover, equity_multiplier)
    roe_5f = [v * 100 if v is not None else None for v in roe_5f]

    # 营运资本
    wc = _map(lambda ca, cl: ca - cl, cur_assets, cur_liab)
    owc = _map(lambda a, v, p: (a or 0) + (v or 0) - (p or 0), ar, inv, ap)
    wc_to_rev = _map(lambda w, r: w / r * 100, owc, revenue)

    # Altman Z
    z_public = []
    z_private = []
    for i in range(n):
        a = assets[i]
        if not a:
            z_public.append(None); z_private.append(None); continue
        x1 = (cur_assets[i] - cur_liab[i]) / a if cur_assets[i] is not None and cur_liab[i] is not None else 0
        x2 = (retained[i] or 0) / a
        x3 = (ebit[i] or 0) / a
        x4 = (equity[i] or 0) / (liab[i] or 1) if liab[i] else None
        x5 = (revenue[i] or 0) / a
        if x4 is None:
            z_public.append(None); z_private.append(None); continue
        z_public.append(1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5)
        z_private.append(0.717 * x1 + 0.847 * x2 + 3.107 * x3 + 0.420 * x4 + 0.998 * x5)

    model = dict(
        years=years, n=n,
        revenue=revenue, cogs=cogs, gross_profit=gross_profit, gross_margin=gross_margin,
        tax_surcharge=tax_surcharge, sell=sell, admin=admin, rd=rd, fin=fin,
        op_profit=op_profit, ebit=ebit, ebitda=ebitda, pretax=pretax, tax=tax,
        net_profit=net_profit, np_parent=np_parent,
        nonop_net=nonop_net, nonrecurring_ratio=nonrecurring_ratio,
        assets=assets, cur_assets=cur_assets, cash=cash, ar=ar, inv=inv,
        fixed=fixed, cip=cip, intang=intang,
        liab=liab, cur_liab=cur_liab, st_debt=st_debt, st_debt1=st_debt1, ap=ap,
        lt_debt=lt_debt, bonds=bonds, equity=equity, equity_p=equity_p, retained=retained,
        ocf=ocf, icf=icf, fcf_fin=fcf_fin, capex=capex, cash_sales=cash_sales, da=da,
        fcf=fcf, ibd=ibd, net_debt=net_debt, interest=interest,
        avg_assets=avg_assets, avg_equity=avg_equity,
        ebit_margin=ebit_margin, net_margin=net_margin, npm_parent=npm_parent,
        roe=roe, roa=roa, roa_ebit=roa_ebit,
        asset_turnover=asset_turnover, equity_multiplier=equity_multiplier,
        current_ratio=current_ratio, quick_ratio=quick_ratio, cash_ratio=cash_ratio,
        cash_to_short_debt=cash_to_short_debt, cash_to_st_debt_only=cash_to_st_debt_only,
        debt_ratio=debt_ratio, ibd_ratio=ibd_ratio, interest_cover=interest_cover,
        ar_turnover=ar_turnover, inv_turnover=inv_turnover, ap_turnover=ap_turnover,
        dso=dso, dio=dio, dpo=dpo, ccc=ccc,
        rev_growth=rev_growth, np_growth=np_growth, npp_growth=npp_growth,
        ocf_to_ni=ocf_to_ni, fcf_to_rev=fcf_to_rev, capex_intensity=capex_intensity,
        cash_recovery=cash_recovery, accrual_ratio=accrual_ratio, da_ratio=da_ratio,
        sell_ratio=sell_ratio, admin_ratio=admin_ratio, rd_ratio=rd_ratio,
        fin_ratio=fin_ratio, period_expense_ratio=period_expense_ratio,
        tax_burden=tax_burden, interest_burden=interest_burden, roe_5f=roe_5f,
        wc=wc, owc=owc, wc_to_rev=wc_to_rev,
        z_public=z_public, z_private=z_private,
    )
    st.session_state.model_cache = model
    return model


# ════════════════════════════════════════════════════════════
# 杜邦五因素连环替代分解
# ════════════════════════════════════════════════════════════
DUPONT_FACTORS = [
    ("税负负担率", "tax_burden", "净利润/利润总额"),
    ("利息负担率", "interest_burden", "利润总额/EBIT"),
    ("EBIT利润率", "ebit_margin", "EBIT/营业收入 (%)"),
    ("总资产周转率", "asset_turnover", "营业收入/平均总资产 (次)"),
    ("权益乘数", "equity_multiplier", "平均总资产/平均权益 (倍)"),
]


def dupont_table(model: dict) -> pd.DataFrame:
    years = model["years"]
    rows = []
    for i, y in enumerate(years):
        rows.append({
            "年份": int(y),
            "ROE(%)": model["roe"][i],
            "税负负担率": model["tax_burden"][i],
            "利息负担率": model["interest_burden"][i],
            "EBIT利润率(%)": model["ebit_margin"][i],
            "总资产周转率": model["asset_turnover"][i],
            "权益乘数": model["equity_multiplier"][i],
        })
    return pd.DataFrame(rows)


def dupont_decompose(model: dict, i0: int = 0, i1: int = -1) -> list:
    """
    连环替代法：按 DUPONT_FACTORS 顺序逐项替换，量化各因素对 ROE 的贡献(pp)
    返回 [(因素名, 贡献pp, 期初值, 期末值, 口径说明)]
    """
    n = model["n"]
    if i1 < 0:
        i1 = n - 1
    if n < 2 or i0 == i1:
        return []

    def roe_of(vals):
        tb, ib, em_, at, eq = vals
        if None in (tb, ib, em_, at, eq):
            return None
        return tb * ib * (em_ / 100) * at * eq * 100

    keys = [k for _, k, _ in DUPONT_FACTORS]
    names = [nm for nm, _, _ in DUPONT_FACTORS]
    descs = [d for _, _, d in DUPONT_FACTORS]

    base = [model[k][i0] for k in keys]
    target = [model[k][i1] for k in keys]
    if any(v is None for v in base) or any(v is None for v in target):
        return []

    contribs = []
    cur = list(base)
    prev_roe = roe_of(cur)
    if prev_roe is None:
        return []
    for j in range(len(keys)):
        cur[j] = target[j]
        new_roe = roe_of(cur)
        if new_roe is None:
            contribs.append((names[j], 0.0, base[j], target[j], descs[j]))
            continue
        contribs.append((names[j], new_roe - prev_roe, base[j], target[j], descs[j]))
        prev_roe = new_roe
    return contribs


# ════════════════════════════════════════════════════════════
# 毛利率变动：结构效应 × 毛利率效应 × 交叉效应（需分部数据）
# ════════════════════════════════════════════════════════════
def margin_bridge(model: dict) -> Optional[dict]:
    """
    总毛利率变动 = Σ Δw_i·m_i0 (结构效应) + Σ w_i0·Δm_i (毛利率效应) + Σ Δw_i·Δm_i (交叉)
    """
    seg = get_segments()
    if len(seg) < 2:
        return None
    years = model["years"]
    n = model["n"]
    if n < 2:
        return None
    i1, i0 = n - 1, n - 2

    def pick(d, key, i):
        arr = d.get(key, [])
        if i < len(arr):
            v = arr[i]
            return None if v is None or (isinstance(v, float) and np.isnan(v)) else float(v)
        return None

    # 板块收入/毛利（成本缺失时用整体毛利率近似）
    rev1, rev0, gp1, gp0 = {}, {}, {}, {}
    for name, d in seg.items():
        r1, r0 = pick(d, "收入", i1), pick(d, "收入", i0)
        c1, c0 = pick(d, "成本", i1), pick(d, "成本", i0)
        if r1 is not None and c1 is not None:
            gp1[name] = r1 - c1
        elif r1 is not None:
            gp1[name] = r1 * (model["gross_margin"][i1] or 0) / 100
        if r0 is not None and c0 is not None:
            gp0[name] = r0 - c0
        elif r0 is not None:
            gp0[name] = r0 * (model["gross_margin"][i0] or 0) / 100
        rev1[name], rev0[name] = r1, r0

    names = [k for k in rev1 if rev1[k] and rev0.get(k)]
    if not names:
        return None
    t1 = sum(rev1[k] for k in names)
    t0 = sum(rev0[k] for k in names)
    if not t1 or not t0:
        return None

    mix_eff = price_eff = cross_eff = 0.0
    detail = []
    for k in names:
        w1, w0 = rev1[k] / t1, rev0[k] / t0
        m1 = gp1[k] / rev1[k] if rev1[k] else 0
        m0 = gp0[k] / rev0[k] if rev0[k] else 0
        mix_eff += (w1 - w0) * m0
        price_eff += w0 * (m1 - m0)
        cross_eff += (w1 - w0) * (m1 - m0)
        detail.append({
            "板块": k, "收入占比_上期": w0 * 100, "收入占比_本期": w1 * 100,
            "毛利率_上期": m0 * 100, "毛利率_本期": m1 * 100,
            "结构贡献(pp)": (w1 - w0) * m0 * 100,
            "毛利率贡献(pp)": w0 * (m1 - m0) * 100,
            "收入贡献(亿元)": rev1[k] - rev0[k],
            "收入贡献占比(%)": (rev1[k] - rev0[k]) / (t1 - t0) * 100 if t1 != t0 else 0,
        })
    total = (sum(gp1[k] for k in names) / t1 - sum(gp0[k] for k in names) / t0)
    return {
        "mix": mix_eff * 100, "price": price_eff * 100, "cross": cross_eff * 100,
        "total": total * 100, "detail": pd.DataFrame(detail),
        "year0": years[i0], "year1": years[i1],
    }


# ════════════════════════════════════════════════════════════
# 经营杠杆：EBIT 对收入回归 → 边际贡献率 / 固定成本 / 盈亏平衡
# ════════════════════════════════════════════════════════════
def operating_leverage(model: dict) -> dict:
    """
    成本性态与经营杠杆（会计法，稳健可解释）：
      变动成本 ≈ 营业成本（+税金及附加）
      边际贡献 = 营业收入 − 营业成本 = 毛利
      固定成本 ≈ 毛利 − EBIT（即期间费用及税金等相对刚性支出）
      盈亏平衡收入 = 固定成本 / 边际贡献率
      DOL = 边际贡献 / EBIT　　DFL = EBIT / (EBIT − 利息)　　DTL = DOL × DFL
    仅当固定成本 > 0 且边际贡献率 > 0 时盈亏平衡才有经济意义。
    """
    res = {"ok": False}
    i = model["n"] - 1
    rev = model["revenue"][i]
    gp = model["gross_profit"][i]
    ebit = model["ebit"][i]
    if None in (rev, gp, ebit) or not rev or ebit <= 0:
        return res
    cmr = gp / rev * 100                       # 边际贡献率 %
    cmr_f = cmr / 100
    fixed = gp - ebit                          # 固定成本（亿元）
    bep = fixed / cmr_f if cmr_f > 0.02 else None
    if bep is not None and bep <= 0:
        bep = None                             # 固定成本为负 → 盈亏平衡无经济意义
    safety = (rev - bep) / rev * 100 if bep else None
    dol = gp / ebit if ebit else None

    interest = model["interest"][i]
    dfl = ebit / (ebit - interest) if (interest and ebit > interest) else None
    dtl = dol * dfl if (dol and dfl) else None

    # 历史序列（用于展示趋势）
    hist = []
    for j in range(model["n"]):
        r, g, e = model["revenue"][j], model["gross_profit"][j], model["ebit"][j]
        if None in (r, g, e) or not r or not e:
            hist.append(None)
        else:
            hist.append(g / e)

    res.update({
        "ok": True, "cmr": cmr, "fixed": fixed, "bep": bep, "safety": safety,
        "dol": dol, "dfl": dfl, "dtl": dtl, "cur_rev": rev, "cur_ebit": ebit,
        "cur_gp": gp, "dol_hist": hist,
        "x": [v for v in model["revenue"] if v is not None],
        "y": [model["ebit"][j] for j in range(model["n"]) if model["revenue"][j]],
    })
    return res


# ════════════════════════════════════════════════════════════
# 盈利质量：净利润 → 经营现金流 → 自由现金流 桥
# ════════════════════════════════════════════════════════════
def cash_bridge(model: dict, i: int = -1) -> dict:
    n = model["n"]
    if i < 0:
        i = n - 1
    ni = model["net_profit"][i]
    ocf = model["ocf"][i]
    da = model["da"][i]
    capex = model["capex"][i]
    wc_change = None
    if None not in (ocf, ni, da):
        wc_change = ocf - ni - da
    return {
        "year": model["years"][i], "净利润": ni, "折旧摊销": da,
        "营运资本变动": wc_change, "经营现金流": ocf, "资本开支": capex,
        "自由现金流": model["fcf"][i],
    }


def earnings_quality_score(model: dict) -> dict:
    """
    盈利质量评分 0-100（越高越好）。六个子项各 0-100，加权。
    """
    def sc(v, good, bad, invert=False):
        if v is None:
            return None
        if not invert:
            if v >= good:
                return 100.0
            if v <= bad:
                return 0.0
            return (v - bad) / (good - bad) * 100
        if v <= good:
            return 100.0
        if v >= bad:
            return 0.0
        return (bad - v) / (bad - good) * 100

    items = {
        "经营现金流/净利润": (sc(_last(model["ocf_to_ni"]), 1.2, 0.4), 0.25),
        "销售收现比": (sc(_last(model["cash_recovery"]), 105, 85), 0.18),
        "应计利润率(越低越好)": (sc(_last(model["accrual_ratio"]), 1.0, 8.0, invert=True), 0.17),
        "自由现金流(亿元)": (sc(_last(model["fcf"]), 5.0, -10.0), 0.18),
        "非经常性损益占比(越低越好)": (sc(_last(model["nonrecurring_ratio"]), 1.0, 15.0, invert=True), 0.12),
        "毛利率稳定性(越低越好)": (sc(_pct_std(model["gross_margin"]), 1.5, 12.0, invert=True), 0.10),
    }
    tot, wsum = 0.0, 0.0
    rows = []
    for k, (s, w) in items.items():
        rows.append({"维度": k, "得分": s, "权重": w})
        if s is not None:
            tot += s * w
            wsum += w
    score = tot / wsum if wsum else None
    return {"score": score, "items": rows, "coverage": wsum}


def _pct_std(arr: Sequence) -> Optional[float]:
    vals = [v for v in arr if v is not None][-5:]
    if len(vals) < 2:
        return None
    m = float(np.mean(vals))
    if abs(m) < 1e-9:
        return None
    return float(np.std(vals)) / abs(m) * 100


# ════════════════════════════════════════════════════════════
# 营运资本释放测算
# ════════════════════════════════════════════════════════════
def wc_release(model: dict, days: int = 10) -> Optional[dict]:
    cur_rev = _last(model["revenue"])
    cur_cogs = _last(model["cogs"])
    if not cur_rev or not cur_cogs:
        return None
    per_day_rev = cur_rev / 365
    per_day_cogs = cur_cogs / 365
    return {
        "days": days,
        "应收": per_day_rev * days,
        "存货": per_day_cogs * days,
        "应付": per_day_cogs * days,
        "净释放": per_day_rev * days + per_day_cogs * days - 0,
    }


# ════════════════════════════════════════════════════════════
# 人均 / 集中度（依赖可选数据）
# ════════════════════════════════════════════════════════════
def per_capita(model: dict) -> Optional[dict]:
    ex = get_extra()
    staff = ex.get("员工人数") or []
    staff = [v for v in staff if v]
    if not staff:
        return None
    n = model["n"]
    rev = model["revenue"][-1]
    npv = model["net_profit"][-1]
    s = staff[-1]
    if not s:
        return None
    out = {"员工人数": s, "人均创收": (rev / s * 1e4) if rev else None,  # 亿元/万人 → 万元/人
           "人均创利": (npv / s * 1e4) if npv else None}
    if len(staff) >= 2 and staff[-2]:
        out["人数变动"] = (s / staff[-2] - 1) * 100
    return out
