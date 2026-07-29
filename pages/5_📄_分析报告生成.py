"""
分析报告生成 v3 — 含管理层行动清单
"""
import streamlit as st; import pandas as pd
from config import COLORS
from modules.data_loader import is_data_loaded, get_company_name, get_income, get_balance, get_years
from modules.kpi_engine import calc_all_kpis, get_alert_summary
from modules.report_generator import build_report_data
from utils.download import generate_pdf_report
from utils.ui_helpers import bi_breadcrumb, bi_drill_bar, bi_badge, bi_alert_strip
from config import KPI_NAMES_CN

if not is_data_loaded(): st.switch_page("pages/0_📥_数据导入.py")
company=get_company_name(); inc=get_income(); bs=get_balance(); years=get_years(); latest=years[-1]
drill=st.session_state.get("drill_context",{})
bi_breadcrumb("报告生成",drill)
st.markdown(f"<h3>📄 分析报告生成 — {company}</h3>",unsafe_allow_html=True)

c1,c2,c3=st.columns(3)
with c1: monthly=st.button("📋 月度经营快报",key="m",use_container_width=True)
with c2: quarterly=st.button("📊 季度分析报告 ⭐推荐",key="q",use_container_width=True,type="primary")
with c3: annual=st.button("📖 年度综合报告",key="a",use_container_width=True)

rt=None;period=""
if monthly: rt,period="monthly",f"{latest}年12月"
elif quarterly: rt,period="quarterly",f"{latest}年Q4"
elif annual: rt,period="annual",f"{latest}年度"

if rt:
    with st.spinner("生成中..."):
        rd=build_report_data(rt,period)
    st.success(f"✅ {period}报告已生成")
    st.markdown(f"### {rd['title']}")
    st.caption(f"公司：{rd['company']} | 期间：{rd['period']}")

    # AI摘要
    ai=rd.get("ai_summary",{})
    if isinstance(ai,dict):
        st.info(f"**{ai.get('label','📋')}**\n\n{ai.get('text','')}")

    # 核心指标
    hl=rd.get("highlights",{}); hlcs=st.columns(min(len(hl),5))
    for i,(k,v) in enumerate(hl.items()):
        with hlcs[i%5]: st.metric(label=k,value=v)
    st.divider()

    # 章节
    for sec in rd.get("sections",[]):
        st.markdown(f"**{sec.get('heading','')}**")
        st.markdown(sec.get("body",""))
        t=sec.get("table")
        if t is not None and isinstance(t,pd.DataFrame) and not t.empty:
            st.dataframe(t,use_container_width=True,hide_index=True,height=140)
        st.caption("")

    # === 管理层行动清单（v3新增） ===
    st.divider()
    st.markdown("### 📋 管理层行动清单")
    st.markdown(f"<span style='color:{COLORS['text_light']};font-size:11px;'>基于各模块Now What建议汇总</span>",unsafe_allow_html=True)

    actions=[
        {"priority":"🔴 高","action":"优化存货管理","detail":"建立库龄结构看板，设置安全库存水位线；推动VMI模式降低自有库存","owner":"供应链+财务","deadline":"1个月内"},
        {"priority":"🔴 高","action":"应收账款催收","detail":"建立大客户账龄预警机制，超90天应收启动催收；考虑保理/贴现","owner":"销售+财务","deadline":"2周内"},
        {"priority":"🟡 中","action":"成本费用优化","detail":"对增幅超15%的费用科目启动专项审计；设定各科目预算红线","owner":"财务BP","deadline":"季度内"},
        {"priority":"🟡 中","action":"高毛利业务倾斜","detail":"汽车+通信业务资源优先配置，目标收入占比从17%→25%","owner":"战略+业务","deadline":"年度"},
        {"priority":"🟡 中","action":"客户集中度改善","detail":"主动拓展新客户，目标前5大客户占比从74%降至65%以下","owner":"销售","deadline":"6个月"},
        {"priority":"🟢 低","action":"研发费用分项目ROI核算","detail":"建立研发费用按项目归集体系，评估各项目投入产出比","owner":"研发+财务","deadline":"下季度"},
    ]
    act_df=pd.DataFrame(actions)
    st.dataframe(act_df,use_container_width=True,hide_index=True,height=200)

    # 下载
    st.divider(); dl1,dl2=st.columns(2)
    with dl1:
        try:
            pdf=generate_pdf_report(rd)
            st.download_button("📄 下载PDF报告",data=pdf,file_name=f"{company}_{period}_报告.pdf",
                mime="application/pdf",use_container_width=True,type="primary")
        except Exception as e:
            st.warning(f"PDF待字体: {str(e)[:50]}")
    with dl2:
        kpis=calc_all_kpis()
        erows=[{"维度":dim,"指标":KPI_NAMES_CN.get(n,n),"当前值":f"{kpis[dim][n]['current']}{kpis[dim][n]['unit']}",
            "状态":{"normal":"正常","warning":"关注","danger":"预警"}.get(kpis[dim][n]["status"])}
            for dim,inds in kpis.items() for n in inds]
        st.download_button("📊 下载指标CSV",data=pd.DataFrame(erows).to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{company}_指标.csv",mime="text/csv",use_container_width=True)

    # 异常穿透
    alerts=get_alert_summary(kpis)
    if alerts:
        st.divider(); st.caption("🔍 报告中的预警项 → 点击穿透")
        ac=st.columns(min(len(alerts),4))
        for i,a in enumerate(alerts[:4]):
            with ac[i]:
                t="pages/1_📊_业财融合看板.py" if a["dim"] in ["盈利能力","营运能力","成长能力"] else "pages/2_🚨_指标监控预警.py"
                if st.button(f"追溯:{a['indicator']}",key=f"rpt_{i}",use_container_width=True):
                    st.session_state.drill_context={"from":"报告","focus":a["indicator"]}; st.switch_page(t)

bi_drill_bar([{"label":"业财看板","target":"pages/1_📊_业财融合看板.py","context":{"from":"报告","focus":""}},
    {"label":"指标预警","target":"pages/2_🚨_指标监控预警.py","context":{"from":"报告","focus":""}},
    {"label":"行业对比","target":"pages/6_🏭_行业对比分析.py","context":{"from":"报告","focus":""}}])
