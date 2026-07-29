"""
指标监控预警 v3 — 用户自定义阈值 + 深度分析
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config import COLORS, KPI_DIMENSIONS, KPI_NAMES_CN, ALERT_COLORS, DEFAULT_THRESHOLDS
from modules.data_loader import is_data_loaded, get_company_name, get_years
from modules.kpi_engine import calc_all_kpis, get_alert_summary
from modules.alert_engine import get_status_description, generate_drill_suggestions
from utils.ui_helpers import bi_kpi_row, bi_dimension_row, bi_breadcrumb, bi_drill_bar, bi_alert_strip, bi_badge, bi_sparkline, bi_settings_panel

if not is_data_loaded():
    st.switch_page("pages/0_📥_数据导入.py")

def _settings_ui():
    """预警设置UI"""
    mode = st.selectbox("预警模式",["标准","严格","宽松"],index=0,key="alert_mode")
    industry = st.selectbox("对标行业",["消费电子","汽车零部件","通信设备","通用"],key="alert_industry")
    st.caption("自定义各指标阈值")
    factor = {"严格":0.7,"标准":1.0,"宽松":1.5}.get(mode,1.0)
    cols = st.columns(3); idx = 0
    for dim, inds in KPI_DIMENSIONS.items():
        for ind in inds:
            with cols[idx % 3]:
                default = DEFAULT_THRESHOLDS.get(ind,{})
                yd = default.get("yellow_low",10); rd = default.get("red_low",5)
                DEFAULT_THRESHOLDS[ind] = {
                    "yellow_low": st.number_input(f"{ind}🟡",value=float(yd)*factor,step=0.5,key=f"th_y_{ind}"),
                    "red_low": st.number_input(f"{ind}🔴",value=float(rd)*factor,step=0.5,key=f"th_r_{ind}"),
                    "unit": default.get("unit","")}
            idx += 1

company = get_company_name(); years = get_years()
drill = st.session_state.get("drill_context", {})
bi_breadcrumb("指标预警", drill)
st.markdown(f"<h3>🚨 指标监控预警 — {company}</h3>", unsafe_allow_html=True)

# === 用户设置面板 ===
bi_settings_panel("预警阈值设置", lambda: _settings_ui(), "alert")

# === 计算KPI ===
kpis = calc_all_kpis()
alerts = get_alert_summary(kpis)

# === 预警摘要 ===
bi_alert_strip(alerts)

# === 五大维度 ===
dim_stats = [{ "name":dim, "normal":sum(1 for i in inds if kpis[dim][i]["status"]=="normal"),
    "warning":sum(1 for i in inds if kpis[dim][i]["status"]=="warning"),
    "danger":sum(1 for i in inds if kpis[dim][i]["status"]=="danger") }
    for dim, inds in KPI_DIMENSIONS.items()]
bi_dimension_row(dim_stats)

st.divider()

for dim, indicators in KPI_DIMENSIONS.items():
    d_count = sum(1 for i in indicators if kpis[dim][i]["status"]=="danger")
    w_count = sum(1 for i in indicators if kpis[dim][i]["status"]=="warning")
    icon = "🔴" if d_count>0 else ("🟡" if w_count>0 else "🟢")

    with st.expander(f"{icon} {dim} ({len(indicators)}项)", expanded=(d_count>0)):
        for ind in indicators:
            d = kpis[dim][ind]; name = KPI_NAMES_CN.get(ind,ind); status = d["status"]
            c1,c2,c3,c4,c5 = st.columns([1.5,1,1,2.5,2])
            with c1: bi_badge(status); st.markdown(f"**{name}**")
            with c2: st.metric("当前",f"{d['current']}{d['unit']}",delta=f"{d['yoy']:+.2f}{d['unit']}" if d['yoy']!=0 else None)
            with c3: st.plotly_chart(bi_sparkline(d["values"],50,ALERT_COLORS.get(status)),use_container_width=True)
            with c4:
                st.caption(get_status_description(ind,status,d["current"]))
                # 风险提示
                if status=="danger":
                    risks = {"ROE":"盈利能力不足→融资成本上升、股价承压","毛利率":"毛利下滑→压缩利润空间→可能需要削减费用或提价",
                        "流动比率":"流动性不足→短期偿债压力→可能需要紧急融资","存货周转率":"存货积压→跌价损失+资金占用→影响现金流",
                        "应收周转率":"回款恶化→坏账风险+现金流紧张→可能需要保理融资",
                        "收入增长率":"收入下滑→市场份额丢失→需要调整产品/渠道策略","净利增长率":"利润下滑→经营效率恶化→需要成本优化专项"}
                    st.caption(f"⚠️ 风险传导：{risks.get(ind,'需关注')}")
            with c5:
                for s in generate_drill_suggestions(ind,status)[:2]:
                    if st.button(f"→ {s['label']}",key=f"d_{dim}_{ind}_{s['label'][:8]}",use_container_width=True):
                        st.session_state.drill_context=s["context"]; st.switch_page(s["target"])
            st.markdown("<hr style='margin:3px 0;'>",unsafe_allow_html=True)

st.divider()
all_rows=[{"维度":dim,"指标":KPI_NAMES_CN.get(i,i),"当前值":f"{kpis[dim][i]['current']}{kpis[dim][i]['unit']}",
    "同比":f"{kpis[dim][i]['yoy']:+.2f}{kpis[dim][i]['unit']}",
    "状态":{"normal":"正常","warning":"关注","danger":"预警"}.get(kpis[dim][i]["status"])}
    for dim,inds in KPI_DIMENSIONS.items() for i in inds]
st.download_button("📥 下载指标CSV",data=pd.DataFrame(all_rows).to_csv(index=False).encode("utf-8-sig"),
    file_name="指标数据.csv",mime="text/csv",key="dl_kpi")

bi_drill_bar([{"label":"追溯业务根因","target":"pages/1_📊_业财融合看板.py","context":{"from":"指标预警","focus":"异常根因"}},
    {"label":"查看预算偏差","target":"pages/3_💰_预算偏差分析.py","context":{"from":"指标预警","focus":"预算关联"}},
    {"label":"行业对比定位","target":"pages/6_🏭_行业对比分析.py","context":{"from":"指标预警","focus":"行业对标"}}])
