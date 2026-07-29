"""预算偏差分析 — Slite"""
import streamlit as st; import pandas as pd
from modules.data_loader import is_data_loaded, get_company_name, get_budget, get_income, get_segment_data, get_years
from modules.budget_analysis import get_budget_vs_actual, get_budget_waterfall_chart, get_revenue_deviation_df, get_cost_deviation_df
from utils.ui_helpers import *

if not is_data_loaded(): st.switch_page("pages/0_📥_数据导入.py")

def _budget_settings():
    tol = st.slider("偏差容忍度(%)",5,20,10,5,key="bt")
    st.session_state["budget_tolerance"] = tol
    budget = get_budget()
    c1,c2,c3 = st.columns(3)
    for biz,col in [("业务一：智能消费电子",c1),("业务二：汽车电子",c2),("业务三：通信互联",c3)]:
        with col:
            d = budget["收入预算"].get(biz,100)
            new = st.number_input(f"{biz}",value=float(d),step=1.0,key=f"bgt_{biz[:12]}")
            budget["收入预算"][biz] = new
    budget["收入预算"]["合计"] = sum(v for k,v in budget["收入预算"].items() if k!="合计")

company = get_company_name(); years = get_years(); latest = years[-1]; inc = get_income(); seg = get_segment_data()
drill = st.session_state.get("drill_context",{}); breadcrumb("预算分析",drill)
st.markdown(f'<h2>💰 预算偏差分析 — {company}</h2>', unsafe_allow_html=True)

settings_panel("预算目标设置", _budget_settings, "budget")

bv = get_budget_vs_actual()
profit = bv.get("利润",{}); np_info = profit.get("净利润",{})
rb = get_budget()["收入预算"].get("合计", sum(v for k,v in get_budget()["收入预算"].items() if k!="合计"))
ra = sum(d["收入"][-1] for d in seg.values()); rp = round(ra/rb*100,1) if rb else 0

kpi_row([
    {"label":"收入预算完成率","value":f"{rp:.1f}%","delta":f"偏差{rp-100:+.1f}%","status":"danger" if rp<95 else "normal"},
    {"label":"净利润","value":f"{np_info.get('实际',0):.0f}亿","delta":f"偏差{np_info.get('偏差率',0):+.1f}%","status":"warning" if np_info.get('偏差率',0)<0 else "normal"},
    {"label":"营业利润","value":f"{profit.get('营业利润',{}).get('实际',0):.0f}亿","status":"normal"},
    {"label":"容忍度","value":f"±{st.session_state.get('budget_tolerance',10)}%","status":"normal"},
])

st.divider()
st.plotly_chart(chart_layout(get_budget_waterfall_chart(), 280, "收入预算偏差瀑布图"), use_container_width=True)

section("各业务板块收入预算偏差")
df = get_revenue_deviation_df()
if not df.empty:
    for _, row in df.iterrows():
        c1,c2,c3,c4,c5,c6 = st.columns([1.8,1.2,1.2,1,1,1.8])
        with c1: badge(row["状态"],row["业务板块"])
        with c2: st.metric("预算",f"{row['预算收入(亿元)']:.0f}亿")
        with c3: st.metric("实际",f"{row['实际收入(亿元)']:.0f}亿")
        with c4: st.metric("偏差",f"{row['偏差(亿元)']:+.0f}亿")
        with c5: st.metric("偏差率",f"{row['偏差率(%)']:+.1f}%")
        with c6:
            if row['偏差率(%)'] < -5: st.caption("🔍 可能：销量不及预期/ASP下滑/客户订单延迟")
            elif row['偏差率(%)'] < 0: st.caption("🟡 轻微偏差")
            else: st.caption("🟢 超预算完成")
st.download_button("📥 下载预算CSV",data=df.to_csv(index=False).encode("utf-8-sig"),file_name="预算偏差.csv",mime="text/csv",key="dl_bgt")

st.divider(); section("费用预算执行")
fee_data = bv.get("费用",{})
fc = st.columns(len(fee_data))
for i,(name,info) in enumerate(fee_data.items()):
    with fc[i]: st.metric(name,f"{info['实际']:.1f}亿",delta=f"预算{info['预算']:.0f}亿·偏差{info['偏差率']:+.1f}%")

drill_bar([{"label":"追溯业务动因","target":"pages/1_📊_业财融合看板.py","context":{"from":"预算分析","focus":"预算业务根因"}},{"label":"战略目标影响","target":"pages/4_🎯_战略目标追踪.py","context":{"from":"预算分析","focus":"战略影响"}},{"label":"行业对标","target":"pages/6_🏭_行业对比分析.py","context":{"from":"预算分析","focus":"行业参照"}}])
