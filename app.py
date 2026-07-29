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

# 检查数据是否已加载
if not st.session_state.get("data_loaded", False):
    st.switch_page("pages/0_📥_数据导入.py")

# 如果已加载，显示首页
from modules.data_loader import get_company_name, get_data_source

company = get_company_name()
source = get_data_source()

# 注入Bloomberg终端风全局CSS
st.markdown("""
<style>
    /* === Bloomberg Terminal Style === */
    .stApp { font-size: 11px; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; background: #f5f6f8; }
    .stMarkdown h1 { font-size: 18px !important; margin: 4px 0 !important; font-weight: 700; }
    .stMarkdown h2 { font-size: 15px !important; margin: 3px 0 !important; font-weight: 700; }
    .stMarkdown h3 { font-size: 13px !important; margin: 2px 0 !important; font-weight: 600; }
    .stMarkdown h4 { font-size: 11px !important; margin: 1px 0 !important; font-weight: 600; }
    div[data-testid="stMetric"] label { font-size: 9px !important; text-transform: uppercase; letter-spacing: 0.5px; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 15px !important; font-weight: 700; font-family: 'Consolas','Courier New',monospace; }
    div[data-testid="stMetric"] div[data-testid="stMetricDelta"] { font-size: 9px !important; }
    .stDataFrame { font-size: 10px; }
    .stDataFrame th { font-size: 9px; padding: 3px 6px !important; background: #1a2332; color: #fff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .stDataFrame td { font-size: 10px; padding: 2px 6px !important; font-family: 'Consolas','Courier New',monospace; }
    .stDataFrame tr:nth-child(even) td { background: #f8f9fc; }
    div.stButton > button { font-size: 10px !important; padding: 3px 10px !important; border-radius: 2px !important; border: 1px solid #d0d4d8 !important; background: #fff !important; color: #2c3e50 !important; }
    div.stButton > button:hover { border-color: #2c5f8a !important; color: #2c5f8a !important; }
    hr { margin: 4px 0 !important; border-color: #e0e4e8; }
    .stExpander { font-size: 11px; }
    .stExpander summary { font-size: 11px; font-weight: 600; }
    section[data-testid="stSidebar"] .stMarkdown { font-size: 10px; }
    section[data-testid="stSidebar"] { background: #1a2332; }
    section[data-testid="stSidebar"] * { color: #d0d4d8 !important; }
    /* 数字等宽字体 */
    [data-testid="stMetricValue"], table td { font-family: 'Consolas','Courier New',monospace !important; }
    /* 紧凑间距 */
    .block-container { padding-top: 1rem !important; padding-bottom: 0 !important; }
    /* 去圆角 */
    * { border-radius: 1px !important; }
    /* Select boxes */
    .stSelectbox label, .stTextInput label, .stNumberInput label { font-size: 10px !important; }
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
