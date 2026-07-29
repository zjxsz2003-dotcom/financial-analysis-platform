"""
业财融合看板 — Slite Design
"""
import streamlit as st; import pandas as pd
from config import COLORS
from modules.data_loader import is_data_loaded, get_company_name, get_income, get_balance, get_years, get_segment_data, get_special_metrics
from modules.business_finance import *
from utils.ui_helpers import show_watermark, kpi_row, four_step, dim_row, settings_panel, drill_bar, alert_strip, badge, spark, section, breadcrumb, chart_layout, WHITE, MOON, SHADOW, INK, SLATE, GREEN
show_watermark()
from modules import business_finance as bf

if not is_data_loaded(): st.switch_page("pages/0_📥_数据导入.py")

company = get_company_name(); inc = get_income(); bs = get_balance(); years = get_years(); latest = years[-1]
drill = st.session_state.get("drill_context", {}); breadcrumb("业财看板", drill)
st.markdown(f'<h2>📊 业财融合深度分析 — {company}</h2>', unsafe_allow_html=True)

# KPI行
total_rev = float(inc[inc["年份"]==latest]["营业收入"].values[0])
np_val = float(inc[inc["年份"]==latest]["净利润"].values[0])
equity = float(bs[bs["年份"]==latest]["股东权益合计"].values[0])
ta = float(bs[bs["年份"]==latest]["资产总计"].values[0])
gross = round((total_rev-float(inc[inc["年份"]==latest]["营业成本"].values[0]))/total_rev*100, 1)
roe = round(np_val/equity*100, 1); top5 = get_special_metrics()["前五大客户收入占比"][-1]

kpi_row([
    {"label":"营业收入","value":f"{total_rev:.0f}亿","delta":f"{round((total_rev-float(inc[inc['年份']==years[-2]]['营业收入'].values[0]))/float(inc[inc['年份']==years[-2]]['营业收入'].values[0])*100,1):+.1f}%","status":"normal"},
    {"label":"净利润","value":f"{np_val:.1f}亿","status":"normal" if np_val>0 else "danger"},
    {"label":"ROE","value":f"{roe:.1f}%","status":"normal" if roe>10 else "warning"},
    {"label":"毛利率","value":f"{gross:.1f}%","status":"normal" if gross>15 else "warning"},
    {"label":"总资产","value":f"{ta:.0f}亿","status":"normal"},
    {"label":"研发费用率","value":f"{round(float(inc[inc['年份']==latest]['研发费用'].values[0])/total_rev*100,1):.1f}%","status":"normal"},
    {"label":"前5大客户","value":f"{top5:.1f}%","status":"warning" if top5>70 else "normal"},
])

st.divider()

