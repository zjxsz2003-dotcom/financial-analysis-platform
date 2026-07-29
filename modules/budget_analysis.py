"""
预算偏差分析模块 v2 — 适配CSMAR DataFrame
"""
import pandas as pd
import plotly.graph_objects as go
from modules.data_loader import get_budget, get_segment_data, get_income, get_years
from config import COLORS


def get_budget_vs_actual() -> dict:
    budget = get_budget()
    seg = get_segment_data()
    inc = get_income()
    years = get_years()

    result = {}

    # 收入预算偏差
    income_budget = budget.get("收入预算", {})
    result["收入"] = {}
    for biz in income_budget:
        if biz == "合计":
            continue
        b = income_budget[biz]
        a = seg[biz]["收入"][-1] if biz in seg else b * 0.95
        dev = a - b
        dev_pct = round(dev / b * 100, 1) if b else 0
        result["收入"][biz] = {
            "预算": b, "实际": a, "偏差": dev, "偏差率": dev_pct,
            "status": "danger" if dev_pct < -5 else ("warning" if dev_pct < 0 else "normal")
        }

    # 成本预算偏差
    cost_budget = budget.get("成本预算", {})
    result["成本"] = {}
    for biz in cost_budget:
        if biz == "合计":
            continue
        b = cost_budget[biz]
        a = seg[biz]["成本"][-1] if biz in seg else b * 1.02
        dev = a - b
        dev_pct = round(dev / b * 100, 1) if b else 0
        result["成本"][biz] = {
            "预算": b, "实际": a, "偏差": dev, "偏差率": dev_pct,
            "status": "danger" if dev_pct > 5 else ("warning" if dev_pct > 0 else "normal")
        }

    # 费用预算
    fee_budget = budget.get("费用预算", {})
    latest = years[-1]
    fee_actual = {}
    if inc is not None:
        row = inc[inc["年份"] == latest]
        if not row.empty:
            fee_actual = {
                "销售费用": float(row["销售费用"].values[0]) if "销售费用" in row.columns else 0,
                "管理费用": float(row["管理费用"].values[0]) if "管理费用" in row.columns else 0,
                "研发费用": float(row["研发费用"].values[0]) if "研发费用" in row.columns else 0,
                "财务费用": float(row["财务费用"].values[0]) if "财务费用" in row.columns else 0,
            }
    result["费用"] = {}
    for fee_name in fee_budget:
        b = fee_budget[fee_name]
        a = fee_actual.get(fee_name, b)
        dev = a - b
        dev_pct = round(dev / b * 100, 1) if b else 0
        result["费用"][fee_name] = {
            "预算": b, "实际": a, "偏差": dev, "偏差率": dev_pct,
            "status": "danger" if dev_pct > 10 else ("warning" if dev_pct > 5 else "normal")
        }

    # 利润预算
    profit_budget = budget.get("利润预算", {})
    np_actual_val = float(inc[inc["年份"] == latest]["净利润"].values[0]) if inc is not None and not inc[inc["年份"] == latest].empty else 0
    op_actual_val = float(inc[inc["年份"] == latest]["营业利润"].values[0]) if inc is not None and not inc[inc["年份"] == latest].empty else 0
    op_budget_val = profit_budget.get("营业利润", op_actual_val)
    np_budget_val = profit_budget.get("净利润", np_actual_val)

    result["利润"] = {
        "营业利润": {
            "预算": op_budget_val, "实际": op_actual_val,
            "偏差": op_actual_val - op_budget_val,
            "偏差率": round((op_actual_val - op_budget_val) / op_budget_val * 100, 1) if op_budget_val else 0,
            "status": "normal" if op_actual_val >= op_budget_val else "warning"
        },
        "净利润": {
            "预算": np_budget_val, "实际": np_actual_val,
            "偏差": np_actual_val - np_budget_val,
            "偏差率": round((np_actual_val - np_budget_val) / np_budget_val * 100, 1) if np_budget_val else 0,
            "status": "normal" if np_actual_val >= np_budget_val else "warning"
        },
    }

    return result


def get_budget_waterfall_chart() -> go.Figure:
    budget = get_budget()
    seg = get_segment_data()

    income_budget = budget.get("收入预算", {})
    total_budget = income_budget.get("合计", sum(v for k, v in income_budget.items() if k != "合计"))

    items = ["预算总收入"]
    values = [total_budget]

    for biz, data in seg.items():
        budget_val = income_budget.get(biz, 0)
        actual_val = data["收入"][-1]
        dev = actual_val - budget_val
        short_name = biz.replace("业务一：","").replace("业务二：","").replace("业务三：","")[:8]
        items.append(f"{short_name}\n{dev:+.0f}亿")
        values.append(dev)

    actual_total = sum(data["收入"][-1] for data in seg.values())
    items.append("实际总收入")
    values.append(actual_total)

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute"] + ["relative"] * (len(items) - 2) + ["total"],
        x=items, y=values,
        text=[f"{v:.0f}亿" for v in values],
        textposition="outside",
        connector={"line": {"color": COLORS["border"]}},
        increasing={"marker": {"color": COLORS["green"]}},
        decreasing={"marker": {"color": COLORS["red"]}},
        totals={"marker": {"color": COLORS["accent"]}},
    ))
    fig.update_layout(
        title=dict(text=f"收入预算偏差瀑布图", font=dict(size=12)),
        height=260,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=10),
    )
    return fig


def get_revenue_deviation_df() -> pd.DataFrame:
    bv = get_budget_vs_actual()
    rows = []
    for biz, info in bv.get("收入", {}).items():
        rows.append({
            "业务板块": biz,
            "预算收入(亿元)": round(info["预算"], 1),
            "实际收入(亿元)": round(info["实际"], 1),
            "偏差(亿元)": round(info["偏差"], 1),
            "偏差率(%)": info["偏差率"],
            "状态": info["status"],
        })
    return pd.DataFrame(rows)


def get_cost_deviation_df() -> pd.DataFrame:
    bv = get_budget_vs_actual()
    rows = []
    for biz, info in bv.get("成本", {}).items():
        rows.append({
            "业务板块": biz,
            "预算成本(亿元)": round(info["预算"], 1),
            "实际成本(亿元)": round(info["实际"], 1),
            "偏差(亿元)": round(info["偏差"], 1),
            "偏差率(%)": info["偏差率"],
            "状态": info["status"],
        })
    return pd.DataFrame(rows)
