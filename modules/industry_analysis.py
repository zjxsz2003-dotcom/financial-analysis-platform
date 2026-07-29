"""
行业对比分析模块
"""
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from config import COLORS, ALERT_COLORS


def get_radar_chart(company_values: dict, industry_values: dict, dimensions: list) -> go.Figure:
    """五维雷达图：公司 vs 行业"""
    fig = go.Figure()

    company_vals = [company_values.get(d, 0) for d in dimensions]
    industry_vals = [industry_values.get(d, 0) for d in dimensions]

    # 归一化到0-100
    max_vals = [max(abs(company_vals[i]), abs(industry_vals[i]), 1) for i in range(len(dimensions))]
    company_norm = [min(company_vals[i] / max_vals[i] * 100, 100) for i in range(len(dimensions))]
    industry_norm = [min(industry_vals[i] / max_vals[i] * 100, 100) for i in range(len(dimensions))]

    fig.add_trace(go.Scatterpolar(r=company_norm, theta=dimensions, name="立讯精密",
        fill="toself", line=dict(color=COLORS["ember"], width=2),
        fillcolor="rgba(44,95,138,0.2)"))
    fig.add_trace(go.Scatterpolar(r=industry_norm, theta=dimensions, name="行业均值",
        fill="toself", line=dict(color=COLORS["amber"], width=2, dash="dash"),
        fillcolor="rgba(230,126,34,0.1)"))

    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 105])),
        height=300, margin=dict(l=20,r=20,t=30,b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, font=dict(size=9)),
        title=dict(text="五维雷达图：公司 vs 行业", font=dict(size=12)), font=dict(size=9))
    return fig


def get_industry_comparison_table(company_kpis: dict, industry_benchmarks: dict) -> pd.DataFrame:
    """行业对标表格"""
    rows = []
    for dim, indicators in company_kpis.items():
        for name, data in indicators.items():
            bench = industry_benchmarks.get(name, {})
            mean_val = bench.get("mean", 0)
            diff = round(data["current"] - mean_val, 2)
            position = "高于行业" if diff > 0 else ("低于行业" if diff < 0 else "持平")
            rows.append({
                "维度": dim,
                "指标": name,
                "本公司": f"{data['current']}{data.get('unit','')}",
                "行业均值": f"{mean_val}{data.get('unit','')}",
                "差异": f"{diff:+.2f}{data.get('unit','')}",
                "行业位置": position,
                "评价": "👍" if diff > 0 else ("⚠️" if abs(diff) > mean_val * 0.3 else "➖"),
            })
    return pd.DataFrame(rows)


# 行业政策/动态数据（预置示例，实际使用时通过web-access动态获取）
INDUSTRY_NEWS_DEMO = [
    {
        "date": "2025-07",
        "category": "政策法规",
        "title": "工信部发布《电子信息制造业2025-2027年行动计划》",
        "impact": "利好消费电子+通信设备产业链，强调自主可控和AI终端创新",
        "source": "工信部官网",
    },
    {
        "date": "2025-06",
        "category": "技术动向",
        "title": "苹果Vision Pro第二代量产启动，立讯为主要组装供应商",
        "impact": "有望贡献2026年收入增量约80-120亿元，但初期毛利率承压",
        "source": "供应链调研",
    },
    {
        "date": "2025-05",
        "category": "竞争格局",
        "title": "歌尔股份大举扩产VR/MR产能，与立讯形成直接竞争",
        "impact": "智能消费电子领域竞争加剧，需关注份额变化和价格压力",
        "source": "公司公告/行业研报",
    },
    {
        "date": "2025-04",
        "category": "市场动向",
        "title": "全球新能源汽车渗透率突破25%，带动车载连接器+域控制器需求爆发",
        "impact": "立讯汽车业务有望持续高增长(30%+)，但需警惕整车厂压价压力",
        "source": "IEA/乘联会",
    },
    {
        "date": "2025-03",
        "category": "政策法规",
        "title": "美国对华加征消费电子关税至25%，苹果供应链面临重新评估",
        "impact": "短期增加出口成本，中长期推动海外产能布局(越南/印度)",
        "source": "美国贸易代表办公室",
    },
    {
        "date": "2025-01",
        "category": "技术动向",
        "title": "AI服务器高速连接器需求暴增，800G光模块进入规模交付期",
        "impact": "通信互联业务受益于AI算力投资周期，高毛利产品占比有望提升",
        "source": "行业研报/LightCounting",
    },
]
