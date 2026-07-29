"""
预算偏差分析 v3
"""
import streamlit as st
import pandas as pd
from config import COLORS
from modules.data_loader import is_data_loaded, get_company_name, get_budget, get_income, get_segment_data, get_years
from modules.budget_analysis import get_budget_vs_actual, get_budget_waterfall_chart, get_revenue_deviation_df, get_cost_deviation_df
from utils.ui_helpers import bi_kpi_row, bi_breadcrumb, bi_drill_bar, bi_badge, bi_settings_panel, bi_section

if not is_data_loaded():
    st.switch_page("pages/0_📥_数据导入.py")

def _budget_settings():
    """预算设置UI - 必须在调用前定义"""
    tol = st.slider("偏差容忍度(%)",5,20,10,5,key="budget_tol")
    st.session_state["budget_tolerance"] = tol
    st.caption("录入各业务板块预算目标（亿元）")
    c1,c2,c3 = st.columns(3)
    budget = get_budget()
    for biz in ["业务一：智能消费电子","业务二：汽车电子","业务三：通信互联"]:
        col = [c1,c2,c3][0] if biz == "业务一：智能消费电子" else ([c1,c2,c3][1] if biz == "业务二：汽车电子" else [c1,c2,c3][2])
        with col:
            default_val = budget["收入预算"].get(biz, 100)
            new_val = st.number_input(f"{biz}", value=float(default_val), step=1.0, key=f"bgt_{biz[:12]}")
            budget["收入预算"][biz] = new_val
    budget["收入预算"]["合计"] = sum(v for k,v in budget["收入预算"].items() if k!="合计")

company = get_company_name(); years = get_years(); latest = years[-1]
inc = get_income(); seg = get_segment_data()
drill = st.session_state.get("drill_context", {})
bi_breadcrumb("预算分析", drill)
st.markdown(f"<h3>💰 预算偏差分析 — {company}</h3>", unsafe_allow_html=True)

# === 用户设置面板 ===
bi_settings_panel("预算目标设置", lambda: _budget_settings(), "budget")

# === KPI ===
bv = get_budget_vs_actual()
profit = bv.get("利润",{})
np_info = profit.get("净利润",{})
op_info = profit.get("营业利润",{})

rev_budget_total = sum(v for k,v in get_budget()["收入预算"].items() if k!="合计")
rev_actual_total = sum(d["收入"][-1] for d in seg.values())
rev_pct = round(rev_actual_total/rev_budget_total*100,1) if rev_budget_total else 0

bi_kpi_row([
    {"label":"收入预算完成率","value":f"{rev_pct:.1f}%","delta":f"偏差{rev_pct-100:+.1f}%","status":"danger" if rev_pct<95 else "normal"},
    {"label":"净利润","value":f"{np_info.get('实际',0):.0f}亿","delta":f"偏差{np_info.get('偏差率',0):+.1f}%","status":"warning" if np_info.get('偏差率',0)<0 else "normal"},
    {"label":"营业利润","value":f"{op_info.get('实际',0):.0f}亿","delta":f"偏差{op_info.get('偏差率',0):+.1f}%","status":"normal"},
    {"label":"偏差容忍度","value":f"±{st.session_state.get('budget_tolerance',10)}%","delta":"","status":"normal"},
], cols_per_row=4)

st.divider()

# === 瀑布图 ===
st.plotly_chart(get_budget_waterfall_chart(), use_container_width=True)

# === 业务板块预算对比（含归因） ===
bi_section("▎各业务板块收入预算偏差（含部门归因）")
df = get_revenue_deviation_df()
if not df.empty:
    for _, row in df.iterrows():
        c1,c2,c3,c4,c5,c6 = st.columns([1.8,1.2,1.2,1,1,1.8])
        with c1: bi_badge(row["状态"],row["业务板块"])
        with c2: st.metric("预算",f"{row['预算收入(亿元)']:.0f}亿")
        with c3: st.metric("实际",f"{row['实际收入(亿元)']:.0f}亿")
        with c4: st.metric("偏差",f"{row['偏差(亿元)']:+.0f}亿")
        with c5: st.metric("偏差率",f"{row['偏差率(%)']:+.1f}%")
        with c6:
            # 偏差归因建议
            if row['偏差率(%)'] < -5:
                st.caption(f"🔍 可能原因：销量不及预期/ASP下滑/客户订单延迟")
                if st.button("→ 业务详情",key=f"bd_{row['业务板块'][:8]}",use_container_width=True):
                    st.session_state.drill_context={"from":"预算分析","focus":row['业务板块']}
                    st.switch_page("pages/1_📊_业财融合看板.py")
            elif row['偏差率(%)'] < 0:
                st.caption("🟡 轻微偏差，关注后续趋势")
            else:
                st.caption("🟢 超预算完成")

st.download_button("📥 下载预算对比CSV",data=df.to_csv(index=False).encode("utf-8-sig"),
    file_name="预算偏差.csv",mime="text/csv",key="dl_budget")

st.divider()

# === 费用预算 ===
bi_section("▎费用预算执行明细")
fee_data = bv.get("费用",{})
fee_cols = st.columns(len(fee_data))
for i,(name,info) in enumerate(fee_data.items()):
    with fee_cols[i]:
        status = info["status"]
        st.metric(name,f"{info['实际']:.1f}亿",delta=f"预算{info['预算']:.0f}亿 · 偏差{info['偏差率']:+.1f}%")

# === 成本偏差归因 ===
st.divider()
bi_section("▎成本偏差归因分析")
cost_df = get_cost_deviation_df()
if not cost_df.empty:
    st.dataframe(cost_df, use_container_width=True, hide_index=True, height=140)

bi_drill_bar([
    {"label":"追溯业务动因","target":"pages/1_📊_业财融合看板.py","context":{"from":"预算分析","focus":"预算业务根因"}},
    {"label":"战略目标影响评估","target":"pages/4_🎯_战略目标追踪.py","context":{"from":"预算分析","focus":"战略影响"}},
    {"label":"查看行业对标","target":"pages/6_🏭_行业对比分析.py","context":{"from":"预算分析","focus":"行业预算参照"}},
])
