"""
UI 组件库 — 企业蓝白版
"""
from __future__ import annotations
from typing import Sequence, Optional
import html
import plotly.graph_objects as go
import streamlit as st

from config import C, STATUS_COLOR, STATUS_LABEL


# ════════════════════════════════════════════════════════════
# 页头 / 区块
# ════════════════════════════════════════════════════════════
def page_head(title: str, subtitle: str = ""):
    st.markdown(
        f'<div class="page-head"><div class="t">{html.escape(title)}</div>'
        f'<div class="s">{html.escape(subtitle)}</div></div>',
        unsafe_allow_html=True,
    )


def section(title: str, desc: str = ""):
    st.markdown(
        f'<div class="sec"><span class="bar"></span><span class="t">{html.escape(title)}</span>'
        f'<span class="d">{html.escape(desc)}</span></div>',
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════
# KPI 卡片组
# ════════════════════════════════════════════════════════════
def kpi_row(items: Sequence[dict], cols: int = 0):
    """
    items: [{"label","value","unit","delta","delta_cls","note","color"}]
    """
    n = len(items)
    if cols:
        # 分行渲染
        for s in range(0, n, cols):
            kpi_row(items[s:s + cols])
        return
    cols_html = []
    for it in items:
        color = it.get("color", C["accent"])
        d = it.get("delta", "")
        dcls = it.get("delta_cls", "")
        if dcls == "auto" and d:
            dcls = "pos" if not str(d).startswith("-") and "▼" not in str(d) else "neg"
        dstyle = f' style="color:{C["good"]}"' if dcls == "pos" else (
            f' style="color:{C["bad"]}"' if dcls == "neg" else "")
        note = f'<div class="n">{html.escape(it["note"])}</div>' if it.get("note") else ""
        cols_html.append(
            f'<div class="kpi" style="border-top-color:{color}">'
            f'<div class="l">{html.escape(it["label"])}</div>'
            f'<div class="v">{html.escape(str(it["value"]))}'
            f'<span class="u">{html.escape(it.get("unit",""))}</span></div>'
            f'<div class="c"{dstyle}>{html.escape(str(d))}</div>{note}</div>'
        )
    st.markdown(f'<div class="kpi-grid">{"".join(cols_html)}</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# 分析结论框
# ════════════════════════════════════════════════════════════
def insight(title: str, blocks: Sequence[tuple], kind: str = ""):
    """
    blocks: [(key, text)]  key ∈ {What, Why, SoWhat, NowWhat, 结论, 风险, 建议}
    """
    kmap = {"What": ("k1", "现象"), "Why": ("k2", "成因"), "SoWhat": ("k3", "影响"),
            "NowWhat": ("k4", "建议"), "结论": ("k1", "结论"), "风险": ("k3", "风险"),
            "建议": ("k4", "建议"), "提示": ("k2", "提示"), "洞察": ("k2", "洞察")}
    lines = []
    for k, txt in blocks:
        cls, cn = kmap.get(k, ("k1", k))
        lines.append(f'<div class="ln"><span class="k {cls}">{cn}｜</span>{txt}</div>')
    border = {"w": C["warn"], "d": C["bad"], "g": C["good"]}.get(kind, C["accent"])
    st.markdown(
        f'<div class="insight" style="border-left-color:{border}">'
        f'<span class="hd">{html.escape(title)}</span>{"".join(lines)}</div>',
        unsafe_allow_html=True,
    )


def exec_summary(headline: str, bullets: Sequence, tone: str = "", title: str = "本页核心结论"):
    """
    页面顶部的文字结论区
    bullets: [(小标题, 正文)] 或 [正文]
    """
    color = {"w": C["warn"], "d": C["bad"], "g": C["good"]}.get(tone, C["primary"])
    items = []
    for j, b in enumerate(bullets, start=1):
        if isinstance(b, (tuple, list)):
            sub, txt = b
            items.append(
                f'<div class="ln" style="margin:6px 0">'
                f'<span style="display:inline-block;min-width:18px;height:18px;line-height:18px;'
                f'text-align:center;border-radius:3px;background:{C["b100"]};color:{C["primary"]};'
                f'font-size:11px;font-weight:700;margin-right:6px">{j}</span>'
                f'<b style="color:{C["navy"]}">{sub}</b>　{txt}</div>')
        else:
            items.append(
                f'<div class="ln" style="margin:6px 0">'
                f'<span style="display:inline-block;min-width:18px;height:18px;line-height:18px;'
                f'text-align:center;border-radius:3px;background:{C["b100"]};color:{C["primary"]};'
                f'font-size:11px;font-weight:700;margin-right:6px">{j}</span>{b}</div>')
    st.markdown(
        f'<div class="insight" style="border-left-width:4px;border-left-color:{color};'
        f'padding:15px 18px">'
        f'<span class="hd" style="font-size:12px;color:{C["muted"]};letter-spacing:1px">'
        f'{html.escape(title)}</span>'
        f'<div style="font-size:14.5px;font-weight:600;color:{C["navy"]};line-height:1.7;'
        f'margin:4px 0 8px">{headline}</div>'
        f'{"".join(items)}</div>', unsafe_allow_html=True)


def note(text: str, kind: str = ""):
    cls = {"w": "note-w", "d": "note-d", "g": "note-g"}.get(kind, "")
    st.markdown(f'<div class="note {cls}">{text}</div>', unsafe_allow_html=True)


def badge(text: str, status: str = "info"):
    m = {"normal": ("bdg-n"), "warning": ("bdg-w"), "danger": ("bdg-d"),
         "info": ("bdg-i"), "na": ("bdg-0")}
    st.markdown(f'<span class="bdg {m.get(status,"bdg-i")}">{html.escape(str(text))}</span>',
                unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# 图表统一风格
# ════════════════════════════════════════════════════════════
def chart(fig: go.Figure, height: int = 280, title: str = "",
          legend_top: bool = True, y_title: str = "", x_title: str = "") -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=12, t=(34 if title else 16), b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Source Han Sans SC, Microsoft YaHei, sans-serif",
                  size=12, color=C["text2"]),
        title=dict(text=f"<b>{title}</b>" if title else "",
                   font=dict(size=13.5, color=C["navy"]), x=0, xanchor="left", y=0.98),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11), bgcolor="rgba(0,0,0,0)") if legend_top else dict(font=dict(size=11)),
        hoverlabel=dict(font_size=12, font_family="Microsoft YaHei"),
        xaxis=dict(showgrid=False, zeroline=False, linecolor=C["line"],
                   tickfont=dict(size=11, color=C["muted"]), title=x_title),
        yaxis=dict(showgrid=True, gridcolor=C["line2"], zeroline=False,
                   tickfont=dict(size=11, color=C["muted"]), title=y_title),
        separators=",",
    )
    return fig


