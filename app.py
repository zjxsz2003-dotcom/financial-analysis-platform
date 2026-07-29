"""
企业财务经营分析预警系统 — 主入口
自动跳转到数据导入页面
"""
import streamlit as st
from config import COLORS

st.set_page_config(
    page_title="企业经营分析预警系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 水印顶栏 - 所有页面可见
st.markdown("""
<div style="text-align:center;font-size:11px;color:#8899aa;background:#f0f2f5;
padding:3px 0;letter-spacing:1px;border-bottom:1px solid #e0e4e8;margin:-1rem -1rem 0.5rem -1rem;">
邹嘉欣秋招使用 · 最后更新2026年7月 · 持续迭代中
</div>
""", unsafe_allow_html=True)

# 检查数据是否已加载
if not st.session_state.get("data_loaded", False):
    st.switch_page("pages/0_📥_数据导入.py")

# 如果已加载，显示首页
from modules.data_loader import get_company_name, get_data_source

company = get_company_name()
source = get_data_source()

# Slite Design System 全局CSS
st.markdown("""
<style>
    /* === Slite: Warm Parchment + Ember Accent === */

    /* ── Canvas ── */
    .stApp { background: #fdf9f4; font-family: 'Inter', 'Microsoft YaHei', sans-serif; }
    .main .block-container { padding: 1.5rem 2rem 1rem 2rem; max-width: 1280px; }

    /* ── Typography ── */
    h1 { font-family: 'Georgia', 'Noto Serif SC', serif !important; font-size: 28px !important; font-weight: 400 !important; color: #2d2f34 !important; letter-spacing: -0.5px !important; margin: 24px 0 8px 0 !important; }
    h2 { font-family: 'Georgia', 'Noto Serif SC', serif !important; font-size: 22px !important; font-weight: 400 !important; color: #2d2f34 !important; margin: 20px 0 6px 0 !important; }
    h3 { font-family: 'Inter', 'Microsoft YaHei', sans-serif !important; font-size: 17px !important; font-weight: 600 !important; color: #3f434a !important; margin: 16px 0 4px 0 !important; }
    .stMarkdown p, .stMarkdown li, .stMarkdown span { font-size: 15px; color: #3f434a; line-height: 1.5; }
    .stCaption { color: #5e646e !important; font-size: 13px !important; }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] { background: #fdf9f4; border-right: 1px solid #ecedef; }
    section[data-testid="stSidebar"] * { color: #3f434a !important; }
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color: #2d2f34 !important; }

    /* ── Metric Cards ── */
    div[data-testid="stMetric"] { background: #ffffff; border: 1px solid #ecedef; border-radius: 12px; padding: 14px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    div[data-testid="stMetric"] label { font-size: 11px !important; color: #5e646e !important; text-transform: uppercase; letter-spacing: 0.5px; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 600 !important; color: #2d2f34 !important; font-family: 'Georgia',serif !important; }

    /* ── Buttons: Pill ── */
    div.stButton > button { border-radius: 999px !important; padding: 8px 22px !important; font-size: 14px !important; font-weight: 500 !important; border: 2px solid #3f434a !important; background: transparent !important; color: #3f434a !important; transition: all 130ms ease !important; }
    div.stButton > button:hover { background: #3f434a !important; color: #fff !important; border-color: #3f434a !important; }
    /* Primary (Ember) button */
    div.stButton > button[kind="primary"] { background: #f67748 !important; color: #fff !important; border: 2px solid #f67748 !important; }
    div.stButton > button[kind="primary"]:hover { background: #e06532 !important; border-color: #e06532 !important; }

    /* ── Expander (Accordion) ── */
    .stExpander { background: #ffffff; border: 1px solid #ecedef; border-radius: 16px; margin: 8px 0; }
    .stExpander summary { font-size: 15px; font-weight: 500; color: #2d2f34; padding: 12px 16px; }

    /* ── Data Tables ── */
    .stDataFrame { border-radius: 12px; overflow: hidden; border: 1px solid #ecedef; }
    .stDataFrame th { background: #f9efe4 !important; color: #2d2f34 !important; font-size: 12px !important; font-weight: 600 !important; padding: 10px 14px !important; text-transform: none !important; letter-spacing: 0 !important; }
    .stDataFrame td { font-size: 13px !important; padding: 8px 14px !important; color: #3f434a !important; font-family: 'Inter',sans-serif !important; }
    .stDataFrame tr:nth-child(even) td { background: #fdf9f4; }

    /* ── Dividers ── */
    hr { margin: 24px 0 !important; border-color: #ecedef !important; }

    /* ── Select / Input ── */
    .stSelectbox label, .stTextInput label, .stNumberInput label { font-size: 13px !important; color: #3f434a !important; }
    .stSelectbox > div, .stTextInput > div { border-radius: 8px !important; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab"] { font-size: 15px !important; color: #5e646e !important; }
    .stTabs [aria-selected="true"] { color: #f67748 !important; }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown(f"""
    <div style="padding:8px 0;text-align:center;">
        <h3 style="margin:0;color:{COLORS['primary']};">📊 经营分析预警</h3>
        <p style="color:{COLORS['text_light']};font-size:11px;margin:2px 0;">财务BP智能助手</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    st.markdown(f"""
    <div class="bi-card">
        <span style="font-size:10px;color:{COLORS['text_light']};">📌 当前公司</span><br>
        <span style="font-size:14px;font-weight:700;color:{COLORS['text']};">{company}</span><br>
        <span style="font-size:10px;color:{COLORS['text_light']};">数据来源：{source}</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # API Key
    api_key = st.text_input("DeepSeek API Key（可选）", type="password",
                            placeholder="输入激活AI分析", label_visibility="collapsed")
    if api_key:
        import os
        os.environ["DEEPSEEK_API_KEY"] = api_key

    anonymize = st.checkbox("公司名称脱敏", value=False)
    if anonymize != st.session_state.get("anonymize", False):
        st.session_state.anonymize = anonymize
        st.rerun()

    st.divider()
    if st.button("📥 重新导入数据", use_container_width=True):
        st.session_state.data_loaded = False
        st.switch_page("pages/0_📥_数据导入.py")

    st.caption("v3.0 · 最后更新: 2026年7月 · 持续迭代中")


# 首页内容
st.markdown(f"""
<div style="text-align:center;padding:10px 0;">
    <h1 style="color:{COLORS['primary']};margin:0;">📊 {company} — 经营分析</h1>
    <p style="color:{COLORS['text_light']};font-size:13px;">业财融合 · 指标预警 · 预算偏差 · 战略追踪 · 智能报告</p>
</div>
""", unsafe_allow_html=True)
st.divider()

# 快速导航
cols = st.columns(6)
targets = [
    ("📊\n业财看板", "pages/1_📊_业财融合看板.py"),
    ("🚨\n指标预警", "pages/2_🚨_指标监控预警.py"),
    ("💰\n预算分析", "pages/3_💰_预算偏差分析.py"),
    ("🎯\n战略追踪", "pages/4_🎯_战略目标追踪.py"),
    ("🏭\n行业对比", "pages/6_🏭_行业对比分析.py"),
    ("📄\n生成报告", "pages/5_📄_分析报告生成.py"),
]
for i, (label, target) in enumerate(targets):
    with cols[i]:
        if st.button(label, key=f"home_nav_{i}", use_container_width=True):
            st.switch_page(target)
