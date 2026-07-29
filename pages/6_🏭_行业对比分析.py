"""
行业对比与动态分析 — v3全新模块
"""
import streamlit as st
import pandas as pd
from config import COLORS, ALERT_COLORS
from modules.data_loader import is_data_loaded, get_company_name, get_years
from modules.kpi_engine import calc_all_kpis, get_alert_summary
from modules.industry_analysis import get_radar_chart, get_industry_comparison_table, INDUSTRY_NEWS_DEMO
from utils.ui_helpers import bi_kpi_row, bi_breadcrumb, bi_drill_bar, bi_section

if not is_data_loaded():
    st.switch_page("pages/0_📥_数据导入.py")

company = get_company_name()
years = get_years()
latest = years[-1]
kpis = calc_all_kpis()

drill = st.session_state.get("drill_context", {})
bi_breadcrumb("行业对比", drill)
st.markdown(f"<h3>🏭 行业对比与动态分析 — {company}</h3>", unsafe_allow_html=True)

# ============================================================
# Tab切换
# ============================================================
tab_a, tab_b, tab_c = st.tabs(["📊 财务对标", "📰 行业动态", "🔍 竞争格局"])

# ============================================================
# Tab A: 财务对标
# ============================================================
with tab_a:
    bi_section("五维雷达图：公司与行业均值对比")

    # 雷达图
    radar_dims = ["盈利能力", "偿债能力", "营运能力", "成长能力", "现金流质量"]
    company_vals = {
        "盈利能力": abs(kpis["盈利能力"]["ROE"]["current"]),
        "偿债能力": max(30 - abs(kpis["偿债能力"]["资产负债率"]["current"]), 0),
        "营运能力": abs(kpis["营运能力"]["存货周转率"]["current"]),
        "成长能力": abs(kpis["成长能力"]["收入增长率"]["current"]),
        "现金流质量": abs(kpis["现金流质量"]["经营现金流/净利润"]["current"]) * 10,
    }
    industry_vals = {
        "盈利能力": 15, "偿债能力": 20, "营运能力": 7,
        "成长能力": 15, "现金流质量": 10,
    }

    radar_fig = get_radar_chart(company_vals, industry_vals, radar_dims)
    st.plotly_chart(radar_fig, use_container_width=True)

    # 对标表格
    bi_section("关键指标行业对标明细")
    from modules.data_loader import get_industry_benchmarks
    bench = get_industry_benchmarks()
    comp_df = get_industry_comparison_table(kpis, bench)
    st.dataframe(comp_df, use_container_width=True, hide_index=True, height=350)

    st.download_button("📥 下载对标数据CSV",
                       data=comp_df.to_csv(index=False).encode("utf-8-sig"),
                       file_name="行业对标.csv", mime="text/csv", key="dl_industry")

# ============================================================
# Tab B: 行业动态
# ============================================================
with tab_b:
    bi_section("行业政策、技术动向与市场趋势")
    st.caption("数据来源：公开新闻/研报/监管公告（Demo数据，实际使用时通过web-access实时获取）")

    # 筛选器
    cats = ["全部"] + sorted(set(n["category"] for n in INDUSTRY_NEWS_DEMO))
    selected_cat = st.selectbox("筛选类别", cats, key="news_filter")

    filtered_news = INDUSTRY_NEWS_DEMO if selected_cat == "全部" else [n for n in INDUSTRY_NEWS_DEMO if n["category"] == selected_cat]

    for news in filtered_news:
        cat_color_map = {
            "政策法规": COLORS["red"], "技术动向": COLORS["accent"],
            "竞争格局": COLORS["amber"], "市场动向": COLORS["green"],
        }
        cat_color = cat_color_map.get(news["category"], COLORS["accent"])

        with st.expander(f"{news['date']} | [{news['category']}] {news['title']}", expanded=False):
            st.markdown(f"""
            <div style="font-size:11px;line-height:1.7;">
            <b>来源：</b>{news['source']}<br>
            <b>影响分析：</b>{news['impact']}
            </div>
            """, unsafe_allow_html=True)

    # 手动添加动态
    bi_section("✏️ 手动添加行业动态")
    with st.form("add_news"):
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            new_date = st.text_input("日期（如2025-07）", key="new_date")
        with c2:
            new_cat = st.selectbox("类别", ["政策法规", "技术动向", "竞争格局", "市场动向"], key="new_cat")
        with c3:
            new_title = st.text_input("标题", key="new_title")
        new_impact = st.text_area("影响分析", key="new_impact", height=68)
        if st.form_submit_button("添加动态"):
            if new_title and new_impact:
                st.success("已添加（本次会话有效）")
                INDUSTRY_NEWS_DEMO.insert(0, {"date": new_date, "category": new_cat, "title": new_title, "impact": new_impact, "source": "手动录入"})
                st.rerun()