def style_series(fig: go.Figure, palette=None) -> go.Figure:
    pal = palette or C["chart"]
    for i, tr in enumerate(fig.data):
        c = pal[i % len(pal)]
        if tr.type == "bar" and hasattr(tr, "marker"):
            tr.marker.color = c
            tr.marker.line = dict(width=0)
        elif tr.type in ("scatter", "scattergl") and hasattr(tr, "line"):
            tr.line.color = c
            if hasattr(tr, "marker"):
                tr.marker.color = c
    return fig


def show(fig: go.Figure, height: int = 280, title: str = "", styled: bool = False):
    st.plotly_chart(chart(fig, height, title), use_container_width=True,
                    config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]})


def sparkline(vals, height: int = 46, color: str = None) -> go.Figure:
    color = color or C["accent"]
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    fig = go.Figure(go.Scatter(
        y=list(vals), mode="lines", line=dict(color=color, width=1.6),
        fill="tozeroy", fillcolor=f"rgba({r},{g},{b},0.12)", hoverinfo="skip"))
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=2, b=2),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False), showlegend=False)
    return fig


def waterfall(x, y, measure=None, height=300, title="", pos_color=None, neg_color=None,
              total_color=None, text_fmt="{:,.0f}"):
    pos_color = pos_color or C["accent"]
    neg_color = neg_color or C["bad"]
    total_color = total_color or C["primary"]
    if measure is None:
        measure = ["absolute"] + ["relative"] * (len(x) - 2) + ["total"]
    fig = go.Figure(go.Waterfall(
        orientation="v", measure=measure, x=list(x), y=list(y),
        text=[text_fmt.format(v) if v is not None else "" for v in y],
        textposition="outside", textfont=dict(size=11),
        connector=dict(line=dict(color=C["line"], width=1)),
        increasing=dict(marker=dict(color=pos_color)),
        decreasing=dict(marker=dict(color=neg_color)),
        totals=dict(marker=dict(color=total_color)),
    ))
    fig.update_layout(showlegend=False)
    return chart(fig, height, title)


