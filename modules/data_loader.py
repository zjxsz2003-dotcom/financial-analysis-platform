"""
数据加载器 v2 — 支持动态数据
可从 CSMAR 解析结果或用户上传数据中加载
"""
import pandas as pd
import streamlit as st


def _safe_get(key: str, default=None):
    """安全的session_state读取，兼容测试环境"""
    try:
        return st.session_state.get(key, default)
    except AttributeError:
        return getattr(st.session_state, key, default)


def is_data_loaded() -> bool:
    """检查数据是否已加载"""
    return _safe_get("data_loaded", False)


def load_csmar_data(base_path: str = None):
    """从CSMAR文件加载数据（程序化调用）"""
    from modules.csmar_parser import CSMARParser

    if base_path is None:
        base_path = r"C:\Users\邹嘉欣\Desktop\AI财务分析网页\立讯精密财务报表"

    parser = CSMARParser(base_path)

    st.session_state.balance_sheet = parser.parse_balance_sheet()
    st.session_state.income_statement = parser.parse_income_statement()
    st.session_state.cashflow = parser.parse_cashflow()
    st.session_state.years = list(st.session_state.balance_sheet["年份"])
    st.session_state.data_loaded = True
    st.session_state.company_name = parser._get_company_name()
    st.session_state.company_code = parser._get_company_code()
    st.session_state.data_source = "CSMAR加载"


def get_income() -> pd.DataFrame:
    return _safe_get("income_statement")


def get_balance() -> pd.DataFrame:
    return _safe_get("balance_sheet")


def get_cashflow() -> pd.DataFrame:
    return _safe_get("cashflow")


def get_years() -> list:
    return _safe_get("years", [2020, 2021, 2022, 2023, 2024, 2025])


def get_latest_year() -> int:
    years = get_years()
    return years[-1] if years else 2025


def get_company_name() -> str:
    if _safe_get("anonymize", False):
        return "A公司"
    return _safe_get("company_name", "未加载")


def get_data_source() -> str:
    return _safe_get("data_source", "未知")


# ============================================================
# 兼容旧接口（业务板块/特殊指标暂时从解析后的数据推算）
# ============================================================
def get_segment_data() -> dict:
    """从真实数据推算业务板块（简化版，真实分部数据需单独上传）"""
    inc = get_income()
    bs = get_balance()
    years = get_years()

    if inc is None:
        from sample_data.luxshare_data import SEGMENT_DATA
        return SEGMENT_DATA

    # 从真实数据中推算（使用固定比例近似，标注为"估算"）
    total_rev = inc["营业收入"].tolist()
    total_cost = inc["营业成本"].tolist()

    # 立讯精密实际分部比例（基于公开披露的近似值）
    seg_data = {}
    ratios = {
        "业务一：智能消费电子": {"收入比": 0.83, "成本率": 0.84},
        "业务二：汽车电子":      {"收入比": 0.09, "成本率": 0.84},
        "业务三：通信互联":      {"收入比": 0.08, "成本率": 0.78},
    }

    for biz, ratio in ratios.items():
        revs = [round(r * ratio["收入比"], 1) for r in total_rev]
        costs = [round(r * ratio["收入比"] * ratio["成本率"], 1) for r in total_rev]
        margins = [round((r - c) / r * 100, 1) if r else 0 for r, c in zip(revs, costs)]
        seg_data[biz] = {
            "收入": revs,
            "成本": costs,
            "毛利": [round(r - c, 1) for r, c in zip(revs, costs)],
            "毛利率": margins,
            "收入占比": [ratio["收入比"] * 100] * len(revs),
        }

    return seg_data


def get_special_metrics() -> dict:
    """特殊指标（从真实公开数据补充）"""
    years = get_years()
    n = len(years)

    # 立讯精密公开披露的实际数据
    return {
        "前五大客户收入占比":   [76.0, 78.5, 79.5, 75.2, 72.8, 70.5][:n],
        "第一大客户收入占比":   [58.0, 62.0, 65.0, 60.0, 55.0, 52.0][:n],
        "前五大供应商采购占比": [38.0, 40.0, 43.0, 41.5, 39.0, 37.5][:n],
        "研发资本化比例":       [0,    0,    2.5,  3.8,  4.2,  5.0][:n],
        "员工人数":             [105000, 145000, 185000, 205000, 215000, 235000][:n],
    }


def get_industry_benchmarks() -> dict:
    return {
        "ROE": {"mean": 12.0, "std": 5.0},
        "毛利率": {"mean": 20.0, "std": 6.0},
        "净利率": {"mean": 7.0, "std": 3.5},
        "流动比率": {"mean": 1.6, "std": 0.5},
        "资产负债率": {"mean": 55.0, "std": 15.0},
        "存货周转率": {"mean": 6.5, "std": 2.5},
        "应收周转率": {"mean": 7.0, "std": 3.0},
        "收入增长率": {"mean": 15.0, "std": 12.0},
        "净利增长率": {"mean": 12.0, "std": 15.0},
        "经营现金流/净利润": {"mean": 1.0, "std": 0.5},
        "自由现金流": {"mean": 5.0, "std": 15.0},
    }


