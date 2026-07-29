"""行业对比 — Slite"""
import streamlit as st; import pandas as pd
from modules.data_loader import is_data_loaded, get_company_name
from modules.kpi_engine import calc_all_kpis
from modules.industry_analysis import get_radar_chart, get_industry_comparison_table, INDUSTRY_NEWS_DEMO
from utils.ui_helpers import show_watermark, kpi_row, drill_bar, section, breadcrumb, chart_layout, RED, INK, AMBER, GREEN, WHITE, MOON, SHADOW, SLATE
show_watermark()

if not is_data_loaded(): st.switch_page("pages/0_📥_数据导入.py")

company=get_company_name(); kpis=calc_all_kpis()
drill=st.session_state.get("drill_context",{}); breadcrumb("行业对比",drill)
st.markdown(f'<h2>🏭 行业对比与动态 — {company}</h2>', unsafe_allow_html=True)

tab_a,tab_b,tab_c=st.tabs(["📊 财务对标","📰 行业动态","🔍 竞争格局"])

with tab_a:
    section("五维雷达图")
    radar_dims=["盈利能力","偿债能力","营运能力","成长能力","现金流质量"]
    company_vals={"盈利能力":abs(kpis["盈利能力"]["ROE"]["current"]),"偿债能力":max(30-abs(kpis["偿债能力"]["资产负债率"]["current"]),0),"营运能力":abs(kpis["营运能力"]["存货周转率"]["current"]),"成长能力":abs(kpis["成长能力"]["收入增长率"]["current"]),"现金流质量":abs(kpis["现金流质量"]["经营现金流/净利润"]["current"])*10}
    industry_vals={"盈利能力":15,"偿债能力":20,"营运能力":7,"成长能力":15,"现金流质量":10}
    st.plotly_chart(chart_layout(get_radar_chart(company_vals,industry_vals,radar_dims),300),use_container_width=True)

    from modules.data_loader import get_industry_benchmarks
    comp_df = get_industry_comparison_table(kpis, get_industry_benchmarks())
    st.dataframe(comp_df, use_container_width=True, hide_index=True, height=350)
    st.download_button("📥 下载对标CSV",data=comp_df.to_csv(index=False).encode("utf-8-sig"),file_name="行业对标.csv",mime="text/csv",key="dl_ind")

with tab_b:
    section("行业政策与动态")
    cats=["全部"]+sorted(set(n["category"] for n in INDUSTRY_NEWS_DEMO))
    sc=st.selectbox("筛选",cats,key="nf")
    fn = INDUSTRY_NEWS_DEMO if sc=="全部" else [n for n in INDUSTRY_NEWS_DEMO if n["category"]==sc]
    cm = {"政策法规":RED,"技术动向":INK,"竞争格局":AMBER,"市场动向":GREEN}
    for news in fn:
        with st.expander(f"{news['date']} | [{news['category']}] {news['title']}"):
            st.markdown(f'<span style="color:{SLATE};font-size:12px;">来源：{news["source"]} | 影响：{news["impact"]}</span>',unsafe_allow_html=True)

with tab_c:
    section("主要竞争对手对比")
    peers=pd.DataFrame([
        {"公司":"立讯精密","代码":"002475","市值":2850,"收入":3323,"净利":182,"毛利率":11.9,"ROE":17.5,"研发率":3.4,"优势":"苹果链+汽车+通信"},
        {"公司":"歌尔股份","代码":"002241","市值":1200,"收入":1050,"净利":42,"毛利率":15.2,"ROE":8.5,"研发率":6.2,"优势":"声学/VR组件"},
        {"公司":"舜宇光学","代码":"02382","市值":1800,"收入":380,"净利":28,"毛利率":22.5,"ROE":12.1,"研发率":8.5,"优势":"车载光学"},
        {"公司":"瑞声科技","代码":"02018","市值":350,"收入":210,"净利":15,"毛利率":25.8,"ROE":6.2,"研发率":9.8,"优势":"精密结构件"},
        {"公司":"工业富联","代码":"601138","市值":4200,"收入":5200,"净利":230,"毛利率":7.8,"ROE":16.8,"研发率":2.1,"优势":"AI服务器"},
    ])
    st.dataframe(peers,use_container_width=True,hide_index=True,height=180)

    st.divider()
    st.markdown(f'<div style="font-size:13px;line-height:1.8;background:{WHITE};border:1px solid {MOON};border-radius:16px;padding:16px;box-shadow:{SHADOW};"><b>📌 竞争优势</b><br>①深度绑定苹果生态+汽车高速增长(245亿/16%+)+通信受益AI周期<br>②全球化产能布局(越南/印度/墨西哥)<br><br><b>⚠️ 潜在风险</b><br>①大客户依赖(前5大74%)+消费电子毛利率偏低(11-12%)vs同行<br>②地缘政治：中美科技脱钩风险<br><br><b>💡 战略建议</b><br>①汽车+通信占比17%→25% ②消费电子OEM→ODM/JDM升级 ③强化供应链金融</div>',unsafe_allow_html=True)

drill_bar([{"label":"业财看板","target":"pages/1_📊_业财融合看板.py","context":{"from":"行业对比","focus":"业财联动"}},{"label":"指标预警","target":"pages/2_🚨_指标监控预警.py","context":{"from":"行业对比","focus":"预警"}},{"label":"生成报告","target":"pages/5_📄_分析报告生成.py","context":{"from":"行业对比","focus":"汇总"}}])
