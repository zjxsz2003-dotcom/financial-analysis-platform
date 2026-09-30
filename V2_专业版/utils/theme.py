"""
全局主题 — 企业蓝白专业风
统一注入 CSS，所有页面共用
"""
from __future__ import annotations
import streamlit as st
from config import C, PAGE_TITLE, PAGE_ICON, LAYOUT

_CSS = f"""
<style>
/* ══════════ 基础画布 ══════════ */
.stApp {{
    background: {C['bg']};
    font-family: "Source Han Sans SC","Noto Sans SC","Microsoft YaHei","PingFang SC",
                 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}}
.main .block-container {{
    padding: 1.2rem 2.2rem 2.5rem 2.2rem;
    max-width: 1440px;
}}
.block-container {{ animation: fadein .25s ease; }}
@keyframes fadein {{ from{{opacity:0;transform:translateY(4px)}} to{{opacity:1;transform:none}} }}

/* ══════════ 排版 ══════════ */
h1, h2, h3, h4 {{
    font-family: "Source Han Sans SC","Microsoft YaHei",sans-serif !important;
    color: {C['navy']} !important;
    letter-spacing: .2px;
}}
h1 {{ font-size: 25px !important; font-weight: 700 !important; margin: 4px 0 2px !important; }}
h2 {{ font-size: 20px !important; font-weight: 700 !important; margin: 8px 0 2px !important; }}
h3 {{ font-size: 16px !important; font-weight: 600 !important; margin: 10px 0 2px !important; }}
h4 {{ font-size: 14px !important; font-weight: 600 !important; }}
p, li, span, div {{ color: {C['text']}; }}
.stCaption, small {{ color: {C['muted']} !important; font-size: 12px !important; }}
hr {{ border: 0 !important; border-top: 1px solid {C['line']} !important; margin: 18px 0 !important; }}

/* ══════════ 侧边栏 ══════════ */
section[data-testid="stSidebar"] {{
    background: {C['white']};
    border-right: 1px solid {C['line']};
}}
section[data-testid="stSidebar"] .block-container {{ padding-top: 1rem; }}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{ color: {C['primary']} !important; }}
section[data-testid="stSidebar"] * {{ color: {C['text2']}; }}
[data-testid="stSidebarNav"] ul li a:hover {{ background: {C['b100']} !important; }}

/* ══════════ 顶栏水印 ══════════ */
.wm-bar {{
    background: linear-gradient(90deg,{C['navy']} 0%,{C['primary']} 100%);
    color:#fff; font-size:11px; letter-spacing:1.2px; text-align:center;
    padding:4px 0; border-radius:0 0 6px 6px;
    margin:-1rem -2.2rem 10px -2.2rem;
}}

/* ══════════ 区块标题 ══════════ */
.sec {{
    display:flex; align-items:center; gap:9px;
    margin:20px 0 10px 0;
}}
.sec .bar {{ width:4px; height:16px; background:{C['primary']}; border-radius:2px; }}
.sec .t {{ font-size:15.5px; font-weight:700; color:{C['navy']}; }}
.sec .d {{ font-size:12px; color:{C['muted']}; margin-left:4px; }}

/* ══════════ 页面页头 ══════════ */
.page-head {{
    background:{C['white']}; border:1px solid {C['line']};
    border-left:4px solid {C['primary']};
    border-radius:8px; padding:14px 18px; margin-bottom:14px;
    box-shadow:0 1px 2px rgba(16,42,70,.05);
}}
.page-head .t {{ font-size:19px; font-weight:700; color:{C['navy']}; }}
.page-head .s {{ font-size:12px; color:{C['muted']}; margin-top:2px; }}

/* ══════════ KPI 卡片 ══════════ */
.kpi-grid {{ display:flex; gap:10px; flex-wrap:wrap; margin:6px 0 4px; }}
.kpi {{
    flex:1 1 130px; min-width:124px;
    background:{C['white']}; border:1px solid {C['line']};
    border-top:3px solid {C['accent']};
    border-radius:7px; padding:10px 12px;
    box-shadow:0 1px 2px rgba(16,42,70,.05);
}}
.kpi .l {{ font-size:11px; color:{C['muted']}; letter-spacing:.3px; }}
.kpi .v {{ font-size:21px; font-weight:700; color:{C['navy']};
           font-variant-numeric:tabular-nums; margin:3px 0 1px; letter-spacing:-.3px; }}
.kpi .u {{ font-size:11px; font-weight:500; color:{C['muted']}; margin-left:1px; }}
.kpi .c {{ font-size:11.5px; font-variant-numeric:tabular-nums; }}
.kpi .n {{ font-size:11px; color:{C['muted']}; margin-top:2px; }}

/* ══════════ 专业财务报表表格 ══════════ */
.fintable-wrap {{
    background:{C['white']}; border:1px solid {C['line']};
    border-radius:7px; overflow:hidden; box-shadow:0 1px 2px rgba(16,42,70,.04);
}}
table.fintable {{ width:100%; border-collapse:collapse; font-size:13px; }}
table.fintable thead th {{
    background:{C['primary']}; color:#fff; font-weight:600; font-size:12px;
    padding:9px 12px; text-align:right; white-space:nowrap;
    border-right:1px solid rgba(255,255,255,.18);
}}
table.fintable thead th:first-child {{ text-align:left; }}
table.fintable thead tr.sub th {{
    background:{C['accent']}; font-size:11px; padding:5px 12px; font-weight:500;
}}
table.fintable tbody td {{
    padding:7px 12px; border-bottom:1px solid {C['line2']};
    font-variant-numeric:tabular-nums; text-align:right; color:{C['text']};
}}
table.fintable tbody td:first-child {{
    text-align:left; color:{C['text']}; font-variant-numeric:normal;
}}
table.fintable tbody tr:nth-child(even) td {{ background:{C['b050']}; }}
table.fintable tbody tr:hover td {{ background:{C['b100']}; }}
table.fintable td.neg {{ color:{C['bad']}; }}
table.fintable td.pos {{ color:{C['good']}; }}
table.fintable tr.grp td {{
    background:{C['b100']} !important; font-weight:600; color:{C['navy']}; font-size:12.5px;
}}
table.fintable tr.sub td {{
    background:{C['b050']} !important; font-weight:700; color:{C['text']};
    border-top:1px solid {C['b300']};
}}
table.fintable tr.tot td {{
    background:{C['b200']} !important; font-weight:700; color:{C['navy']};
    border-top:2px solid {C['primary']};
}}
table.fintable td.ind1 {{ padding-left:26px; }}
table.fintable td.ind2 {{ padding-left:40px; }}
table.fintable td.lbl {{ white-space:nowrap; }}
.tbl-cap {{ font-size:11.5px; color:{C['muted']}; margin:2px 0 12px; }}

/* ══════════ 徽章 ══════════ */
.bdg {{
    display:inline-block; padding:1px 8px; border-radius:3px;
    font-size:11px; font-weight:600; line-height:17px; white-space:nowrap;
}}
.bdg-n {{ background:{C['good']}1A; color:{C['good']}; border:1px solid {C['good']}44; }}
.bdg-w {{ background:{C['warn']}1A; color:{C['warn']}; border:1px solid {C['warn']}44; }}
.bdg-d {{ background:{C['bad']}1A;  color:{C['bad']};  border:1px solid {C['bad']}44; }}
.bdg-i {{ background:{C['accent']}1A; color:{C['primary']}; border:1px solid {C['accent']}44; }}
.bdg-0 {{ background:{C['line2']}; color:{C['muted']}; border:1px solid {C['line']}; }}

/* ══════════ 分析结论框（What-Why-SoWhat-NowWhat）══════════ */
.insight {{
    background:{C['white']}; border:1px solid {C['line']};
    border-left:3px solid {C['accent']};
    border-radius:7px; padding:13px 16px; margin:8px 0; font-size:13px; line-height:1.75;
}}
.insight .hd {{
    font-size:13.5px; font-weight:700; color:{C['navy']};
    margin-bottom:6px; display:block;
}}
.insight .ln {{ margin:3px 0; }}
.insight .k {{ font-weight:700; margin-right:4px; }}
.insight .k1 {{ color:{C['primary']}; }}
.insight .k2 {{ color:{C['warn']}; }}
.insight .k3 {{ color:{C['bad']}; }}
.insight .k4 {{ color:{C['good']}; }}

/* ══════════ 提示条 ══════════ */
.note {{
    background:{C['b050']}; border:1px solid {C['line']};
    border-left:3px solid {C['accent']};
    border-radius:5px; padding:9px 13px; font-size:12.5px; color:{C['text2']};
    margin:8px 0; line-height:1.65;
}}
.note-w {{ background:#FDF6EC; border-color:#F3DFC0; border-left-color:{C['warn']}; }}
.note-d {{ background:#FBEEEC; border-color:#F2D4CF; border-left-color:{C['bad']}; }}
.note-g {{ background:#EDF7F2; border-color:#C9E6D8; border-left-color:{C['good']}; }}

/* ══════════ Metric / 组件微调 ══════════ */
div[data-testid="stMetric"] {{
    background:{C['white']}; border:1px solid {C['line']};
    border-radius:7px; padding:9px 13px;
    box-shadow:0 1px 2px rgba(16,42,70,.04);
}}
div[data-testid="stMetric"] label {{
    font-size:11px !important; color:{C['muted']} !important;
}}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
    font-size:21px !important; font-weight:700 !important;
    color:{C['navy']} !important; font-variant-numeric:tabular-nums;
}}

/* ══════════ 按钮 ══════════ */
div.stButton > button {{
    border-radius:5px !important; border:1px solid {C['line']} !important;
    background:{C['white']} !important; color:{C['primary']} !important;
    font-size:13px !important; font-weight:500 !important;
    padding:6px 14px !important; transition:all .12s ease !important;
}}
div.stButton > button:hover {{
    background:{C['b100']} !important; border-color:{C['accent']} !important;
}}
div.stButton > button[kind="primary"] {{
    background:{C['primary']} !important; color:#fff !important;
    border-color:{C['primary']} !important;
}}
div.stButton > button[kind="primary"]:hover {{
    background:{C['primary_d']} !important; border-color:{C['primary_d']} !important;
}}

/* ══════════ Expander ══════════ */
.stExpander {{ border:1px solid {C['line']} !important;
    border-radius:7px !important; background:{C['white']} !important; }}
.stExpander summary {{ font-size:13.5px !important; font-weight:600 !important;
    color:{C['navy']} !important; }}

/* ══════════ Tabs ══════════ */
.stTabs [data-baseweb="tab-list"] {{ gap:2px; border-bottom:2px solid {C['line']}; }}
.stTabs [data-baseweb="tab"] {{
    font-size:13.5px !important; color:{C['text2']} !important;
    padding:8px 16px !important; border-radius:5px 5px 0 0 !important;
}}
.stTabs [aria-selected="true"] {{
    color:{C['primary']} !important; font-weight:600 !important;
    background:{C['b100']} !important;
    box-shadow:inset 0 -2px 0 {C['primary']} !important;
}}

/* ══════════ dataframe 兜底样式 ══════════ */
.stDataFrame {{ border-radius:7px; overflow:hidden; border:1px solid {C['line']}; }}
.stDataFrame th {{ background:{C['b200']} !important; color:{C['navy']} !important;
    font-size:12px !important; font-weight:600 !important; }}
.stDataFrame td {{ font-size:12.5px !important; font-variant-numeric:tabular-nums; }}

/* ══════════ 进度条 ══════════ */
.stProgress > div > div > div {{ background:{C['accent']} !important; }}

/* ══════════ 风险评分卡 ══════════ */
.risk-card {{
    background:{C['white']}; border:1px solid {C['line']};
    border-radius:8px; padding:14px 16px; text-align:center;
}}
.gauge-row {{ display:flex; align-items:center; gap:10px; margin:5px 0; }}
.gauge-row .nm {{ flex:0 0 96px; font-size:12px; color:{C['text2']}; text-align:right; }}
.gauge-row .bar {{ flex:1; height:11px; background:{C['line2']}; border-radius:6px; overflow:hidden; }}
.gauge-row .fill {{ height:11px; border-radius:6px; }}
.gauge-row .vl {{ flex:0 0 52px; font-size:12px; font-weight:700;
    font-variant-numeric:tabular-nums; }}
</style>
"""


def apply_theme(title: str = PAGE_TITLE, icon: str = PAGE_ICON, sidebar: str = "expanded"):
    """每个页面顶部调用：注入页面配置 + 全局CSS"""
    try:
        st.set_page_config(page_title=title, page_icon=icon, layout=LAYOUT,
                           initial_sidebar_state=sidebar)
    except Exception:
        pass
    st.markdown(_CSS, unsafe_allow_html=True)


def watermark(text: str = "邹嘉欣 · 企业经营分析与风险预警平台 V2.0 · 分析结论由系统规则引擎自动生成"):
    st.markdown(f'<div class="wm-bar">{text}</div>', unsafe_allow_html=True)
