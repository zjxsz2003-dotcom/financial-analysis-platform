"""分析报告生成 — Slite"""
import streamlit as st; import pandas as pd
from modules.data_loader import is_data_loaded, get_company_name, get_income, get_balance, get_years
from modules.kpi_engine import calc_all_kpis, get_alert_summary
from modules.report_generator import build_report_data
from utils.download import generate_pdf_report
from utils.ui_helpers import *

if not is_data_loaded(): st.switch_page("pages/0_📥_数据导入.py")

company=get_company_name(); years=get_years(); latest=years[-1]; inc=get_income(); bs=get_balance()
drill=st.session_state.get("drill_context",{}); breadcrumb("报告生成",drill)
st.markdown(f'<h2>📄 分析报告生成 — {company}</h2>', unsafe_allow_html=True)

c1,c2,c3=st.columns(3)
with c1: mth=st.button("📋 月度经营快报",key="m",use_container_width=True)
with c2: qtr=st.button("📊 季度分析报告 ⭐",key="q",use_container_width=True,type="primary")
with c3: ann=st.button("📖 年度综合报告",key="a",use_container_width=True)

rt=None;period=""
if mth: rt,period="monthly",f"{latest}年12月"
elif qtr: rt,period="quarterly",f"{latest}年Q4"
elif ann: rt,period="annual",f"{latest}年度"

if rt:
    with st.spinner("生成中..."): rd=build_report_data(rt,period)
    st.success(f"✅ {period}报告已生成")
    st.markdown(f"### {rd['title']}")
    st.caption(f"{rd['company']} | {rd['period']}")

    hl=rd.get("highlights",{}); hcs=st.columns(min(len(hl),5))
    for i,(k,v) in enumerate(hl.items()):
        with hcs[i%5]: st.metric(label=k,value=v)

    st.divider()
    for sec in rd.get("sections",[]):
        st.markdown(f"**{sec.get('heading','')}**")
        st.markdown(sec.get("body",""))
        t=sec.get("table")
        if t is not None and isinstance(t,pd.DataFrame) and not t.empty:
            st.dataframe(t,use_container_width=True,hide_index=True,height=140)
        st.caption("")

    st.divider()
    st.markdown("### 📋 管理层行动清单")
    actions = [
        {"优先级":"🔴 高","行动":"优化存货管理","说明":"建立库龄看板+安全库存线+推动VMI","负责人":"供应链+财务","期限":"1个月"},
        {"优先级":"🔴 高","行动":"应收账款催收","说明":"大客户账龄预警+超90天催收+保理/贴现","负责人":"销售+财务","期限":"2周"},
        {"优先级":"🟡 中","行动":"成本费用优化","说明":"增幅>15%科目专项审计+预算红线","负责人":"财务BP","期限":"季度内"},
        {"优先级":"🟡 中","行动":"高毛利业务倾斜","说明":"汽车+通信收入占比从17%→25%","负责人":"战略+业务","期限":"年度"},
        {"优先级":"🟡 中","行动":"客户集中度改善","说明":"前5大占比从74%降至65%以下","负责人":"销售","期限":"6个月"},
        {"优先级":"🟢 低","行动":"研发ROI核算","说明":"按项目归集费用+投入产出评估","负责人":"研发+财务","期限":"下季度"},
    ]
    st.dataframe(pd.DataFrame(actions),use_container_width=True,hide_index=True,height=200)

    st.divider(); dl1,dl2=st.columns(2)
    with dl1:
        try:
            pdf=generate_pdf_report(rd)
            st.download_button("📄 下载PDF报告",data=pdf,file_name=f"{company}_{period}_报告.pdf",mime="application/pdf",use_container_width=True,type="primary")
        except Exception as e: st.warning(f"PDF待中文字体: {str(e)[:50]}")
    with dl2:
        kpis=calc_all_kpis()
        er=[{"维度":dim,"指标":KPI_NAMES_CN.get(n,n),"当前值":f"{kpis[dim][n]['current']}{kpis[dim][n]['unit']}","状态":{"normal":"正常","warning":"关注","danger":"预警"}.get(kpis[dim][n]["status"])} for dim,inds in kpis.items() for n in inds]
        st.download_button("📊 下载指标CSV",data=pd.DataFrame(er).to_csv(index=False).encode("utf-8-sig"),file_name=f"{company}_指标.csv",mime="text/csv",use_container_width=True)

drill_bar([{"label":"业财看板","target":"pages/1_📊_业财融合看板.py","context":{"from":"报告","focus":""}},{"label":"指标预警","target":"pages/2_🚨_指标监控预警.py","context":{"from":"报告","focus":""}},{"label":"行业对比","target":"pages/6_🏭_行业对比分析.py","context":{"from":"报告","focus":""}}])
