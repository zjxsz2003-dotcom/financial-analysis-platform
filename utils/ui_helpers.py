"""
UI 复用组件库 v3 — Bloomberg终端风 + 四步法分析组件
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from config import COLORS, ALERT_COLORS, ALERT_ICONS


# ============================================================
# 深色顶栏
# ============================================================
def bi_topbar(company: str, period: str, extra: str = ""):
    st.markdown(f"""
    <div style="background:{COLORS['primary']};color:#fff;padding:8px 16px;
    border-radius:2px;margin-bottom:8px;display:flex;align-items:center;gap:16px;">
        <span style="font-weight:700;font-size:14px;">📊 {company}</span>
        <span style="font-size:11px;opacity:0.8;">{period}</span>
        <span style="font-size:10px;opacity:0.6;">{extra}</span>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# 设置面板
# ============================================================
def bi_settings_panel(title: str, content_func, key_prefix: str = ""):
    """可折叠的设置面板"""
    with st.expander(f"⚙️ {title}", expanded=False):
        content_func()


# ============================================================
# 四步法分析卡片
# ============================================================
def four_step_card(title: str, what: str, why: str, sowhat: str, nowwhat: str, chart=None):
    """What→Why→So What→Now What 四步分析卡片"""
    st.markdown(f"**▎{title}**")

    if chart:
        c1, c2 = st.columns([0.58, 0.42])
        with c1:
            st.plotly_chart(chart, use_container_width=True)
        with c2:
            st.markdown(f"""
            <div style="font-size:11px;line-height:1.6;">
            <p><b style="color:{COLORS['accent']};">📌 What — 发生了什么</b><br>{what}</p>
            <p><b style="color:{COLORS['amber']};">🔍 Why — 为什么会发生</b><br>{why}</p>
            <p><b style="color:{COLORS['red']};">⚠️ So What — 这意味着什么</b><br>{sowhat}</p>
            <p><b style="color:{COLORS['green']};">💡 Now What — 应该怎么调整</b><br>{nowwhat}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="font-size:11px;line-height:1.6;background:#fff;padding:10px 14px;
        border-left:3px solid {COLORS['accent']};margin:4px 0;">
        <p><b style="color:{COLORS['accent']};">📌 What</b> — {what}</p>
        <p><b style="color:{COLORS['amber']};">🔍 Why</b> — {why}</p>
        <p><b style="color:{COLORS['red']};">⚠️ So What</b> — {sowhat}</p>
        <p><b style="color:{COLORS['green']};">💡 Now What</b> — {nowwhat}</p>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# 条件格式数据表格
# ============================================================
def conditional_table(df: pd.DataFrame, status_col: str = "状态", height: int = 200):
    """带条件格式的数据表格"""
    if df.empty:
        st.caption("无数据")
        return

    # 使用st.dataframe + column_config
    col_config = {}
    for col in df.columns:
        col_config[col] = st.column_config.TextColumn(col, width="small")

    styled = df.style.map(
        lambda x: 'background-color: #ffeaea; color: #c0392b; font-weight:600',
        subset=[status_col]
    ).map(
        lambda x: 'background-color: #fff3e0; color: #e67e22; font-weight:600' if x == "关注" else '',
        subset=[status_col]
    )
    st.dataframe(styled, use_container_width=True, hide_index=True, height=height)


# ============================================================
# 迷你图 + 数值并排
# ============================================================
def sparkline_with_value(values: list, current_val, unit: str = "", height: int = 40,
                         color: str = None, status: str = "normal"):
    """迷你趋势图 + 数值并排"""
    c1, c2 = st.columns([2, 1])
    with c1:
        fig = go.Figure()
        line_color = color or ALERT_COLORS.get(status, COLORS["accent"])
        fig.add_trace(go.Scatter(
            y=values, mode="lines",
            line=dict(color=line_color, width=1.5),
            fill="tozeroy", fillcolor=line_color.replace(")", ",0.15)").replace("rgb(", "rgba("),
            showlegend=False,
        ))
        fig.update_layout(
            height=height, margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, visible=False),
        )
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        font_size = "16px" if len(str(current_val)) < 8 else "13px"
        val_color = ALERT_COLORS.get(status, COLORS["text"])
        st.markdown(f"""
        <div style="text-align:right;padding-top:4px;">
            <span style="font-size:{font_size};font-weight:700;color:{val_color};">{current_val}</span>
            <span style="font-size:10px;color:{COLORS['text_light']};">{unit}</span>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# KPI度量行
# ============================================================
def bi_kpi_row(metrics: list, cols_per_row: int = 6):
    n = len(metrics)
    for r in range((n + cols_per_row - 1) // cols_per_row):
        cols = st.columns(cols_per_row)
        for c in range(cols_per_row):
            idx = r * cols_per_row + c
            if idx < n:
                m = metrics[idx]
                with cols[c]:
                    status = m.get("status", "normal")
                    border_c = ALERT_COLORS.get(status, COLORS["border"])
                    st.markdown(f"""
                    <div style="background:#fff;border-left:2px solid {border_c};
                    padding:4px 8px;margin:1px 0;border-radius:1px;">
                        <div style="font-size:9px;color:{COLORS['text_light']};text-transform:uppercase;">{m['label']}</div>
                        <div style="font-size:14px;font-weight:700;color:{COLORS['text']};">{m['value']}</div>
                        <div style="font-size:9px;color:{COLORS['green'] if m.get('delta','').startswith('+') else COLORS['red']};">{m.get('delta','')}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                break


# ============================================================
# 维度行
# ============================================================
def bi_dimension_row(dimensions: list):
    cols = st.columns(len(dimensions))
    for i, d in enumerate(dimensions):
        with cols[i]:
            total = d["normal"] + d["warning"] + d["danger"]
            bc = ALERT_COLORS["danger"] if d["danger"] > 0 else (ALERT_COLORS["warning"] if d["warning"] > 0 else ALERT_COLORS["normal"])
            icon = "🔴" if d["danger"] > 0 else ("🟡" if d["warning"] > 0 else "🟢")
            st.markdown(f"""
            <div style="background:#fff;border:1px solid {bc};padding:6px 8px;text-align:center;border-radius:2px;">
                <div style="font-size:10px;color:{COLORS['text_light']};">{icon} {d['name']}</div>
                <div style="font-size:9px;margin-top:2px;">
                    <span style="color:{ALERT_COLORS['normal']};">{d['normal']}</span>/
                    <span style="color:{ALERT_COLORS['warning']};">{d['warning']}</span>/
                    <span style="color:{ALERT_COLORS['danger']};">{d['danger']}</span>/{total}
                </div>
            </div>
            """, unsafe_allow_html=True)


# ============================================================
# 兼容旧API + 补充导出
# ============================================================
def bi_breadcrumb(current: str, parent: dict = None):
    if parent and parent.get("from"):
        c = st.columns([1, 10])
        with c[0]:
            if st.button("← 返回", key=f"back_{current[:4]}", use_container_width=True):
                page_map = {"业财":"pages/1_📊_业财融合看板.py","指标":"pages/2_🚨_指标监控预警.py",
                           "预算":"pages/3_💰_预算偏差分析.py","战略":"pages/4_🎯_战略目标追踪.py",
                           "报告":"pages/5_📄_分析报告生成.py","行业":"pages/6_🏭_行业对比分析.py"}
                for k, v in page_map.items():
                    if k in parent["from"]: st.switch_page(v); break
        with c[1]: st.caption(f"← {parent['from']} | {parent.get('focus','')}")
        st.session_state.drill_context = {}

def bi_drill_bar(links: list):
    """页面底部穿透导航"""
    st.divider(); st.caption("🔍 穿透分析")
    cols = st.columns(len(links))
    for i, link in enumerate(links):
        with cols[i]:
            if st.button(f"→ {link['label']}", key=f"drill_{i}", use_container_width=True):
                if link.get("context"): st.session_state.drill_context = link["context"]
                st.switch_page(link["target"])

def bi_alert_strip(alerts: list):
    """预警摘要条"""
    if not alerts: st.success("✅ 所有指标正常"); return
    cols = st.columns(min(len(alerts), 5))
    for i, a in enumerate(alerts[:5]):
        with cols[i]:
            c = ALERT_COLORS.get(a.get("status","warning"), "#888")
            st.markdown(f"""<div style="background:#fff;border:1px solid {c};padding:4px 6px;text-align:center;border-radius:2px;margin:2px 0;">
            <div style="font-size:9px;color:{COLORS['text_light']};">{a.get('dim','')}</div>
            <div style="font-size:11px;font-weight:600;color:{c};">{a.get('indicator','')}</div>
            <div style="font-size:10px;">{a.get('value','')}</div></div>""", unsafe_allow_html=True)

def bi_sparkline(values: list, height: int = 50, color: str = None) -> go.Figure:
    """迷你折线图"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=values, mode="lines", line=dict(color=color or COLORS["accent"], width=1.5), showlegend=False))
    fig.update_layout(height=height, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, visible=False))
    return fig

def bi_badge(status: str, text: str = ""):
    """状态徽章"""
    color = ALERT_COLORS.get(status, COLORS["text_light"])
    label = {"normal":"正常","warning":"关注","danger":"预警"}.get(status, "")
    display = text or label
    st.markdown(f"""<span style="display:inline-block;padding:1px 7px;border-radius:8px;font-size:9px;font-weight:600;color:#fff;background:{color};">{display}</span>""", unsafe_allow_html=True)

def bi_section(title: str, desc: str = ""):
    """区块标题"""
    st.markdown(f"**{title}**")
    if desc: st.caption(desc)

# 旧API兼容
kpi_card = lambda l,v,u="",d="",s="normal": bi_kpi_row([{"label":l,"value":v,"delta":d,"status":s}],1)
breadcrumb_nav = bi_breadcrumb
section_header = bi_section
status_badge = bi_badge
mini_trend_chart = bi_sparkline
module_footer_nav = bi_drill_bar
alert_summary_bar = bi_alert_strip
two_column_layout = lambda ch, t, r=0.6: None
