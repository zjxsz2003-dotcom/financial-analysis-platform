"""
数据加载与会话状态管理 — V2（完全公司无关）
所有派生数据（预算、战略目标）均基于实际报表自动推导，不写死任何公司
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd
import streamlit as st

from config import INDUSTRY_PRESETS, DEFAULT_INDUSTRY


def _g(k, d=None):
    try:
        return st.session_state.get(k, d)
    except Exception:
        return d


# ════════════════════════════════════════════════════════════
# 载入
# ════════════════════════════════════════════════════════════
def load(parsed: dict, source: str = "", name: str = "", code: str = ""):
    """parsed: parser.parse_folder / parse_uploaded 的输出"""
    st.session_state.income = parsed.get("income")
    st.session_state.balance = parsed.get("balance")
    st.session_state.cashflow = parsed.get("cashflow")
    st.session_state.years = parsed.get("years", [])
    st.session_state.company_name = name or parsed.get("company_name") or "未命名公司"
    st.session_state.company_code = code or parsed.get("company_code") or ""
    st.session_state.data_source = source or "文件上传"
    st.session_state.data_loaded = True
    # 清除派生缓存
    for k in ("budget_cache", "strategy_cache", "industry_cache", "model_cache"):
        st.session_state.pop(k, None)


def reset():
    for k in ("income", "balance", "cashflow", "years", "budget_cache", "strategy_cache",
              "industry_cache", "model_cache", "segments", "extra_metrics"):
        st.session_state.pop(k, None)
    st.session_state.data_loaded = False


# ════════════════════════════════════════════════════════════
# 读取
# ════════════════════════════════════════════════════════════
def is_loaded() -> bool:
    return bool(_g("data_loaded", False))


def get_income() -> Optional[pd.DataFrame]:
    return _g("income")


def get_balance() -> Optional[pd.DataFrame]:
    return _g("balance")


def get_cashflow() -> Optional[pd.DataFrame]:
    return _g("cashflow")


def get_years() -> list:
    return list(_g("years", []) or [])


def get_company_name() -> str:
    if _g("anonymize", False):
        return "A公司"
    return _g("company_name", "未加载")


def get_company_code() -> str:
    return _g("company_code", "")


def get_data_source() -> str:
    return _g("data_source", "未知")


# ════════════════════════════════════════════════════════════
# 可选补充数据（决定部分深度分析是否可用）
# ════════════════════════════════════════════════════════════
def get_segments() -> dict:
    """{板块: {"收入":[...], "成本":[...]}}，未上传则空"""
    return _g("segments", {}) or {}


def has_segments() -> bool:
    return len(get_segments()) >= 2


def get_extra() -> dict:
    """
    可选经营指标：客户/供应商集中度、员工人数、研发资本化率
    {"前五大客户占比":[...], "第一大客户占比":[...], "前五大供应商占比":[...],
     "员工人数":[...], "研发资本化率":[...]}
    """
    return _g("extra_metrics", {}) or {}


def set_extra(d: dict):
    st.session_state.extra_metrics = d


def available_flags() -> dict:
    """数据完备度诊断：哪些增强分析可用"""
    inc, bs, cf = get_income(), get_balance(), get_cashflow()
    seg = get_segments()
    ex = get_extra()
    def has(df, *cols):
        return df is not None and not df.empty and any(
            c in df.columns and pd.to_numeric(df[c], errors="coerce").notna().sum() >= 2
            for c in cols)
    return {
        "利润表": has(inc, "营业收入", "净利润"),
        "资产负债表": has(bs, "资产总计", "股东权益合计"),
        "现金流量表": has(cf, "经营现金流量净额"),
        "折旧摊销": has(cf, "折旧摊销"),
        "销售收现": has(cf, "销售商品收到的现金"),
        "分部数据": len(seg) >= 2,
        "客户集中度": bool(ex.get("前五大客户占比")),
        "员工人数": bool(ex.get("员工人数")),
        "研发费用": has(inc, "研发费用"),
    }


# ════════════════════════════════════════════════════════════
# 行业基准
# ════════════════════════════════════════════════════════════
def get_industry_name() -> str:
    return _g("industry_name", DEFAULT_INDUSTRY)


def set_industry(name: str):
    st.session_state.industry_name = name
    st.session_state.pop("industry_cache", None)


def get_industry_benchmarks() -> dict:
    """返回 {指标: 值}，用户自定义优先于预设"""
    if "industry_cache" in st.session_state:
        return st.session_state.industry_cache
    base = dict(INDUSTRY_PRESETS.get(get_industry_name(), INDUSTRY_PRESETS[DEFAULT_INDUSTRY]))
    custom = _g("industry_custom", {}) or {}
    base.update({k: v for k, v in custom.items() if v is not None})
    st.session_state.industry_cache = base
    return base


def set_custom_benchmark(d: dict):
    cur = dict(_g("industry_custom", {}) or {})
    cur.update({k: v for k, v in d.items() if v is not None})
    st.session_state.industry_custom = cur
    st.session_state.pop("industry_cache", None)


def get_peer_data() -> Optional[pd.DataFrame]:
    """同业公司数据（可选上传），列：公司 + 各指标"""
    return _g("peer_data")


def set_peer_data(df: pd.DataFrame):
    st.session_state.peer_data = df


# ════════════════════════════════════════════════════════════
# 预算：由历史趋势自动推导（可用户覆盖）
# ════════════════════════════════════════════════════════════
def _median_growth(series: list, lo=-0.10, hi=0.35) -> float:
    vals = [v for v in series if v is not None and not (isinstance(v, float) and np.isnan(v))]
    if len(vals) < 2:
        return 0.08
    g = []
    for i in range(1, len(vals)):
        if vals[i - 1] and vals[i - 1] > 0:
            g.append(vals[i] / vals[i - 1] - 1)
    if not g:
        return 0.08
    m = float(np.median(g[-3:]))
    return float(np.clip(m, lo, hi))


def build_default_budget() -> dict:
    """
    参考预算：以「上一年度实际」为基数，乘以「历史增速中位数」，
    即模拟管理层在年初基于上年经营结果制定预算的口径（无前视偏差）。
    用户可在预算页面逐项改写。
    """
    inc, years = get_income(), get_years()
    seg = get_segments()
    if inc is None or inc.empty or len(years) < 2:
        return {}
    i = len(years) - 1          # 当前（预算执行年）
    j = i - 1                   # 上一年度（预算基数年）
    prev = inc.iloc[j]
    cur = inc.iloc[i]
    base_rev = float(prev.get("营业收入") or 0)

    # 增速假设只用 j 年及之前的历史，避免前视偏差
    g = _median_growth(inc["营业收入"].tolist()[:i], lo=0.0, hi=0.30)
    total_budget = base_rev * (1 + g)

    budget = {"收入预算": {}, "成本预算": {}, "费用预算": {}, "利润预算": {},
              "_assumption": {"收入增速假设": round(g * 100, 1)}}

    segs = seg if len(seg) >= 2 else {}
    if segs:
        shares, gs = {}, {}
        tot_prev = 0.0
        for name, d in segs.items():
            r = d["收入"][j] if len(d["收入"]) > j else None
            if r and not (isinstance(r, float) and np.isnan(r)):
                tot_prev += float(r)
        for name, d in segs.items():
            r_prev = d["收入"][j] if len(d["收入"]) > j else None
            if r_prev and not (isinstance(r_prev, float) and np.isnan(r_prev)) and tot_prev:
                shares[name] = float(r_prev) / tot_prev
            gs[name] = _median_growth([x for x in d["收入"][:i] if x is not None], 0.0, 0.35)
        denom = sum(shares.get(n, 0) * (1 + gs.get(n, g)) for n in segs) or 1
        for name in segs:
            share = shares.get(name, 1.0 / len(segs))
            budget["收入预算"][name] = round(total_budget * share * (1 + gs.get(name, g)) / denom, 2)
            c_prev = segs[name]["成本"][j] if len(segs[name]["成本"]) > j else None
            r_prev = segs[name]["收入"][j] if len(segs[name]["收入"]) > j else None
            c_rate = (float(c_prev) / float(r_prev)) if (c_prev and r_prev) else 0.8
            budget["成本预算"][name] = round(budget["收入预算"][name] * c_rate, 2)
        budget["收入预算"]["合计"] = round(sum(
            v for k, v in budget["收入预算"].items() if k != "合计"), 2)
        budget["成本预算"]["合计"] = round(sum(
            v for k, v in budget["成本预算"].items() if k != "合计"), 2)
    else:
        budget["收入预算"]["整体"] = round(total_budget, 2)
        budget["收入预算"]["合计"] = round(total_budget, 2)
        cost_rate = float(prev.get("营业成本") or 0) / base_rev if base_rev else 0.8
        budget["成本预算"]["整体"] = round(total_budget * cost_rate, 2)
        budget["成本预算"]["合计"] = round(total_budget * cost_rate, 2)

    for fee in ("销售费用", "管理费用", "研发费用", "财务费用"):
        if fee in inc.columns:
            gv = _median_growth(inc[fee].tolist()[:i], -0.05, 0.30)
            base_v = float(prev.get(fee) or 0)
            budget["费用预算"][fee] = round(base_v * (1 + gv), 2)
            budget["_assumption"][f"{fee}增速假设"] = round(gv * 100, 1)

    np_series = inc["净利润"].tolist()[:i]
    gnp = _median_growth(np_series, -0.15, 0.40)
    budget["利润预算"]["营业利润"] = round(float(prev.get("营业利润") or 0) * (1 + gnp), 2)
    budget["利润预算"]["净利润"] = round(float(prev.get("净利润") or 0) * (1 + gnp), 2)
    budget["_assumption"]["净利润增速假设"] = round(gnp * 100, 1)
    return budget


def get_budget() -> dict:
    if "budget_cache" in st.session_state:
        return st.session_state.budget_cache
    b = build_default_budget()
    st.session_state.budget_cache = b
    return b


def set_budget(b: dict):
    st.session_state.budget_cache = b


# ════════════════════════════════════════════════════════════
# 战略目标：由杜邦分解 + 历史/行业基准自动推导
# ════════════════════════════════════════════════════════════
def build_default_strategy(model: dict) -> list:
    """model: finance_core.build_model() 的输出"""
    if not model or not model.get("years"):
        return []
    years = model["years"]
    i = len(years) - 1
    bench = get_industry_benchmarks()
    roe = model["roe"]
    rev = model["revenue"]
    npv = model["net_profit"]

    def cur(series):
        return float(series[i]) if i < len(series) and series[i] is not None else 0.0

    def _median(vals, default):
        vals = [v for v in vals if v is not None]
        return float(np.median(vals)) if vals else default

    # 目标1：ROE —— 取「近3年最优」「行业基准」「当前×1.05」三者最大，确保有挑战性
    roe_hist = [v for v in roe if v is not None][-3:]
    roe_target = round(max(max(roe_hist) if roe_hist else cur(roe),
                            bench.get("ROE", 10),
                            cur(roe) * 1.05), 1)
    npm = cur(model["net_margin"])
    ato = cur(model["asset_turnover"])
    em = cur(model["equity_multiplier"])

    # 目标2：收入增长 —— 近3年中位增速 vs 行业基准取高（不用 CAGR，避免目标过激）
    gs = []
    for k in range(1, len(rev)):
        if rev[k - 1] and rev[k]:
            gs.append(rev[k] / rev[k - 1] - 1)
    hist_g = float(np.median(gs[-3:]) * 100) if gs else 10.0
    g_target = round(max(hist_g, bench.get("收入增长率", 8), 5.0), 1)
    rev_target = round(cur(rev) * (1 + g_target / 100), 1)

    # 目标3：现金流质量 —— 不低于 1.0，且比当前再改善 5%
    ocf_ni = cur(model["ocf_to_ni"])
    ocf_target = round(max(1.0, ocf_ni * 1.05), 2)

    # 目标4：杠杆控制（越低越好）—— 向行业基准收敛，每期至少压降 5%
    dr = cur(model["debt_ratio"])
    dr_target = round(max(bench.get("资产负债率", 50), dr * 0.95), 1)

    targets = [
        {
            "name": f"ROE 达到 {roe_target}%",
            "unit": "%", "target_value": roe_target, "current_value": round(cur(roe), 1),
            "kpi_tree": {
                "销售净利率": {"weight": 0.45, "current": round(npm, 2),
                               "target": round(npm * (roe_target / max(cur(roe), 0.01)), 2)},
                "总资产周转率": {"weight": 0.30, "current": round(ato, 2),
                                 "target": round(max(ato * 1.05, bench.get("总资产周转率", 0.8)), 2)},
                "权益乘数": {"weight": 0.25, "current": round(em, 2),
                             "target": round(min(em * 1.03, 3.0), 2)},
            },
        },
        {
            "name": f"营业收入增长 {g_target}%",
            "unit": "亿元", "target_value": rev_target, "current_value": round(cur(rev), 1),
            "kpi_tree": {
                "收入同比增速": {"weight": 0.6, "current": round(cur(model["rev_growth"]), 1),
                                 "target": g_target},
                "毛利率": {"weight": 0.4, "current": round(cur(model["gross_margin"]), 1),
                           "target": round(max(cur(model["gross_margin"]), bench.get("毛利率", 20)), 1)},
            },
        },
        {
            "name": f"经营现金流/净利润 ≥ {ocf_target}",
            "unit": "倍", "target_value": ocf_target,
            "current_value": round(ocf_ni, 2),
            "kpi_tree": {
                "应收账款周转天数": {"weight": 0.4, "current": round(cur(model["dso"]), 0),
                                     "target": round(cur(model["dso"]) * 0.92, 0)},
                "存货周转天数": {"weight": 0.35, "current": round(cur(model["dio"]), 0),
                                 "target": round(cur(model["dio"]) * 0.95, 0)},
                "应付账款周转天数": {"weight": 0.25, "current": round(cur(model["dpo"]), 0),
                                     "target": round(cur(model["dpo"]) * 1.05, 0)},
            },
        },
        {
            "name": f"资产负债率降至 {dr_target}% 以内",
            "unit": "%", "target_value": dr_target,
            "current_value": round(dr, 1), "lower_better": True,
            "kpi_tree": {
                "流动比率": {"weight": 0.4, "current": round(cur(model["current_ratio"]), 2),
                             "target": round(max(cur(model["current_ratio"]), bench.get("流动比率", 1.5)), 2)},
                "利息保障倍数": {"weight": 0.35, "current": round(cur(model["interest_cover"]), 1),
                                 "target": round(max(cur(model["interest_cover"]), 4.0), 1)},
                "现金/短期有息负债": {"weight": 0.25, "current": round(cur(model["cash_to_short_debt"]), 2),
                                     "target": round(max(cur(model["cash_to_short_debt"]), 1.2), 2)},
            },
        },
    ]
    return targets


def get_strategy(model: dict) -> list:
    if "strategy_cache" in st.session_state:
        return st.session_state.strategy_cache
    t = build_default_strategy(model)
    st.session_state.strategy_cache = t
    return t


def set_strategy(t: list):
    st.session_state.strategy_cache = t