def gauge_bar(name: str, value: float, max_value: float = 100,
              color: str = None, fmt: str = "{:.0f}") -> str:
    pct_v = 0 if not max_value else max(0.0, min(100.0, value / max_value * 100))
    color = color or (C["bad"] if pct_v >= 70 else (C["warn"] if pct_v >= 45 else C["good"]))
    return (f'<div class="gauge-row"><div class="nm">{html.escape(name)}</div>'
            f'<div class="bar"><div class="fill" style="width:{pct_v:.1f}%;background:{color}"></div></div>'
            f'<div class="vl" style="color:{color}">{fmt.format(value)}</div></div>')


def score_gauge(score: float, label: str = "综合风险分") -> str:
    lvl, stt = risk_level(score)
    color = STATUS_COLOR.get(stt, C["neutral"])
    return (f'<div class="risk-card">'
            f'<div style="font-size:11px;color:{C["muted"]}">{html.escape(label)}</div>'
            f'<div style="font-size:38px;font-weight:700;color:{color};'
            f'font-variant-numeric:tabular-nums;line-height:1.1">{score:.0f}</div>'
            f'<div style="font-size:13px;font-weight:600;color:{color};margin-top:2px">{lvl}</div>'
            f'<div style="font-size:10.5px;color:{C["faint"]};margin-top:3px">0 = 低风险 · 100 = 高风险</div>'
            f'</div>')


def risk_level(score: float):
    from config import RISK_LEVELS
    for lo, hi, name, stt in RISK_LEVELS:
        if lo <= score < hi:
            return name, stt
    return "高风险", "danger"


# ════════════════════════════════════════════════════════════
# 导航
# ════════════════════════════════════════════════════════════
PAGE_MAP = {
    "导入": "pages/0_数据导入.py",
    "诊断": "pages/1_经营诊断.py",
    "归因": "pages/2_业财归因.py",
    "风险": "pages/3_财务风险.py",
    "预算": "pages/4_预算与战略.py",
    "报告": "pages/5_分析报告.py",
}


def drill_bar(links: Sequence[dict], label: str = "联动分析"):
    st.markdown(
        f'<div class="sec" style="margin-top:22px"><span class="bar"></span>'
        f'<span class="t">{html.escape(label)}</span></div>', unsafe_allow_html=True)
    cols = st.columns(len(links))
    for i, lk in enumerate(links):
        with cols[i]:
            if st.button(f"→ {lk['label']}", key=f"drill_{i}_{lk['label'][:6]}",
                         use_container_width=True):
                if lk.get("context"):
                    st.session_state.drill_context = lk["context"]
                st.switch_page(lk["target"])


def breadcrumb(current: str):
    ctx = st.session_state.get("drill_context") or {}
    if not ctx.get("from"):
        return
    c = st.columns([1, 9])
    with c[0]:
        if st.button("← 返回", key=f"bk_{current[:4]}", use_container_width=True):
            tgt = PAGE_MAP.get(ctx["from"][:2])
            if tgt:
                st.switch_page(tgt)
    with c[1]:
        st.caption(f"穿透路径：{ctx.get('from','')} → {current}"
                   + (f"｜关注点：{ctx.get('focus','')}" if ctx.get("focus") else ""))
