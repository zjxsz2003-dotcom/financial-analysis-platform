"""
② 业财归因 —— 为什么会这样？
把「比率变化」拆到业务：盈利含金量 · 板块结构 · 成本费用 · 营运资本
"""
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from utils.shell import init
from utils import ui
from utils import tables as T
from modules import finance_core as fc
from modules import business_deep as bd
from modules import page_summary as ps
from modules import business_context as bc
from modules.data_loader import get_company_name, get_years
from config import C

init("业财归因", "🔬", step=2)

model = fc.build_model()
years = get_years()
company = get_company_name()
L = lambda k: fc._last(model.get(k, []))
P = lambda k: fc._prev(model.get(k, []))

ui.page_head(f"{company}　② 业财归因",
             "回答「为什么会这样」—— 利润含金量 · 板块与毛利率拆解 · 成本费用 · 营运资本")

# ══════════ 核心结论 ══════════
try:
    h, bl, tone = ps.summary_earnings(model, None)
    ui.exec_summary(h, bl, tone, title="核心结论")
    bc.render_brief(model)
except Exception as e:
    st.caption(f"（结论生成跳过：{e}）")

# ══════════ 盈利含金量 ══════════
ui.section("利润是真的吗", "净利润 → 经营现金流 → 自由现金流")
eq = fc.earnings_quality_score(model)
cb = fc.cash_bridge(model)
c1, c2 = st.columns([0.75, 1.6])
with c1:
    col = C["good"] if (eq["score"] or 0) >= 70 else (
        C["warn"] if (eq["score"] or 0) >= 50 else C["bad"])
    st.markdown(f'<div class="risk-card" style="border-top:3px solid {col}">'
                f'<div style="font-size:11px;color:{C["muted"]}">盈利质量得分</div>'
                f'<div style="font-size:34px;font-weight:700;color:{col}">'
                f'{T.num(eq["score"],0)}</div>'
                f'<div style="font-size:11px;color:{C["muted"]}">满分 100</div></div>',
                unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    for r in eq["items"]:
        st.markdown(ui.gauge_bar(r["维度"], r["得分"] or 0, 100, fmt="{:.0f}"),
                    unsafe_allow_html=True)
with c2:
    steps = ["净利润", "折旧摊销", "营运资本变动", "经营现金流", "资本开支", "自由现金流"]
    vals = [cb["净利润"], cb["折旧摊销"], cb["营运资本变动"],
            cb["经营现金流"], (cb["资本开支"] and -cb["资本开支"]), cb["自由现金流"]]
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "total", "relative", "total"],
        x=steps, y=vals, text=[T.num(v, 1) for v in vals],
        textposition="outside", textfont=dict(size=10),
        connector=dict(line=dict(color=C["line"])),
        increasing=dict(marker=dict(color=C["accent"])),
        decreasing=dict(marker=dict(color=C["bad"])),
        totals=dict(marker=dict(color=C["primary"]))))
    ui.show(fig, 300, f"净利润 → 自由现金流 桥（{cb['year']} 年，亿元）")

# ══════════ 板块与毛利率拆解 ══════════
ui.section("收入结构与毛利率拆解")
so = bd.segment_overview(model)
if not so:
    ui.note("未上传分部数据，板块级归因不可用。可在「数据导入 → 补充经营数据」补充后自动启用。", "w")
