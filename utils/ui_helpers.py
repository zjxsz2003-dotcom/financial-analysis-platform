"""
Slite Design System — UI 组件库
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# Slite palette
INK="#2d2f34"; CHARCOAL="#3f434a"; SLATE="#5e646e"; FOG="#9da3af"
CANVAS="#fdf9f4"; WHITE="#ffffff"; DUST="#f9efe4"; MOON="#ecedef"; MIST="#d9dde6"
EMBER="#f67748"; NEPTUNE="#74a6f1"; GREEN="#479a53"; RED="#c0392b"; AMBER="#e67e22"
SHADOW="0 1px 3px rgba(0,0,0,0.04), 0 2px 6px rgba(0,0,0,0.03)"

# Slite chart palette
CHART_COLORS = [EMBER, INK, GREEN, NEPTUNE, AMBER, "#4b51c3", SLATE, DUST]

def chart_layout(fig: go.Figure, h=280, title="") -> go.Figure:
    """统一图表风格"""
    fig.update_layout(
        height=h,
        margin=dict(l=10, r=10, t=30 if title else 20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Microsoft YaHei, sans-serif", size=12, color=CHARCOAL),
        title=dict(text=title, font=dict(size=14, color=INK, family="Georgia, serif")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=11)),
        xaxis=dict(showgrid=False, zeroline=False, color=SLATE),
        yaxis=dict(showgrid=True, gridcolor=MOON, zeroline=False, color=SLATE),
    )
    # apply Slite colors
    if fig.data:
        for i, trace in enumerate(fig.data):
            c = CHART_COLORS[i % len(CHART_COLORS)]
            if hasattr(trace, "marker") and trace.marker:
                if trace.type == "bar": trace.marker.color = c
                elif trace.type in ("scatter", "scattergl"): trace.line.color = c
    return fig

# ── Components ──

def show_watermark():
    st.markdown(f'<div style="text-align:center;font-size:10px;color:{FOG};background:{DUST};padding:2px 0;letter-spacing:1px;">· 邹嘉欣秋招使用 · 最后更新2026年7月 · 持续迭代中 ·</div>', unsafe_allow_html=True)

def bi_topbar(company, period, extra=""):
    st.markdown(f'<div style="background:{INK};color:#fff;padding:6px 20px;border-radius:32px;margin:4px 0 16px;display:flex;align-items:center;gap:16px;font-size:13px;"><b>📊 {company}</b> <span style="opacity:0.7;font-size:11px;">{period}</span> <span style="opacity:0.5;font-size:10px;margin-left:auto;">{extra}</span></div>', unsafe_allow_html=True)

def kpi_row(metrics: list):
    """紧凑KPI行 — Slite粉尘卡片"""
    n = len(metrics); cols = st.columns(n)
    for i, m in enumerate(metrics):
        with cols[i]:
            status = m.get("status", "normal")
            border_c = { "normal": MOON, "warning": AMBER, "danger": RED }.get(status, MOON)
            st.markdown(f'<div style="background:{WHITE};border:1px solid {border_c};border-radius:12px;padding:12px 14px;box-shadow:{SHADOW};">'
                f'<div style="font-size:10px;color:{SLATE};text-transform:uppercase;letter-spacing:0.5px;">{m["label"]}</div>'
                f'<div style="font-size:22px;font-weight:600;color:{INK};font-family:Georgia,serif;margin:4px 0;">{m["value"]}</div>'
                f'<div style="font-size:11px;color:{GREEN if m.get("delta","").startswith("+") else SLATE};">{m.get("delta","")}</div>'
                f'</div>', unsafe_allow_html=True)

def four_step(title, what, why, sowhat, nowwhat, chart=None):
    """What→Why→So What→Now What — Slite卡片"""
    st.markdown(f"**▎{title}**")
    if chart:
        c1, c2 = st.columns([0.55, 0.45])
        with c1: st.plotly_chart(chart_layout(chart), use_container_width=True)
        with c2: st.markdown(f'<div style="font-size:13px;line-height:1.7;background:{WHITE};border:1px solid {MOON};border-radius:16px;padding:16px;box-shadow:{SHADOW};">'
            f'<p><b style="color:{INK};">📌 What</b><br>{what}</p>'
            f'<p><b style="color:{AMBER};">🔍 Why</b><br>{why}</p>'
            f'<p><b style="color:{RED};">⚠️ So What</b><br>{sowhat}</p>'
            f'<p><b style="color:{GREEN};">💡 Now What</b><br>{nowwhat}</p></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="font-size:13px;line-height:1.7;background:{WHITE};border:1px solid {MOON};border-radius:16px;padding:16px;margin:4px 0;box-shadow:{SHADOW};"><p><b style="color:{INK};">📌 What</b> — {what}</p><p><b style="color:{AMBER};">🔍 Why</b> — {why}</p><p><b style="color:{RED};">⚠️ So What</b> — {sowhat}</p><p><b style="color:{GREEN};">💡 Now What</b> — {nowwhat}</p></div>', unsafe_allow_html=True)

def dim_row(dims: list):
    """五大维度行 — 粉尘标签"""
    cols = st.columns(len(dims))
    for i, d in enumerate(dims):
        with cols[i]:
            bc = RED if d["danger"]>0 else (AMBER if d["warning"]>0 else MOON)
            icon = "●" if d["danger"]>0 else ("◉" if d["warning"]>0 else "●")
            color = RED if d["danger"]>0 else (AMBER if d["warning"]>0 else GREEN)
            st.markdown(f'<div style="background:{DUST};border:1px solid {bc};border-radius:40px;padding:10px 14px;text-align:center;">'
                f'<div style="font-size:11px;color:{SLATE};">{icon} {d["name"]}</div>'
                f'<div style="font-size:10px;margin-top:2px;color:{CHARCOAL};">{d["normal"]}/{d["warning"]}/{d["danger"]}/{d["normal"]+d["warning"]+d["danger"]}</div></div>', unsafe_allow_html=True)

def settings_panel(title, func, key=""):
    with st.expander(f"⚙️ {title}", expanded=False):
        func()

def drill_bar(links: list):
    """穿透导航 — pill按钮"""
    st.divider()
    st.caption("🔍 穿透分析")
    cols = st.columns(len(links))
    for i, link in enumerate(links):
        with cols[i]:
            if st.button(f"→ {link['label']}", key=f"drill_{i}", use_container_width=True):
                if link.get("context"): st.session_state.drill_context = link["context"]
                st.switch_page(link["target"])

def alert_strip(alerts: list):
    if not alerts: st.success("✅ 所有指标正常"); return
    cols = st.columns(min(len(alerts), 5))
    for i, a in enumerate(alerts[:5]):
        with cols[i]:
            c = RED if a.get("status")=="danger" else AMBER
            st.markdown(f'<div style="background:{WHITE};border:1px solid {c};border-radius:12px;padding:8px;text-align:center;box-shadow:{SHADOW};"><div style="font-size:10px;color:{SLATE};">{a.get("dim","")}</div><div style="font-size:12px;font-weight:600;color:{c};">{a.get("indicator","")}</div><div style="font-size:11px;color:{INK};">{a.get("value","")}</div></div>', unsafe_allow_html=True)

def badge(status, text=""):
    c = { "normal": GREEN, "warning": AMBER, "danger": RED }.get(status, FOG)
    label = {"normal":"正常","warning":"关注","danger":"预警"}.get(status, "")
    display = text or label
    st.markdown(f'<span style="display:inline-block;padding:2px 10px;border-radius:999px;font-size:11px;font-weight:600;color:#fff;background:{c};">{display}</span>', unsafe_allow_html=True)

def spark(vals, h=50, color=INK):
    fig = go.Figure(go.Scatter(y=vals, mode="lines", line=dict(color=color, width=1.5), fill="tozeroy", fillcolor=color+"14", showlegend=False))
    fig.update_layout(height=h, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig

def section(t, d=""):
    st.markdown(f"<h3>{t}</h3>", unsafe_allow_html=True)
    if d: st.caption(d)

def breadcrumb(curr, parent=None):
    if parent and parent.get("from"):
        c = st.columns([1,10])
        with c[0]:
            if st.button("← 返回", key=f"back_{curr[:4]}", use_container_width=True):
                pm = {"业":"pages/1_📊_业财融合看板.py","指":"pages/2_🚨_指标监控预警.py","预":"pages/3_💰_预算偏差分析.py","战":"pages/4_🎯_战略目标追踪.py","报":"pages/5_📄_分析报告生成.py","行":"pages/6_🏭_行业对比分析.py"}
                for k,v in pm.items():
                    if k in parent["from"]: st.switch_page(v); break
        with c[1]: st.caption(f"← {parent['from']} | {parent.get('focus','')}")
        st.session_state.drill_context = {}

# 兼容别名
bi_kpi_row=kpi_row; bi_dimension_row=dim_row; bi_breadcrumb=breadcrumb; bi_drill_bar=drill_bar
bi_alert_strip=alert_strip; bi_badge=badge; bi_sparkline=spark; bi_settings_panel=settings_panel
bi_section=section; four_step_card=four_step; compact_chart=chart_layout; bi_drill_bar=drill_bar
