"""
KPI 指标计算引擎 v2 — 适配CSMAR真实DataFrame格式
"""
import pandas as pd
import numpy as np
from modules.data_loader import get_income, get_balance, get_cashflow, get_years, get_industry_benchmarks
from config import KPI_DIMENSIONS, KPI_NAMES_CN, DEFAULT_THRESHOLDS


def calc_all_kpis() -> dict:
    """
    计算所有KPI，支持CSMAR DataFrame格式
    返回: {"盈利能力": {"ROE": {"values":[], "current":x, "yoy":y, "status":"normal"}, ...}, ...}
    """
    inc = get_income()
    bs = get_balance()
    cf = get_cashflow()
    industry = get_industry_benchmarks()

    if inc is None or bs is None:
        return _empty_kpi_result()

    years_list = inc["年份"].tolist()
    n = len(years_list)

    # 提取核心数据
    revenue = inc["营业收入"].values
    cogs = inc["营业成本"].values
    net_profit = inc["净利润"].values
    total_assets = bs["资产总计"].values if "资产总计" in bs.columns else np.zeros(n)
    total_equity = bs["股东权益合计"].values if "股东权益合计" in bs.columns else np.zeros(n)
    current_assets = bs["流动资产合计"].values if "流动资产合计" in bs.columns else np.zeros(n)
    current_liab = bs["流动负债合计"].values if "流动负债合计" in bs.columns else np.ones(n)
    total_liab = bs["负债合计"].values if "负债合计" in bs.columns else np.zeros(n)
    inventory = bs["存货净额"].values if "存货净额" in bs.columns else np.ones(n)
    receivables = bs["应收账款净额"].values if "应收账款净额" in bs.columns else np.ones(n)

    ocf = np.zeros(n)
    capex = np.zeros(n)
    if cf is not None:
        if "经营现金流量净额" in cf.columns:
            ocf = cf["经营现金流量净额"].values
        if "资本开支" in cf.columns:
            capex = cf["资本开支"].values

    # 计算各项指标
    def safe_div(a, b, default=0):
        return np.where(b != 0, a / b, default)

    # 盈利能力
    roe_vals = np.round(safe_div(net_profit, total_equity) * 100, 1)
    gross_margin_vals = np.round(safe_div(revenue - cogs, revenue) * 100, 1)
    net_margin_vals = np.round(safe_div(net_profit, revenue) * 100, 1)

    # 偿债能力
    cur_ratio_vals = np.round(safe_div(current_assets, current_liab), 2)
    debt_ratio_vals = np.round(safe_div(total_liab, total_assets) * 100, 1)

    # 营运能力
    inv_turnover_vals = np.round(safe_div(cogs, inventory, 0), 1)
    ar_turnover_vals = np.round(safe_div(revenue, receivables, 0), 1)

    # 成长能力
    rev_growth_vals = np.zeros(n)
    np_growth_vals = np.zeros(n)
    for i in range(1, n):
        rev_growth_vals[i] = round(safe_div(revenue[i] - revenue[i-1], revenue[i-1])[()] * 100, 1)
        np_growth_vals[i] = round(safe_div(net_profit[i] - net_profit[i-1], net_profit[i-1])[()] * 100, 1)

    # 现金流
    ocf_ni_vals = np.round(safe_div(ocf, net_profit), 2)
    fcf_vals = np.round(ocf - capex, 1)

    all_raw = {
        "ROE": list(roe_vals),
        "毛利率": list(gross_margin_vals),
        "净利率": list(net_margin_vals),
        "流动比率": list(cur_ratio_vals),
        "资产负债率": list(debt_ratio_vals),
        "存货周转率": list(inv_turnover_vals),
        "应收周转率": list(ar_turnover_vals),
        "收入增长率": list(rev_growth_vals),
        "净利增长率": list(np_growth_vals),
        "经营现金流/净利润": list(ocf_ni_vals),
        "自由现金流": list(fcf_vals),
    }

    # 组装结果
    result = {}
    for dim, indicators in KPI_DIMENSIONS.items():
        result[dim] = {}
        for ind in indicators:
            vals = all_raw[ind]
            current = vals[-1] if vals else 0
            yoy = round(current - (vals[-2] if len(vals) > 1 else current), 2)
            status = _judge_status(ind, current, industry)

            result[dim][ind] = {
                "values": vals,
                "current": current,
                "yoy": yoy,
                "status": status,
                "trend": "up" if len(vals) >= 3 and vals[-1] > vals[-3] else ("down" if len(vals) >= 3 and vals[-1] < vals[-3] else "stable"),
                "unit": DEFAULT_THRESHOLDS.get(ind, {}).get("unit", ""),
                "benchmark_mean": industry.get(ind, {}).get("mean", 0),
            }

    return result


def _judge_status(indicator: str, value: float, industry: dict) -> str:
    thresholds = DEFAULT_THRESHOLDS.get(indicator, {})
    mean_val = industry.get(indicator, {}).get("mean", 0)
    std_val = industry.get(indicator, {}).get("std", 1)

    if indicator == "资产负债率":
        if value > thresholds.get("red_high", 80):
            return "danger"
        if value > thresholds.get("yellow_high", 65):
            return "warning"
        return "normal"

    yellow_low = thresholds.get("yellow_low", mean_val - 0.5 * std_val)
    red_low = thresholds.get("red_low", mean_val - 1.5 * std_val)

    if value < red_low:
        return "danger"
    if value < yellow_low:
        return "warning"
    return "normal"


def get_alert_summary(kpi_results: dict) -> list:
    alerts = []
    for dim, indicators in kpi_results.items():
        for name, data in indicators.items():
            if data["status"] in ("warning", "danger"):
                alerts.append({
                    "dim": dim,
                    "indicator": KPI_NAMES_CN.get(name, name),
                    "status": data["status"],
                    "value": f"{data['current']}{data['unit']}",
                    "key": name,
                })
    return alerts


def _empty_kpi_result() -> dict:
    result = {}
    for dim, indicators in KPI_DIMENSIONS.items():
        result[dim] = {}
        for ind in indicators:
            result[dim][ind] = {
                "values": [], "current": 0, "yoy": 0,
                "status": "normal", "trend": "stable",
                "unit": "", "benchmark_mean": 0,
            }
    return result