else:
    df = so["df"]
    c1, c2 = st.columns([1.3, 1])
    with c1:
        rows = []
        for _, r in df.iterrows():
            rows.append({"c": [r["板块"], T.num(r["收入"], 1),
                               (T.delta(r["增速"], 1, "%"), "pos" if (r["增速"] or 0) >= 0 else "neg"),
                               T.pct(r["收入占比"], 1), T.pct(r["毛利率"], 2),
                               (T.delta(r["毛利率变动"], 2, " pp") if r["毛利率变动"] is not None else "—",
                                "pos" if (r["毛利率变动"] or 0) >= 0 else "neg"),
                               T.num(r["毛利"], 1)], "t": "normal", "i": 0})
        rows.append({"c": ["合计", T.num(df["收入"].sum(), 1),
                           (T.delta((df['收入'].sum()/df['收入_上期'].sum()-1)*100
                                    if df["收入_上期"].sum() else None, 1, "%"), ""),
                           "100.0%", T.pct(so["weighted_margin"], 2), "",
                           T.num(df["毛利"].sum(), 1)], "t": "tot", "i": 0})
        st.markdown(T.fin_table(["板块", "收入(亿)", "同比", "占比",
                                 "毛利率", "毛利率变动", "毛利(亿)"], rows),
                    unsafe_allow_html=True)
    with c2:
        fig = go.Figure()
        for j, r in df.iterrows():
            fig.add_trace(go.Bar(name=r["板块"], x=["收入"], y=[r["收入"]],
                                 marker_color=C["chart"][j % len(C["chart"])]))
        fig.update_layout(barmode="stack")
        ui.show(fig, 240, "板块收入构成（亿元）")

    mb = fc.margin_bridge(model)
    if mb:
        st.markdown("**毛利率变动两因素分解**（结构效应 × 毛利率效应，无残差）")
        c1, c2 = st.columns([1, 1.2])
        with c1:
            st.markdown(T.fin_table(
                ["分解项", "贡献", "含义"],
                [{"c": ["结构效应", T.delta(mb["mix"], 2, " pp"),
                        "高/低毛利板块占比变化"], "t": "normal", "i": 0},
                 {"c": ["毛利率效应", T.delta(mb["price"], 2, " pp"),
                        "各板块售价与成本变化"], "t": "normal", "i": 0},
                 {"c": ["交叉效应", T.delta(mb["cross"], 2, " pp"), "两项同时变动"],
                  "t": "normal", "i": 0},
                 {"c": ["合计", T.delta(mb["total"], 2, " pp"),
                        f"{mb['year0']}→{mb['year1']}"], "t": "tot", "i": 0}]),
                unsafe_allow_html=True)
        with c2:
            dd = mb["detail"]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=dd["板块"], y=dd["结构贡献(pp)"], name="结构效应",
                                 marker_color=C["primary"]))
            fig.add_trace(go.Bar(x=dd["板块"], y=dd["毛利率贡献(pp)"], name="毛利率效应",
                                 marker_color=C["accent"]))
            fig.update_layout(barmode="group")
            fig.update_yaxes(title_text="pp")
            ui.show(fig, 250, "各板块对毛利率变动贡献")
    ui.insight("板块结构结论", so["insight"])

# ══════════ 成本费用 ══════════
ui.section("成本费用弹性")
cs = bd.cost_structure(model)
c1, c2 = st.columns(2)
with c1:
    names = list(cs["items"].keys())
    vals = [cs["items"][k] for k in names]
    fig = go.Figure(go.Bar(y=names, x=vals, orientation="h", marker_color=C["primary"],
                           text=[T.num(v, 1) for v in vals], textposition="outside",
                           textfont=dict(size=10)))
    fig.update_xaxes(title_text="亿元")
    ui.show(fig, 260, "成本费用构成")
with c2:
    edf = bd.expense_efficiency(model)["df"]
    fig = go.Figure()
    for j, r in edf.iterrows():
        fig.add_trace(go.Scatter(x=years, y=model[{"销售费用": "sell_ratio", "管理费用": "admin_ratio",
                                                   "研发费用": "rd_ratio", "财务费用": "fin_ratio"}[r["科目"]]],
                                 name=r["科目"], mode="lines+markers",
                                 line=dict(width=2, color=C["chart"][j % len(C["chart"])])))
    fig.update_yaxes(title_text="占收入比(%)")
    ui.show(fig, 260, "费用率趋势")

