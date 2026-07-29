"""
战略目标追踪 — BI紧凑风格
"""
import streamlit as st
from config import COLORS, ALERT_COLORS
from modules.data_loader import is_data_loaded, get_company_name, get_strategy_targets
from modules.strategy_tracker import get_strategy_progress_data, get_strategy_progress_chart, get_kpi_tree_figure, what_if_simulation
from utils.ui_helpers import bi_kpi_row, bi_breadcrumb, bi_section, bi_drill_bar, bi_badge, show_watermark
show_watermark()

if not is_data_loaded():
    st.switch_page("pages/0_📥_数据导入.py")

def compact_chart(fig, h=240):
    fig.update_layout(height=h, margin=dict(l=5,r=5,t=25,b=5), font=dict(size=9),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

company = get_company_name()
strategy_data = get_strategy_progress_data()
drill = st.session_state.get("drill_context", {})
bi_breadcrumb("战略追踪", drill)

st.markdown(f"<h3>🎯 战略目标追踪 — {company}</h3>", unsafe_allow_html=True)

# === 进度总览 ===
st.plotly_chart(compact_chart(get_strategy_progress_chart(), 220), use_container_width=True)

# === 战略KPI卡片 ===
s_metrics = []
for s in strategy_data:
    s_metrics.append({
        "label": s["name"][:18],
        "value": f"{s['progress']:.1f}%",
        "delta": f"目标{s['target_value']}{s['unit']}",
        "status": s["status"],
    })
bi_kpi_row(s_metrics, cols_per_row=len(s_metrics))

st.divider()

# === 每个战略目标详情 ===
for i, target in enumerate(strategy_data):
    status = target["status"]
    bc = ALERT_COLORS[status]
    icon = {"normal": "🟢", "warning": "🟡", "danger": "🔴"}[status]

    st.markdown(f"""
    <div style="background:#fff;border:1.5px solid {bc};border-radius:6px;padding:10px 14px;margin:4px 0;">
        <strong>{icon} 目标{i+1}：{target['name']}</strong>
        <span style="float:right;font-size:12px;">当前 {target['current_value']}{target['unit']}
        / 目标 {target['target_value']}{target['unit']}</span>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        st.progress(min(target["progress"] / 100, 1.0), text=f"完成率 {target['progress']:.1f}%")
    with c2:
        if status == "danger":
            st.error("落后时间进度")
        elif status == "warning":
            st.warning("略落后")
        else:
            st.success("进度正常")

    # KPI树
    kpi_tree = target.get("kpi_tree", {})
    if kpi_tree:
        with st.expander("📊 KPI分解", expanded=False):
            tree_cols = st.columns(len(kpi_tree))
            for j, (kpi_name, kpi_info) in enumerate(kpi_tree.items()):
                with tree_cols[j]:
                    sub_ratio = kpi_info["current"] / kpi_info["target"] if kpi_info["target"] else 0
                    sub_status = "danger" if sub_ratio < 0.7 else ("warning" if sub_ratio < 0.9 else "normal")
                    st.metric(kpi_name[:15], str(kpi_info["current"]),
                             delta=f"目标{kpi_info['target']}")
                    bi_badge(sub_status)

st.divider()

# === What-if ===
bi_section("🔮 What-if 情景模拟")
c1, c2, c3 = st.columns([1, 1, 1.5])
with c1:
    adj_margin = st.slider("调整毛利率(%)", 10.0, 25.0, 18.0, 0.5, key="whatif_margin")
with c2:
    adj_growth = st.slider("调整收入增速(%)", -15.0, 30.0, 10.0, 1.0, key="whatif_growth")
with c3:
    if st.button("🔍 运行模拟", use_container_width=True, type="primary"):
        sim = what_if_simulation(adjusted_margin=adj_margin, adjusted_rev_growth=adj_growth)
        st.metric("基准ROE", f"{sim['base_roe']}%")
        for sc in sim["scenarios"]:
            st.metric(sc["name"], f"{sc['new_roe']}%",
                     delta=f"净利润变化{sc['np_change']:+.1f}亿")

bi_drill_bar([
    {"label": "相关预警指标", "target": "pages/2_🚨_指标监控预警.py", "context": {"from": "战略追踪", "focus": "战略KPI预警"}},
    {"label": "预算执行情况", "target": "pages/3_💰_预算偏差分析.py", "context": {"from": "战略追踪", "focus": "战略预算关联"}},
])