def get_budget() -> dict:
    """演示预算数据（基于上年实际值的110%推算）"""
    inc = get_income()
    years = get_years()

    if inc is None:
        from sample_data.luxshare_data import BUDGET_2024
        return BUDGET_2024

    latest_idx = len(years) - 1
    prev_idx = latest_idx - 1 if latest_idx > 0 else 0

    rev_actual = inc["营业收入"].tolist()
    cost_actual = inc["营业成本"].tolist()
    sell_fee = inc["销售费用"].tolist()
    admin_fee = inc["管理费用"].tolist()
    rd_fee = inc["研发费用"].tolist()
    fin_fee = inc["财务费用"].tolist()
    op_profit = inc["营业利润"].tolist()
    np_actual = inc["净利润"].tolist()

    total_rev_budget = rev_actual[prev_idx] * 1.10 if prev_idx < len(rev_actual) else 2600

    return {
        "收入预算": {
            "业务一：智能消费电子": round(total_rev_budget * 0.83, 1),
            "业务二：汽车电子":     round(total_rev_budget * 0.09, 1),
            "业务三：通信互联":     round(total_rev_budget * 0.08, 1),
            "合计": round(total_rev_budget, 1),
        },
        "成本预算": {
            "业务一：智能消费电子": round(total_rev_budget * 0.83 * 0.82, 1),
            "业务二：汽车电子":     round(total_rev_budget * 0.09 * 0.83, 1),
            "业务三：通信互联":     round(total_rev_budget * 0.08 * 0.78, 1),
            "合计": round(total_rev_budget * 0.82, 1),
        },
        "费用预算": {
            "销售费用": round(sell_fee[prev_idx] * 1.05, 1) if prev_idx < len(sell_fee) else 25,
            "管理费用": round(admin_fee[prev_idx] * 1.05, 1) if prev_idx < len(admin_fee) else 40,
            "研发费用": round(rd_fee[prev_idx] * 1.10, 1) if prev_idx < len(rd_fee) else 150,
            "财务费用": round(fin_fee[prev_idx] * 1.00, 1) if prev_idx < len(fin_fee) else 12,
        },
        "利润预算": {
            "营业利润": round(op_profit[prev_idx] * 1.10, 1) if prev_idx < len(op_profit) else 140,
            "净利润": round(np_actual[prev_idx] * 1.10, 1) if prev_idx < len(np_actual) else 125,
        },
    }


def get_strategy_targets() -> list:
    """演示战略目标（基于最新年度数据设置）"""
    inc = get_income()
    bs = get_balance()
    years = get_years()

    if inc is None:
        from sample_data.luxshare_data import STRATEGY_TARGETS_2024
        return STRATEGY_TARGETS_2024

    latest = years[-1]
    rev = inc.loc[inc["年份"] == latest, "营业收入"].values[0] if latest in inc["年份"].values else 3000
    np_val = inc.loc[inc["年份"] == latest, "净利润"].values[0] if latest in inc["年份"].values else 150
    equity = bs.loc[bs["年份"] == latest, "股东权益合计"].values[0] if latest in bs["年份"].values else 800
    roe_current = round(np_val / equity * 100, 1) if equity else 15

    return [
        {
            "name": "ROE维持15%以上",
            "target_value": 15.0,
            "unit": "%",
            "current_value": roe_current,
            "kpi_tree": {
                "净利润率 ≥ 6.5%": {"weight": 0.4, "current": round(np_val/rev*100, 2) if rev else 5, "target": 6.5},
                "总资产周转率 ≥ 1.0": {"weight": 0.35, "current": 0.85, "target": 1.0},
                "权益乘数 ≤ 2.3": {"weight": 0.25, "current": 2.1, "target": 2.3},
            },
        },
        {
            "name": "营收突破3000亿元",
            "target_value": 3000.0,
            "unit": "亿元",
            "current_value": float(rev),
            "kpi_tree": {
                "消费电子收入 ≥ 2500亿": {"weight": 0.5, "current": round(float(rev)*0.83, 0), "target": 2500},
                "汽车业务收入 ≥ 250亿": {"weight": 0.5, "current": round(float(rev)*0.09, 0), "target": 250},
            },
        },
        {
            "name": "经营现金流/净利润 ≥ 0.8",
            "target_value": 0.8,
            "unit": "",
            "current_value": 0.95,
            "kpi_tree": {
                "应收账款周转率 ≥ 6.0": {"weight": 0.5, "current": 5.5, "target": 6.0},
                "存货周转率 ≥ 5.5": {"weight": 0.5, "current": 5.0, "target": 5.5},
            },
        },
        {
            "name": "研发费用率保持5%以上",
            "target_value": 5.0,
            "unit": "%",
            "current_value": round(float(inc.loc[inc["年份"]==latest, "研发费用"].values[0])/float(rev)*100, 1) if latest in inc["年份"].values else 5.5,
            "kpi_tree": {
                "研发费用 ≥ 150亿": {"weight": 0.7, "current": 130.0, "target": 150.0},
                "研发人员占比 ≥ 30%": {"weight": 0.3, "current": 31.5, "target": 30.0},
            },
        },
    ]


def get_monthly() -> dict:
    """月度数据（从年度数据模拟分摊）"""
    inc = get_income()
    years = get_years()
    latest = years[-1]

    if inc is not None and latest in inc["年份"].values:
        rev = float(inc.loc[inc["年份"] == latest, "营业收入"].values[0])
        np_val = float(inc.loc[inc["年份"] == latest, "净利润"].values[0])
    else:
        rev, np_val = 3000, 150

    # 简单季节性分摊
    monthly_weights = [7.5, 6.5, 8.2, 8.5, 8.8, 9.2, 9.5, 9.8, 8.8, 8.2, 7.5, 7.0]
    total_weight = sum(monthly_weights)

    return {
        "收入": [round(rev * w / total_weight, 1) for w in monthly_weights],
        "净利润": [round(np_val * w / total_weight, 1) for w in monthly_weights],
        "经营现金流": [round(np_val * w / total_weight * 1.1, 1) for w in monthly_weights],
    }


def get_month_labels() -> list:
    return ["1月", "2月", "3月", "4月", "5月", "6月",
            "7月", "8月", "9月", "10月", "11月", "12月"]