# ============================================================
# Tab C: 竞争格局
# ============================================================
with tab_c:
    bi_section("主要竞争对手对比")
    st.caption("以下为消费电子/精密制造行业主要竞争对手（Demo数据）")

    # 竞争对手对比表
    peers_data = pd.DataFrame([
        {"公司":"立讯精密","代码":"002475","市值(亿元)":2850,"收入(亿元)":3323,"净利(亿元)":182,"毛利率":11.9,"ROE":17.5,"研发费率":3.4,"核心优势":"苹果产业链+汽车电子+通信"},
        {"公司":"歌尔股份","代码":"002241","市值(亿元)":1200,"收入(亿元)":1050,"净利(亿元)":42,"毛利率":15.2,"ROE":8.5,"研发费率":6.2,"核心优势":"声学/光学+VR/MR组件"},
        {"公司":"舜宇光学","代码":"02382","市值(亿元)":1800,"收入(亿元)":380,"净利(亿元)":28,"毛利率":22.5,"ROE":12.1,"研发费率":8.5,"核心优势":"手机镜头+车载光学"},
        {"公司":"瑞声科技","代码":"02018","市值(亿元)":350,"收入(亿元)":210,"净利(亿元)":15,"毛利率":25.8,"ROE":6.2,"研发费率":9.8,"核心优势":"声学元器件+精密结构件"},
        {"公司":"工业富联","代码":"601138","市值(亿元)":4200,"收入(亿元)":5200,"净利(亿元)":230,"毛利率":7.8,"ROE":16.8,"研发费率":2.1,"核心优势":"云计算+AI服务器+工业互联网"},
    ])
    st.dataframe(peers_data, use_container_width=True, hide_index=True, height=200)

    # 竞争优劣势分析
    st.divider()
    st.markdown(f"""
    <div style="font-size:11px;line-height:1.8;background:#fff;padding:12px 16px;border-radius:2px;">
    <b style="color:{COLORS['accent']};">📌 立讯精密竞争优势</b><br>
    ① 深度绑定苹果生态，消费电子基本盘稳固（第一大客户占比约52%）<br>
    ② 汽车业务高速增长差异化突破，2025年收入超245亿，毛利率持续提升至16%+<br>
    ③ 通信互联受益AI算力周期，高速连接器技术壁垒高，毛利率22%+为三大板块最高<br>
    ④ 全球化产能布局（越南/印度/墨西哥），有效应对关税风险<br><br>

    <b style="color:{COLORS['red']};">⚠️ 潜在风险与挑战</b><br>
    ① 大客户依赖度虽在下降(前5大从80%降至74%)，仍处于高位<br>
    ② 消费电子毛利率(11-12%)显著低于同行(歌尔15%/舜宇22%)，盈利质量需改善<br>
    ③ 汽车业务研发投入大+爬坡期长，短期拖累整体ROE<br>
    ④ 地缘政治风险：中美科技脱钩若升级，苹果供应链转移风险加大<br><br>

    <b style="color:{COLORS['green']};">💡 战略建议</b><br>
    ① 加速汽车+通信高毛利业务占比提升(目标从17%→25%)<br>
    ② 推动消费电子从OEM→ODM/JDM模式升级，提升附加值<br>
    ③ 强化研发资本化+供应链金融，优化现金流和资产效率
    </div>
    """, unsafe_allow_html=True)

# === 穿透 ===
bi_drill_bar([
    {"label":"查看业财看板","target":"pages/1_📊_业财融合看板.py","context":{"from":"行业对比","focus":"业财联动"}},
    {"label":"查看指标预警","target":"pages/2_🚨_指标监控预警.py","context":{"from":"行业对比","focus":"预警详情"}},
    {"label":"生成分析报告","target":"pages/5_📄_分析报告生成.py","context":{"from":"行业对比","focus":"汇总报告"}},
])