# 杜邦分析
with st.expander("📐 杜邦分析 — 五年趋势拆解", expanded=True):
    dp_data = []
    for yr in years:
        ri = inc[inc["年份"]==yr].iloc[0]; rb = bs[bs["年份"]==yr].iloc[0]
        rv = float(ri["营业收入"]); np = float(ri["净利润"])
        ta_y = float(rb["资产总计"]); eq = float(rb["股东权益合计"])
        npm = round(np/rv*100,2); ato = round(rv/ta_y,3); em = round(ta_y/eq,2); roe_y = round(npm*ato*em/100,1)
        dp_data.append({"年份":int(yr),"ROE(%)":roe_y,"净利率(%)":npm,"总资产周转率":ato,"权益乘数":em,"净利润(亿)":round(np,1),"收入(亿)":round(rv,1)})
    dp_df = pd.DataFrame(dp_data)
    st.markdown("**ROE = 净利率 × 总资产周转率 × 权益乘数**")
    st.dataframe(dp_df, use_container_width=True, hide_index=True, height=200)

    if len(dp_data) >= 3:
        f = dp_data[0]; l = dp_data[-1]; rc = l["ROE(%)"]-f["ROE(%)"]; nc = l["净利率(%)"]-f["净利率(%)"]; ac = l["总资产周转率"]-f["总资产周转率"]; ec = l["权益乘数"]-f["权益乘数"]
        npm_c = nc*f["总资产周转率"]*f["权益乘数"]/100
        ato_c = l["净利率(%)"]*ac*f["权益乘数"]/100
        em_c = l["净利率(%)"]*l["总资产周转率"]*ec/100
        st.markdown(f'<div style="font-size:13px;line-height:1.8;background:{WHITE};border:1px solid {MOON};border-radius:16px;padding:16px;margin:8px 0;box-shadow:{SHADOW};"><b>📌 ROE从{f["年份"]}年 {f["ROE(%)"]}% → {l["年份"]}年 {l["ROE(%)"]}%（{rc:+.1f}%）</b><br>'
            f'<b>🔍 因素分解：</b>①净利率贡献≈{npm_c:+.2f}pp ②周转率贡献≈{ato_c:+.2f}pp ③杠杆贡献≈{em_c:+.2f}pp<br>'
            f'<b>💡 核心驱动：</b>{"净利率" if abs(npm_c)>=abs(ato_c) and abs(npm_c)>=abs(em_c) else ("周转率" if abs(ato_c)>=abs(em_c) else "杠杆")}</div>', unsafe_allow_html=True)

st.divider()

# 板块概览
c1, c2 = st.columns(2)
with c1: st.plotly_chart(chart_layout(get_segment_revenue_chart(), 260), use_container_width=True)
with c2: st.plotly_chart(chart_layout(get_segment_margin_chart(), 260), use_container_width=True)
w, wh, sw, nw = bf.segment_fourstep(); four_step("业务板块收入与毛利", w, wh, sw, nw)
st.divider()

# 收入+成本
c3, c4 = st.columns(2)
with c3:
    st.plotly_chart(chart_layout(bf.revenue_attribution_chart(), 250), use_container_width=True)
    w, wh, sw, nw = bf.revenue_attribution_fourstep(); four_step("收入驱动归因", w, wh, sw, nw)
with c4:
    st.plotly_chart(chart_layout(bf.cost_structure_chart(), 250), use_container_width=True)
    w, wh, sw, nw = bf.cost_analysis_fourstep(); four_step("成本差异分析", w, wh, sw, nw)
st.divider()

# 应收+存货
c5, c6 = st.columns(2)
with c5:
    st.plotly_chart(chart_layout(bf.ar_quality_chart(), 250), use_container_width=True)
    w, wh, sw, nw = bf.ar_quality_fourstep(); four_step("应收账款质量", w, wh, sw, nw)
with c6:
    st.plotly_chart(chart_layout(bf.inventory_structure_chart(), 250), use_container_width=True)
    w, wh, sw, nw = bf.inventory_fourstep(); four_step("存货与跌价风险", w, wh, sw, nw)
st.divider()

# 费用+研发
c7, c8 = st.columns(2)
with c7:
    st.plotly_chart(chart_layout(bf.fee_roi_chart(), 250), use_container_width=True)
    w, wh, sw, nw = bf.fee_roi_fourstep(); four_step("费用效能ROI", w, wh, sw, nw)
with c8:
    st.plotly_chart(chart_layout(get_rd_efficiency_chart(), 250), use_container_width=True)
    st.plotly_chart(chart_layout(get_customer_concentration_chart(), 250), use_container_width=True)

drill_bar([{"label":"查看预警指标","target":"pages/2_🚨_指标监控预警.py","context":{"from":"业财看板","focus":"异常指标"}},{"label":"查看预算偏差","target":"pages/3_💰_预算偏差分析.py","context":{"from":"业财看板","focus":"预算根因"}},{"label":"行业对比分析","target":"pages/6_🏭_行业对比分析.py","context":{"from":"业财看板","focus":"行业对标"}}])
