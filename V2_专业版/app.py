"""
企业经营分析与风险预警平台 V2.0 — 首页驾驶舱
一条主线：诊断 → 归因 → 风险 → 决策 → 输出
"""
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.shell import init
from utils import ui
from utils import tables as T
from utils.tables import num, pct, delta
from modules import finance_core as fc
from modules import risk_analysis as ra
from modules.kpi import snapshot, alerts, dim_stats, status_counts
from modules import page_summary as ps
from modules import business_context as bc
from modules.data_loader import (get_company_name, get_company_code, get_years,
                                 get_data_source, available_flags)
from config import C, STATUS_COLOR

init("经营驾驶舱", "◧", step=0)

company = get_company_name()
years = get_years()
model = fc.build_model()
snap = snapshot(model)
al = alerts(snap)
rs = ra.risk_scorecard(model)
risk_lv, risk_st = ra.risk_level(rs["total"])

cnt = status_counts(snap)
tot_valid = max(cnt["normal"] + cnt["warning"] + cnt["danger"], 1)
kpi_health = (cnt["normal"] * 1.0 + cnt["warning"] * 0.5) / tot_valid * 100
risk_health = 100 - (rs["total"] or 50)
health = 0.5 * kpi_health + 0.5 * risk_health

ui.page_head(f"{company}　经营驾驶舱",
             f"{get_company_code()}　｜　{years[0]}–{years[-1]} 年　｜　"
             f"{len(years)} 个报告期　｜　数据来源 {get_data_source()}")

# ══════════ 核心结论 ══════════
try:
    h, bl, tone = ps.summary_home(model, snap, rs, health)
    ui.exec_summary(h, bl, tone, title="核心结论 · 一句话看清当期经营")
    bc.render_brief(model)
except Exception as e:
    st.caption(f"（结论生成跳过：{e}）")

# ══════════ 健康度 + 核心指标 ══════════
L = lambda k: fc._last(model.get(k, []))
hc = st.columns([1.05, 1, 1, 1, 1, 1, 1, 1])
with hc[0]:
    color = (C["good"] if health >= 70 else (C["warn"] if health >= 50 else C["bad"]))
    st.markdown(
        f'<div class="risk-card" style="border-top:3px solid {color}">'
        f'<div style="font-size:11px;color:{C["muted"]}">综合健康度</div>'
        f'<div style="font-size:32px;font-weight:700;color:{color};'
        f'font-variant-numeric:tabular-nums;line-height:1.15">{health:.0f}</div>'
        f'<div style="font-size:11px;color:{C["muted"]}">风险 {num(rs["total"],0)} 分 · '
        f'预警 {cnt["danger"]} 项</div></div>', unsafe_allow_html=True)

cards = [
    ("营业收入", L("revenue"), "亿元", L("rev_growth"), True),
    ("净利润", L("net_profit"), "亿元", L("np_growth"), True),
    ("ROE", L("roe"), "%", None, None),
    ("毛利率", L("gross_margin"), "%", None, None),
    ("经营现金流", L("ocf"), "亿元", None, None),
    ("自由现金流", L("fcf"), "亿元", None, None),
    ("资产负债率", L("debt_ratio"), "%", None, None),
]
for j, (lab, v, unit, gv, is_growth) in enumerate(cards):
    with hc[j + 1]:
        dcls, dtxt = "", ""
        if gv is not None:
            dtxt = delta(gv, 1, "%")
            dcls = "pos" if gv >= 0 else "neg"
        st.markdown(
            f'<div class="kpi"><div class="l">{lab}</div>'
            f'<div class="v">{num(v,1)}<span class="u">{unit}</span></div>'
            f'<div class="c" style="color:{C["good"] if dcls=="pos" else (C["bad"] if dcls=="neg" else C["muted"])}">'
            f'{dtxt}</div></div>', unsafe_allow_html=True)

# ══════════ 预警 ══════════
if al:
    ui.note("　".join(
        f'{"🔴" if a["status"]=="danger" else "🟡"} <b>{a["name"]}</b> '
        f'{num(a["value"], a["dec"])}{a["unit"]}' for a in al[:8]),
        "d" if any(a["status"] == "danger" for a in al) else "w")
else:
    ui.note("本期所有监控指标均处于阈值安全区间。", "g")

# ══════════ 趋势 + 风险 ══════════
c1, c2 = st.columns([1.4, 1])
with c1:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=years, y=model["revenue"], name="营业收入",
                         marker_color=C["primary"]), secondary_y=False)
    fig.add_trace(go.Scatter(x=years, y=model["net_profit"], name="净利润",
                             mode="lines+markers", line=dict(color=C["bad"], width=2.4)),
                  secondary_y=True)
    fig.add_trace(go.Scatter(x=years, y=model["ocf"], name="经营现金流",
                             mode="lines+markers",
                             line=dict(color=C["good"], width=2, dash="dot")), secondary_y=True)
    fig.update_yaxes(title_text="收入（亿元）", secondary_y=False)
    fig.update_yaxes(title_text="利润 / 现金流（亿元）", secondary_y=True)
    ui.show(fig, 290, "收入、净利润与经营现金流")
with c2:
    r1, r2 = st.columns(2)
    with r1:
        st.markdown(ui.score_gauge(rs["total"] or 0, "综合风险分"), unsafe_allow_html=True)
    with r2:
        for name, d in rs["dims"].items():
            st.markdown(ui.gauge_bar(name, d["score"] or 0, 100, fmt="{:.0f}"),
                        unsafe_allow_html=True)

# ══════════ 五步主线导航 ══════════
ui.section("分析主线", "点任一步进入，五步串成完整分析闭环")
nav = [
    ("① 经营诊断", "pages/1_经营诊断.py", "现在怎么样", "五维体检 · 杜邦归因 · 行业对标"),
    ("② 业财归因", "pages/2_业财归因.py", "为什么会这样", "盈利含金量 · 板块拆解 · 营运资本"),
    ("③ 财务风险", "pages/3_财务风险.py", "会出什么问题", "风险评分 · Z值 · 压力测试"),
    ("④ 预算与战略", "pages/4_预算与战略.py", "离目标多远", "利润桥 · 达成缺口 · 情景模拟"),
    ("⑤ 分析报告", "pages/5_分析报告.py", "输出成果", "一键生成 · 多格式导出"),
]
nc = st.columns(5)
for j, (name, path, q, desc) in enumerate(nav):
    with nc[j]:
        st.markdown(
            f'<div style="background:#fff;border:1px solid {C["line"]};'
            f'border-top:3px solid {C["primary"]};border-radius:7px;padding:12px 13px;'
            f'margin-bottom:8px;min-height:96px">'
            f'<div style="font-size:13.5px;font-weight:700;color:{C["navy"]}">{name}</div>'
            f'<div style="font-size:12px;color:{C["accent"]};font-weight:600;margin:3px 0">'
            f'{q}</div>'
            f'<div style="font-size:11px;color:{C["muted"]};line-height:1.5">{desc}</div>'
            f'</div>', unsafe_allow_html=True)
        if st.button("进入 →", key=f"nav_{j}", use_container_width=True):
            st.switch_page(path)

# ══════════ 数据完备度 ══════════
flags = available_flags()
missing = [k for k, v in flags.items() if not v]
if missing:
    ui.note("以下数据未提供，相关分析自动降级：<b>" + "、".join(missing) +
            "</b>。可在「数据导入 → 补充经营数据」补充。", "w")
