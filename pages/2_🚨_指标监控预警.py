"""
指标监控预警 — Slite
"""
import streamlit as st; import pandas as pd; import plotly.graph_objects as go
from config import KPI_DIMENSIONS, KPI_NAMES_CN, DEFAULT_THRESHOLDS
from modules.data_loader import is_data_loaded, get_company_name, get_years
from modules.kpi_engine import calc_all_kpis, get_alert_summary
from modules.alert_engine import get_status_description, generate_drill_suggestions
from utils.ui_helpers import show_watermark, kpi_row, dim_row, settings_panel, drill_bar, alert_strip, badge, spark, section, breadcrumb
show_watermark()

if not is_data_loaded(): st.switch_page("pages/0_📥_数据导入.py")

company = get_company_name(); years = get_years()
drill = st.session_state.get("drill_context", {}); breadcrumb("指标预警", drill)
st.markdown(f'<h2>🚨 指标监控预警 — {company}</h2>', unsafe_allow_html=True)

def _settings_ui():
    mode = st.selectbox("预警模式",["标准","严格","宽松"],index=0,key="am")
    factor = {"严格":0.7,"标准":1.0,"宽松":1.5}.get(mode,1.0)
    cols = st.columns(3); idx = 0
    for dim, inds in KPI_DIMENSIONS.items():
        for ind in inds:
            with cols[idx%3]:
                d = DEFAULT_THRESHOLDS.get(ind,{})
                DEFAULT_THRESHOLDS[ind] = {"yellow_low":st.number_input(f"{ind}🟡",value=float(d.get("yellow_low",10))*factor,step=0.5,key=f"ty_{ind}"),
                    "red_low":st.number_input(f"{ind}🔴",value=float(d.get("red_low",5))*factor,step=0.5,key=f"tr_{ind}"),"unit":d.get("unit","")}
            idx += 1

settings_panel("预警阈值设置", _settings_ui, "alert")

kpis = calc_all_kpis(); alerts = get_alert_summary(kpis)
alert_strip(alerts)

dim_stats = [{"name":dim,"normal":sum(1 for i in inds if kpis[dim][i]["status"]=="normal"),
    "warning":sum(1 for i in inds if kpis[dim][i]["status"]=="warning"),
    "danger":sum(1 for i in inds if kpis[dim][i]["status"]=="danger")} for dim, inds in KPI_DIMENSIONS.items()]
dim_row(dim_stats)
st.divider()

for dim, indicators in KPI_DIMENSIONS.items():
    dc = sum(1 for i in indicators if kpis[dim][i]["status"]=="danger")
    wc = sum(1 for i in indicators if kpis[dim][i]["status"]=="warning")
    icon = "●" if dc>0 else ("◉" if wc>0 else "●")
    with st.expander(f"{icon} {dim} ({len(indicators)}项)", expanded=(dc>0)):
        for ind in indicators:
            d = kpis[dim][ind]; name = KPI_NAMES_CN.get(ind,ind); status = d["status"]
            c1,c2,c3,c4,c5 = st.columns([1.5,1,1,2.5,2])
            with c1: badge(status); st.markdown(f"**{name}**")
            with c2: st.metric("当前",f"{d['current']}{d['unit']}",delta=f"{d['yoy']:+.2f}{d['unit']}" if d['yoy']!=0 else None)
            with c3: st.plotly_chart(spark(d["values"],50,{ "normal": GREEN, "warning": AMBER, "danger": RED }.get(status,INK)),use_container_width=True)
            with c4:
                st.caption(get_status_description(ind,status,d["current"]))
                if status=="danger": st.caption(f"⚠️ 风险传导：{'盈利能力下降→融资成本上升' if ind=='ROE' else ('流动性不足→短期偿债压力' if ind=='流动比率' else ('存货积压→跌价损失+资金占用' if ind=='存货周转率' else '需重点关注'))}")
            with c5:
                for s in generate_drill_suggestions(ind,status)[:2]:
                    if st.button(f"→ {s['label']}",key=f"d_{dim}_{ind}_{s['label'][:8]}",use_container_width=True):
                        st.session_state.drill_context=s["context"]; st.switch_page(s["target"])
            st.divider()

all_rows = [{"维度":dim,"指标":KPI_NAMES_CN.get(i,i),"当前值":f"{kpis[dim][i]['current']}{kpis[dim][i]['unit']}","同比":f"{kpis[dim][i]['yoy']:+.2f}{kpis[dim][i]['unit']}","状态":{"normal":"正常","warning":"关注","danger":"预警"}.get(kpis[dim][i]["status"])} for dim,inds in KPI_DIMENSIONS.items() for i in inds]
st.download_button("📥 下载指标CSV",data=pd.DataFrame(all_rows).to_csv(index=False).encode("utf-8-sig"),file_name="指标数据.csv",mime="text/csv",key="dl_kpi")

drill_bar([{"label":"追溯业务根因","target":"pages/1_📊_业财融合看板.py","context":{"from":"指标预警","focus":"异常根因"}},{"label":"查看预算偏差","target":"pages/3_💰_预算偏差分析.py","context":{"from":"指标预警","focus":"预算关联"}},{"label":"行业对比定位","target":"pages/6_🏭_行业对比分析.py","context":{"from":"指标预警","focus":"行业对标"}}])
