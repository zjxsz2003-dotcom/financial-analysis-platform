"""
报告生成模块 v2 — 适配CSMAR DataFrame
"""
import pandas as pd
from modules.data_loader import get_company_name, get_years, get_income, get_balance, get_cashflow
from modules.kpi_engine import calc_all_kpis, get_alert_summary
from modules.budget_analysis import get_budget_vs_actual, get_revenue_deviation_df
from modules.strategy_tracker import get_strategy_progress_data
from modules.llm_writer import generate_report_summary
from config import KPI_NAMES_CN


def build_report_data(report_type: str, period: str) -> dict:
    company = get_company_name()
    years = get_years()
    latest = years[-1]
    inc = get_income()
    bs = get_balance()
    kpis = calc_all_kpis()

    # 核心指标亮点
    rev = float(inc[inc["年份"] == latest]["营业收入"].values[0]) if inc is not None and not inc[inc["年份"] == latest].empty else 0
    prev_idx = len(years) - 2
    prev_rev = float(inc[inc["年份"] == years[prev_idx]]["营业收入"].values[0]) if prev_idx >= 0 and inc is not None else rev
    np_val = float(inc[inc["年份"] == latest]["净利润"].values[0]) if inc is not None and not inc[inc["年份"] == latest].empty else 0
    prev_np = float(inc[inc["年份"] == years[prev_idx]]["净利润"].values[0]) if prev_idx >= 0 and inc is not None else np_val
    equity_val = float(bs[bs["年份"] == latest]["股东权益合计"].values[0]) if bs is not None and not bs[bs["年份"] == latest].empty else 1
    roe = round(np_val / equity_val * 100, 1)
    total_assets = float(bs[bs["年份"] == latest]["资产总计"].values[0]) if bs is not None and not bs[bs["年份"] == latest].empty else 0

    highlights = {
        "营业收入": f"{rev:.0f}亿元（同比{round((rev-prev_rev)/prev_rev*100,1):+.1f}%）",
        "净利润": f"{np_val:.1f}亿元（同比{round((np_val-prev_np)/prev_np*100,1):+.1f}%）",
        "ROE": f"{roe:.1f}%",
        "总资产": f"{total_assets:.0f}亿元",
        "经营现金流/净利润": f"{kpis['现金流质量']['经营现金流/净利润']['current']:.2f}",
    }

    alerts = get_alert_summary(kpis)

    type_cn = {"monthly": "月度经营快报", "quarterly": "季度经营分析报告", "annual": "年度综合经营报告"}
    ai_result = generate_report_summary(company, period, type_cn.get(report_type, ""), highlights, alerts)

    sections = []

    # 1. 核心指标
    kpi_rows = []
    for dim, indicators in kpis.items():
        for name, data in indicators.items():
            kpi_rows.append({
                "维度": dim, "指标": KPI_NAMES_CN.get(name, name),
                "当前值": f"{data['current']}{data['unit']}",
                "同比": f"{data['yoy']:+.2f}{data['unit']}",
                "状态": {"normal":"正常","warning":"关注","danger":"预警"}.get(data["status"]),
            })
    sections.append({
        "heading": "一、核心指标概览",
        "body": f"截至{period}，公司实现营业收入{rev:.0f}亿元，净利润{np_val:.1f}亿元，ROE为{roe:.1f}%。",
        "table": pd.DataFrame(kpi_rows),
    })

    # 2. 预警
    if alerts:
        alert_body = "以下指标触发预警：\n" + "\n".join(
            [f"- {'🔴' if a['status']=='danger' else '🟡'} [{a['dim']}] {a['indicator']}：{a['value']}" for a in alerts]
        )
    else:
        alert_body = "本期所有指标均处于正常区间。"
    sections.append({"heading": "二、预警清单", "body": alert_body})

    # 3. 预算
    bv = get_budget_vs_actual()
    budget_body = "各业务板块收入预算执行：\n" + "\n".join([
        f"- {'🔴' if i['偏差率']<-5 else ('🟡' if i['偏差率']<0 else '🟢')} {biz}：实际{i['实际']:.0f}亿 vs 预算{i['预算']:.0f}亿（{i['偏差率']:+.1f}%）"
        for biz, i in bv.get("收入", {}).items()
    ])
    sections.append({"heading": "三、预算执行情况", "body": budget_body, "table": get_revenue_deviation_df()})

    # 4. 战略
    sd = get_strategy_progress_data()
    strategy_body = "年度战略目标进度：\n" + "\n".join([
        f"- {'🔴' if s['status']=='danger' else ('🟡' if s['status']=='warning' else '🟢')} {s['name']}：{s['progress']:.1f}%（{s['current_value']}{s['unit']}/{s['target_value']}{s['unit']}）"
        for s in sd
    ])
    sections.append({"heading": "四、战略目标追踪", "body": strategy_body})

    return {
        "title": f"{company}{type_cn.get(report_type, '经营分析报告')}",
        "period": period,
        "company": company,
        "sections": sections,
        "ai_summary": ai_result,
        "highlights": highlights,
        "alerts": alerts,
    }
