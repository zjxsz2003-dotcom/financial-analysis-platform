"""战略目标追踪 — Slite"""
import streamlit as st
from modules.data_loader import is_data_loaded, get_company_name, get_strategy_targets
from modules.strategy_tracker import get_strategy_progress_data, get_strategy_progress_chart, get_kpi_tree_figure, what_if_simulation
from utils.ui_helpers import *

if not is_data_loaded(): st.switch_page("pages/0_📥_数据导入.py")

company = get_company_name(); sd = get_strategy_progress_data()
drill = st.session_state.get("drill_context",{}); breadcrumb("战略追踪",drill)
st.markdown(f'<h2>🎯 战略目标追踪 — {company}</h2>', unsafe_allow_html=True)

st.plotly_chart(chart_layout(get_strategy_progress_chart(), 260, "年度战略目标完成进度"), use_container_width=True)

for i, t in enumerate(sd):
    status = t["status"]; bc = { "normal": GREEN, "warning": AMBER, "danger": RED }[status]
    icon = {"normal":"●","warning":"◉","danger":"●"}[status]
    st.markdown(f'<div style="background:{WHITE};border:2px solid {bc};border-radius:16px;padding:20px;margin:12px 0;box-shadow:{SHADOW};"><h4>{icon} {t["name"]}</h4>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns([2,1.5,2])
    with c1: st.progress(min(t["progress"]/100,1.0),text=f"完成率 {t['progress']:.1f}%")
    with c2: st.metric("当前",f"{t['current_value']}{t['unit']}"); st.metric("目标",f"{t['target_value']}{t['unit']}")
    with c3:
        if status=="danger": st.error("严重落后")
        elif status=="warning": st.warning("略落后")
        else: st.success("进度正常")
    kp = t.get("kpi_tree",{})
    if kp:
        with st.expander("📊 KPI分解树"):
            st.plotly_chart(chart_layout(get_kpi_tree_figure(t["name"],kp),250), use_container_width=True)
            for kn, ki in kp.items():
                sr = ki["current"]/ki["target"] if ki["target"] else 0; ss = "danger" if sr<0.7 else ("warning" if sr<0.9 else "normal")
                sc = st.columns([3,1,1,2])
                with sc[0]: st.markdown(f"**{kn}**")
                with sc[1]: st.metric("当前",str(ki["current"]))
                with sc[2]: st.metric("目标",str(ki["target"]))
                with sc[3]: badge(ss);
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()
section("🔮 What-if 情景模拟")
c1,c2,c3 = st.columns([1,1,2])
with c1: m = st.slider("毛利率(%)",12.0,22.0,18.0,0.5,key="wm")
with c2: g = st.slider("收入增速(%)",-10.0,25.0,10.0,1.0,key="wg")
with c3:
    if st.button("运行模拟",use_container_width=True,type="primary"):
        sim = what_if_simulation(adjusted_margin=m, adjusted_rev_growth=g)
        sc = st.columns(len(sim["scenarios"])+1)
        with sc[0]: st.metric("基准ROE",f"{sim['base_roe']}%"); st.metric("基准净利润",f"{sim['base_np']:.0f}亿")
        for j,s in enumerate(sim["scenarios"]):
            with sc[j+1]: st.metric(s["name"],f"{s['new_roe']}%",delta=f"ROE {s['new_roe']-s['base_roe']:+.1f}%")

drill_bar([{"label":"相关预警指标","target":"pages/2_🚨_指标监控预警.py","context":{"from":"战略追踪","focus":"战略预警"}},{"label":"预算执行情况","target":"pages/3_💰_预算偏差分析.py","context":{"from":"战略追踪","focus":"预算关联"}},{"label":"业财分析","target":"pages/1_📊_业财融合看板.py","context":{"from":"战略追踪","focus":"动因分析"}}])