erows = []
for k, v in cs["elastic"].items():
    if v["占收入比"] is None:
        continue
    erows.append({"c": [k, T.pct(v["占收入比"], 2),
                        (T.delta(v["增速"], 1, "%") if v["增速"] is not None else "—",
                         "pos" if (v["增速"] or 0) >= 0 else "neg"),
                        (T.num(v["弹性"], 2) if v["弹性"] is not None else "—",
                         "neg" if (v["弹性"] or 0) > 1.15 else ""),
                        ("扩张快于收入" if (v["弹性"] or 0) > 1.15 else
                         ("基本同步" if (v["弹性"] or 0) > 0.85 else "慢于收入"))],
                  "t": "normal", "i": 0})
st.markdown(T.fin_table(["科目", "占收入比", "同比", "收入弹性", "评价"], erows),
            unsafe_allow_html=True)
ui.insight("成本费用诊断", cs["insight"])

# ══════════ 营运资本 ══════════
ui.section("营运资本效率", "DSO + DIO − DPO = CCC")
wc = bd.working_capital(model)
c1, c2 = st.columns(2)
with c1:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=years, y=model["dso"], name="DSO 应收", marker_color=C["primary"]))
    fig.add_trace(go.Bar(x=years, y=model["dio"], name="DIO 存货", marker_color=C["accent"]))
    fig.add_trace(go.Bar(x=years, y=[-(v or 0) for v in model["dpo"]],
                         name="DPO 应付（负）", marker_color=C["good"]))
    fig.update_layout(barmode="relative")
    fig.update_yaxes(title_text="天")
    ui.show(fig, 260, "营运资本周转天数分解")
with c2:
    wrows = [
        {"c": ["应收周转天数 DSO", T.num(wc["dso"], 0), T.num(P("dso"), 0),
               (T.delta((wc["dso"] or 0) - (P("dso") or 0), 0, " 天"),
                "neg" if (wc["dso"] or 0) > (P("dso") or 0) else "pos")], "t": "normal", "i": 0},
        {"c": ["存货周转天数 DIO", T.num(wc["dio"], 0), T.num(P("dio"), 0),
               (T.delta((wc["dio"] or 0) - (P("dio") or 0), 0, " 天"),
                "neg" if (wc["dio"] or 0) > (P("dio") or 0) else "pos")], "t": "normal", "i": 0},
        {"c": ["应付周转天数 DPO", T.num(wc["dpo"], 0), T.num(P("dpo"), 0),
               (T.delta((wc["dpo"] or 0) - (P("dpo") or 0), 0, " 天"),
                "pos" if (wc["dpo"] or 0) > (P("dpo") or 0) else "neg")], "t": "normal", "i": 0},
        {"c": ["现金转换周期 CCC", T.num(wc["ccc"], 0), T.num(wc["ccc0"], 0),
               (T.delta((wc["ccc"] or 0) - (wc["ccc0"] or 0), 0, " 天"),
                "neg" if (wc["ccc"] or 0) > (wc["ccc0"] or 0) else "pos")], "t": "tot", "i": 0}]
    st.markdown(T.fin_table(["指标", "本期(天)", "上期(天)", "变动"], wrows),
                unsafe_allow_html=True)
    ui.insight("营运资本诊断", wc["insight"], kind="w" if (wc["ccc"] or 0) > 90 else "")

c1, c2 = st.columns(2)
with c1:
    ui.insight("应收账款质量", bd.ar_quality(model)["insight"])
with c2:
    ui.insight("存货质量", bd.inventory_quality(model)["insight"])

# ══════════ 业务视角 ══════════
ui.section("业务视角", "财务现象背后的真实业务事件")
bc.render_panel(model, show_events=True)

ui.drill_bar([
    {"label": "③ 财务风险评估", "target": "pages/3_财务风险.py",
     "context": {"from": "业财归因", "focus": "现金流与营运风险"}},
    {"label": "④ 预算与战略", "target": "pages/4_预算与战略.py",
     "context": {"from": "业财归因", "focus": "成本费用偏差"}},
], label="下一步")
