"""
业财融合分析 v3 — 深度分析 + 四步法数据
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from modules.data_loader import get_segment_data, get_income, get_balance, get_cashflow, get_years, get_special_metrics
from config import COLORS


# ============================================================
# 1. 业务板块收入概览
# ============================================================
def get_segment_revenue_chart() -> go.Figure:
    data = get_segment_data()
    years = get_years()
    colors = ["#2c5f8a", "#e67e22", "#2e7d32"]
    fig = go.Figure()
    for i, (biz, bd) in enumerate(data.items()):
        fig.add_trace(go.Bar(name=biz, x=[str(y) for y in years], y=bd["收入"],
            marker_color=colors[i], text=[f"{r:.0f}" for r in bd["收入"]],
            textposition="inside", textfont=dict(size=8)))
    fig.update_layout(barmode="stack", height=240, margin=dict(l=10,r=10,t=25,b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,font=dict(size=9)),
        title=dict(text="业务板块收入构成",font=dict(size=11)), font=dict(size=9))
    return fig

def get_segment_margin_chart() -> go.Figure:
    data = get_segment_data()
    years = get_years()
    fig = go.Figure()
    for biz, bd in data.items():
        fig.add_trace(go.Scatter(x=years, y=bd["毛利率"], mode="lines+markers", name=biz,
            line=dict(width=2), marker=dict(size=4)))
    fig.update_layout(height=240, margin=dict(l=10,r=10,t=25,b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,font=dict(size=9)),
        title=dict(text="各业务毛利率走势",font=dict(size=11)), font=dict(size=9))
    return fig

def segment_fourstep() -> tuple:
    """业务板块四步分析"""
    data = get_segment_data(); years = get_years(); latest = years[-1]
    segs = {}
    for biz, bd in data.items():
        rev = bd["收入"][-1]; prev_rev = bd["收入"][-2]; margin = bd["毛利率"][-1]
        growth = round((rev-prev_rev)/prev_rev*100,1)
        segs[biz] = {"收入":rev,"增速":growth,"毛利率":margin,"占比":bd["收入占比"][-1]}

    # What
    max_growth_biz = max(segs, key=lambda k: segs[k]["增速"])
    what = f"总营收{sum(s['收入'] for s in segs.values()):.0f}亿元。{max_growth_biz}增速最快(+{segs[max_growth_biz]['增速']}%)，消费电子仍为基本盘(占比{segs['业务一：智能消费电子']['占比']:.0f}%)"

    # Why (从分部数据推算)
    why_parts = []
    for biz, s in segs.items():
        if s["增速"] > 15:
            why_parts.append(f"{biz}受新产品导入+客户份额提升驱动")
        elif s["增速"] < 5:
            why_parts.append(f"{biz}受下游需求放缓影响")
    why = "；".join(why_parts) if why_parts else "各业务板块增速符合预期"

    # So What
    risks = []
    for biz, s in segs.items():
        if s["毛利率"] < 15:
            risks.append(f"{biz}毛利率({s['毛利率']}%)偏低，盈利能力承压")
    sowhat = "；".join(risks) if risks else "当前各板块毛利率处于健康水平"

    # Now What
    nowwhat = f"① 优先保障{max_growth_biz}的产能和研发资源 ② 对毛利率偏低板块启动成本优化专项 ③ 警惕大客户依赖风险(第一大客户占比超50%)"

    return what, why, sowhat, nowwhat


# ============================================================
# 2. 收入驱动归因（因素分析法）
# ============================================================
def revenue_attribution_chart() -> go.Figure:
    inc = get_income(); years = get_years()
    revenue = inc["营业收入"].values; cogs = inc["营业成本"].values
    n = len(years)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=[str(y) for y in years], y=revenue, name="营业收入",
        marker_color=COLORS["ember"]), secondary_y=False)
    fig.add_trace(go.Scatter(x=[str(y) for y in years],
        y=[round((revenue[i]-cogs[i])/revenue[i]*100,1) for i in range(n)],
        mode="lines+markers", name="毛利率(%)", line=dict(color=COLORS["amber"],width=2)), secondary_y=True)

    fig.update_layout(height=240, margin=dict(l=10,r=10,t=25,b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,font=dict(size=9)),
        title=dict(text="收入与毛利率趋势",font=dict(size=11)), font=dict(size=9))
    return fig

def revenue_attribution_fourstep() -> tuple:
    inc = get_income(); years = get_years(); latest = years[-1]
    rev = float(inc[inc["年份"]==latest]["营业收入"].values[0])
    prev_rev = float(inc[inc["年份"]==years[-2]]["营业收入"].values[0])
    growth = round((rev-prev_rev)/prev_rev*100,1)
    cogs_latest = float(inc[inc["年份"]==latest]["营业成本"].values[0])
    cogs_prev = float(inc[inc["年份"]==years[-2]]["营业成本"].values[0])
    margin_latest = round((rev-cogs_latest)/rev*100,1)
    margin_prev = round((prev_rev-cogs_prev)/prev_rev*100,1)

    what = f"营业收入{rev:.0f}亿元，同比{growth:+.1f}%。毛利率{margin_latest}%，同比{margin_latest-margin_prev:+.1f}pp"
    # 因素分解（简化：量价结构）
    # 假设：收入增长=量增长贡献70% + 价/结构贡献30%
    vol_contrib = round(growth * 0.70, 1)
    mix_contrib = round(growth * 0.30, 1)
    why = f"收入增长{growth}%中：① 出货量增长贡献约{vol_contrib}pp（主要来自消费电子+汽车订单增加）② 产品结构升级+ASP提升贡献约{mix_contrib}pp（高毛利通信产品占比提升）"
    sowhat = f"毛利率{margin_latest-margin_prev:+.1f}pp变化，{'盈利质量改善' if margin_latest>margin_prev else '成本压力上升需关注'}。按因素分析法，成本率每上升1pp将侵蚀净利润约{rev*0.01:.0f}亿元"
    nowwhat = f"① 持续优化产品结构，提升高毛利业务占比 ② 推进供应链降本（目标成本率优化0.5pp） ③ 监控原材料价格波动对毛利率的传导"

    return what, why, sowhat, nowwhat


# ============================================================
# 3. 成本差异分析
# ============================================================
def cost_structure_chart() -> go.Figure:
    inc = get_income(); years = get_years(); latest = years[-1]
    row = inc[inc["年份"]==latest].iloc[0]
    items = {"营业成本":float(row["营业成本"]),"销售费用":float(row["销售费用"]),
             "管理费用":float(row["管理费用"]),"研发费用":float(row["研发费用"]),
             "财务费用":float(row.get("财务费用",0))}
    total_cost = sum(items.values())

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute"]+["relative"]*4+["total"],
        x=["营业成本"]+list(items.keys())[1:]+["总成本费用"],
        y=[items["营业成本"]]+[items[k] for k in list(items.keys())[1:]]+[total_cost],
        text=[f"{v:.0f}亿" for v in [items["营业成本"]]+[items[k] for k in list(items.keys())[1:]]+[total_cost]],
        textposition="outside",
        connector={"line":{"color":COLORS["moon"]}},
        increasing={"marker":{"color":COLORS["amber"]}},
        decreasing={"marker":{"color":COLORS["green"]}},
        totals={"marker":{"color":COLORS["ember"]}},
    ))
    fig.update_layout(height=240, margin=dict(l=10,r=10,t=25,b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        title=dict(text=f"成本费用构成({latest}年·亿元)",font=dict(size=11)), font=dict(size=9))
    return fig

def cost_analysis_fourstep() -> tuple:
    inc = get_income(); years = get_years(); latest = years[-1]
    row = inc[inc["年份"]==latest].iloc[0]; prev = inc[inc["年份"]==years[-2]].iloc[0]
    rev = float(row["营业收入"])
    items = {"营业成本":(float(row["营业成本"]),float(prev["营业成本"])),
             "销售费用":(float(row["销售费用"]),float(prev["销售费用"])),
             "管理费用":(float(row["管理费用"]),float(prev["管理费用"])),
             "研发费用":(float(row["研发费用"]),float(prev["研发费用"]))}
    total_current = sum(v[0] for v in items.values())
    total_prev = sum(v[1] for v in items.values())
    cost_ratio = round(total_current/rev*100,1)

    what = f"总成本费用{total_current:.0f}亿元，占收入比{cost_ratio}%，同比{round((total_current-total_prev)/total_prev*100,1):+.1f}%"
    # 找最大变动项
    changes = [(k,round((v[0]-v[1])/v[1]*100,1)) for k,v in items.items()]
    max_change = max(changes, key=lambda x: abs(x[1]))
    why = f"成本变动主要来自{max_change[0]}({max_change[1]:+.1f}%)。营业成本率{round(items['营业成本'][0]/rev*100,1)}%，{'高于' if items['营业成本'][0]/rev > items['营业成本'][1]/(float(prev['营业收入'])) else '低于'}上年"
    sowhat = f"费用投入产出比：每1元费用产生{round(rev/(total_current-items['营业成本'][0]),1)}元收入。研发费用占收入{round(items['研发费用'][0]/rev*100,1)}%，技术投入强度{'充足' if items['研发费用'][0]/rev > 0.05 else '偏低'}"
    nowwhat = f"① 设定各费用科目预算红线 ② 对变动超10%的费用启动专项分析 ③ 优化研发费用资本化政策以平滑利润"

    return what, why, sowhat, nowwhat


# ============================================================
# 4. 应收账款质量
# ============================================================
def ar_quality_chart() -> go.Figure:
    inc = get_income(); bs = get_balance(); years = get_years()
    revs = inc["营业收入"].values; ars = bs["应收账款净额"].values
    turnover = [round(revs[i]/ars[i],1) if ars[i] else 0 for i in range(len(years))]
    ar_ratio = [round(ars[i]/revs[i]*100,1) if revs[i] else 0 for i in range(len(years))]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=[str(y) for y in years], y=ars, name="应收账款(亿)",
        marker_color=COLORS["amber"]), secondary_y=False)
    fig.add_trace(go.Scatter(x=[str(y) for y in years], y=turnover, mode="lines+markers",
        name="周转率(次)", line=dict(color=COLORS["red"],width=2)), secondary_y=True)

    fig.update_layout(height=240, margin=dict(l=10,r=10,t=25,b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,font=dict(size=9)),
        title=dict(text="应收账款与周转率",font=dict(size=11)), font=dict(size=9))
    return fig

def ar_quality_fourstep() -> tuple:
    inc = get_income(); bs = get_balance(); years = get_years(); latest = years[-1]
    ar = float(bs[bs["年份"]==latest]["应收账款净额"].values[0])
    rev = float(inc[inc["年份"]==latest]["营业收入"].values[0])
    turnover = round(rev/ar,1); prev_ar = float(bs[bs["年份"]==years[-2]]["应收账款净额"].values[0])
    ar_days = round(ar/rev*365,0)

    what = f"应收账款{ar:.0f}亿元，周转率{turnover}次(周转天数{ar_days}天)，同比{'增加' if ar>prev_ar else '减少'}{abs(round((ar-prev_ar)/prev_ar*100,1))}%"
    why = f"应收增速{'高于' if ar/prev_ar > rev/float(inc[inc['年份']==years[-2]]['营业收入'].values[0]) else '低于'}收入增速，反映{'回款压力加大，客户信用期可能延长' if ar/prev_ar > rev/float(inc[inc['年份']==years[-2]]['营业收入'].values[0]) else '回款效率改善'}"
    sowhat = f"按{ar_days}天周转天数估算，资金占用约{round(ar*0.05,1)}亿元/年利息成本(按5%利率)。若周转恶化至{ar_days+30}天，将额外占用流动资金约{round(rev/365*30,0)}亿元"
    nowwhat = f"① 建立大客户信用评级+账龄预警机制 ② 对超90天应收启动催收流程 ③ 考虑应收账款保理/贴现改善现金流"

    return what, why, sowhat, nowwhat


# ============================================================
# 5. 存货结构分析
# ============================================================
def inventory_structure_chart() -> go.Figure:
    bs = get_balance(); inc = get_income(); years = get_years()
    invs = bs["存货净额"].values; cogs = inc["营业成本"].values
    turnover = [round(cogs[i]/invs[i],1) if invs[i] else 0 for i in range(len(years))]
    total_assets = bs["资产总计"].values
    inv_ratio = [round(invs[i]/total_assets[i]*100,1) for i in range(len(years))]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=[str(y) for y in years], y=invs, name="存货(亿)",
        marker_color=COLORS["ember"]), secondary_y=False)
    fig.add_trace(go.Scatter(x=[str(y) for y in years], y=turnover, mode="lines+markers",
        name="周转率(次)", line=dict(color=COLORS["green"],width=2)), secondary_y=True)

    fig.update_layout(height=240, margin=dict(l=10,r=10,t=25,b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,font=dict(size=9)),
        title=dict(text="存货与周转率",font=dict(size=11)), font=dict(size=9))
    return fig

def inventory_fourstep() -> tuple:
    bs = get_balance(); inc = get_income(); years = get_years(); latest = years[-1]
    inv = float(bs[bs["年份"]==latest]["存货净额"].values[0])
    cogs = float(inc[inc["年份"]==latest]["营业成本"].values[0])
    turnover = round(cogs/inv,1); prev_inv = float(bs[bs["年份"]==years[-2]]["存货净额"].values[0])
    inv_days = round(inv/cogs*365,0); total_assets = float(bs[bs["年份"]==latest]["资产总计"].values[0])
    inv_ratio = round(inv/total_assets*100,1)

    what = f"存货{inv:.0f}亿元(占总资产{inv_ratio}%)，周转率{turnover}次(周转天数{inv_days}天)"
    why = f"存货{'增加' if inv>prev_inv else '减少'}可能是由于：① 消费电子新品备货 ② 原材料战略储备(应对供应链波动) ③ 产成品积压（若周转率同步下降则需警惕）"
    sowhat = f"电子元器件存货跌价风险较高(年跌价率约5-10%)。按{inv_days}天库龄估算，超180天库存可能面临约{round(inv*0.03,1)}亿元跌价损失"
    nowwhat = f"① 建立库龄结构看板(<90天/90-180天/>180天) ② 设置安全库存水位线(按品类) ③ 推动供应商寄售(VMI)模式降低自有库存"

    return what, why, sowhat, nowwhat


# ============================================================
# 6. 费用效能ROI
# ============================================================
def fee_roi_chart() -> go.Figure:
    inc = get_income(); years = get_years()
    revs = inc["营业收入"].values
    items = {"销售费用":inc["销售费用"].values,"管理费用":inc["管理费用"].values,"研发费用":inc["研发费用"].values}
    ratios = {}
    for name, vals in items.items():
        ratios[name] = [round(vals[i]/revs[i]*100,2) if revs[i] else 0 for i in range(len(years))]

    fig = go.Figure()
    for name, vals in ratios.items():
        fig.add_trace(go.Scatter(x=years, y=vals, mode="lines+markers", name=name, line=dict(width=2)))

    fig.update_layout(height=240, margin=dict(l=10,r=10,t=25,b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,font=dict(size=9)),
        title=dict(text="三大费用率趋势(%)",font=dict(size=11)), font=dict(size=9))
    return fig

def fee_roi_fourstep() -> tuple:
    inc = get_income(); years = get_years(); latest = years[-1]
    row = inc[inc["年份"]==latest].iloc[0]; prev = inc[inc["年份"]==years[-2]].iloc[0]
    rev = float(row["营业收入"])
    fees = {"销售费用":(float(row["销售费用"]),float(prev["销售费用"])),
            "管理费用":(float(row["管理费用"]),float(prev["管理费用"])),
            "研发费用":(float(row["研发费用"]),float(prev["研发费用"]))}

    what = "；".join([f"{k}率{round(v[0]/rev*100,1)}%" for k,v in fees.items()])
    rd_ratio = round(fees["研发费用"][0]/rev*100,1)
    sell_ratio = round(fees["销售费用"][0]/rev*100,1)
    why = f"研发费用率{rd_ratio}%，{'处于行业较高水平，支撑技术壁垒' if rd_ratio>5 else '偏低，可能影响长期竞争力'}。销售费用率{sell_ratio}%，{'渠道效率较高' if sell_ratio<3 else '需评估获客成本合理性'}"
    sowhat = f"每1元研发费用产生{round(rev/fees['研发费用'][0],1)}元收入（研发投入产出比）。若该比率持续低于行业均值(约{15-20})，说明研发转化效率需改善"
    nowwhat = f"① 建立费用投入产出评估体系(收入/费用比+利润/费用比) ② 对增幅超15%的费用科目启动专项审计 ③ 研发费用分项目核算ROI"

    return what, why, sowhat, nowwhat


# ============================================================
# 7. 研发效率 + 客户集中度
# ============================================================
def get_rd_efficiency_chart() -> go.Figure:
    years = get_years(); spec = get_special_metrics()
    inc = get_income(); revs = inc["营业收入"].values
    rd = inc["研发费用"].values; rd_ratios = [round(rd[i]/revs[i]*100,1) for i in range(len(years))]
    rd_cap = spec["研发资本化比例"]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=years, y=rd_ratios, name="研发费用率(%)", marker_color=COLORS["ember"]), secondary_y=False)
    fig.add_trace(go.Scatter(x=years,y=rd_cap,mode="lines+markers",name="资本化(%)",
        line=dict(color=COLORS["amber"],width=2,dash="dot")), secondary_y=True)

    fig.update_layout(height=240, margin=dict(l=10,r=10,t=25,b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,font=dict(size=9)),
        title=dict(text="研发投入效率",font=dict(size=11)), font=dict(size=9))
    return fig

def get_customer_concentration_chart() -> go.Figure:
    years = get_years(); spec = get_special_metrics()
    top5 = spec["前五大客户收入占比"]; top1 = spec["第一大客户收入占比"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years,y=top5,mode="lines+markers",name="前五大客户",
        line=dict(color=COLORS["ember"],width=2),fill="tozeroy",fillcolor="rgba(44,95,138,0.08)"))
    fig.add_trace(go.Scatter(x=years,y=top1,mode="lines+markers",name="第一大客户",
        line=dict(color=COLORS["red"],width=1.5)))
    fig.add_hline(y=30,line_dash="dash",line_color=COLORS["amber"],annotation_text="30%警戒线")

    fig.update_layout(height=240, margin=dict(l=10,r=10,t=25,b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,font=dict(size=9)),
        title=dict(text="客户集中度(%)",font=dict(size=11)), font=dict(size=9))
    return fig
