"""
③ 财务风险 —— 会出什么问题？
六维风险评分 · Altman Z · 流动性阶梯 · 压力测试 · 风险传导链
"""
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from utils.shell import init
from utils import ui
from utils import tables as T
from modules import finance_core as fc
from modules import risk_analysis as ra
from modules.kpi import snapshot
from modules import page_summary as ps
from modules import business_context as bc
from modules.data_loader import get_company_name, get_years
from config import C, STATUS_COLOR

init("财务风险", "⚠️", step=3)

model = fc.build_model()
snap = snapshot(model)
years = get_years()
company = get_company_name()

ui.page_head(f"{company}　③ 财务风险",
             "回答「会出什么问题」—— 风险打分 · 破产判别 · 承压测算 · 整改清单")

rs = ra.risk_scorecard(model)
lv, stt = ra.risk_level(rs["total"])
az = ra.altman_detail(model)
lp = ra.liquidity_profile(model)

# ══════════ 核心结论 ══════════
try:
    h, bl, tone = ps.summary_risk(model, rs, az, lp)
    ui.exec_summary(h, bl, tone, title="核心结论")
    bc.render_brief(model)
except Exception as e:
    st.caption(f"（结论生成跳过：{e}）")

# ══════════ 评分卡 ══════════
ui.section("六维风险评分", "0 = 低风险，100 = 高风险")
c1, c2, c3 = st.columns([0.75, 1.5, 1.5])
with c1:
    st.markdown(ui.score_gauge(rs["total"] or 0, "综合风险分"), unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:12px;color:{C["muted"]};text-align:center;'
                f'margin-top:4px">评级：<b style="color:{STATUS_COLOR[stt]}">{lv}</b></div>',
                unsafe_allow_html=True)
with c2:
    for name, d in rs["dims"].items():
        st.markdown(ui.gauge_bar(name, d["score"] or 0, 100, fmt="{:.0f}"),
                    unsafe_allow_html=True)
with c3:
    st.plotly_chart(ra.radar_chart(rs, 300), use_container_width=True,
                    config={"displaylogo": False})

with st.expander("▸ 评分明细（各维度子指标）", expanded=False):
    for name, d in rs["dims"].items():
        st.markdown(f"**{name}　{T.num(d['score'],0)} 分**")
        rows = [{"c": [n, T.num(s, 0), f"{w:.0%}", T.num(v, 2), unit],
                 "t": "normal", "i": 0} for n, s, w, v, unit in d["items"]]
        st.markdown(T.fin_table(["子指标", "风险分", "权重", "当前值", "单位"], rows),
                    unsafe_allow_html=True)

# ══════════ Z 值 + 流动性 ══════════
ui.section("破产判别与流动性")
c1, c2 = st.columns(2)
with c1:
    if az:
        zrows = [
            {"c": ["X1 营运资本/总资产", T.pct(az["x1"], 2), "1.2"], "t": "normal", "i": 0},
            {"c": ["X2 留存收益/总资产", T.pct(az["x2"], 2), "1.4"], "t": "normal", "i": 0},
            {"c": ["X3 EBIT/总资产", T.pct(az["x3"], 2), "3.3"], "t": "normal", "i": 0},
            {"c": ["X4 权益/总负债", T.num(az["x4"], 2), "0.6"], "t": "normal", "i": 0},
            {"c": ["X5 收入/总资产", T.num(az["x5"], 2), "1.0"], "t": "normal", "i": 0},
            {"c": ["Z（上市制造口径）", T.num(az["z"], 2), az["zone"][0]], "t": "tot", "i": 0},
            {"c": ["Z′（私营企业口径）", T.num(az["zp"], 2), az["zone_p"][0]], "t": "sub", "i": 0},
        ]
        st.markdown(T.fin_table(["因子", "取值", "判别/权重"], zrows), unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=years, y=az["series"]["z"], name="Z",
                                 mode="lines+markers", line=dict(color=C["primary"], width=2.4)))
        fig.add_hline(y=2.99, line_dash="dash", line_color=C["good"],
                      annotation_text="安全 2.99", annotation_font=dict(size=10))
        fig.add_hline(y=1.81, line_dash="dash", line_color=C["bad"],
                      annotation_text="困境 1.81", annotation_font=dict(size=10))
        ui.show(fig, 250, "Z-Score 趋势")
    else:
        ui.note("缺少必要科目，无法计算 Z 值。", "w")
with c2:
    lrows = [
        {"c": ["货币资金", T.num(lp["cash"], 1), "即时可用"], "t": "normal", "i": 0},
        {"c": ["短期有息负债", T.num(lp["short_total"], 1), "一年内到期"], "t": "normal", "i": 0},
        {"c": ["长期有息负债", T.num(lp["long_total"], 1), "期限较长"], "t": "normal", "i": 0},
        {"c": ["有息负债合计", T.num(lp["ibd"], 1), f"短债占比 {T.pct(lp['short_share'],1)}"],
         "t": "sub", "i": 0},
        {"c": ["现金 / 短期有息负债", T.num(lp["cover_short"], 2), "≥1.5 为安全"],
         "t": "normal", "i": 0},
        {"c": ["（现金+经营现金流）/短债", T.num(lp["cover_with_ocf"], 2), "含年度造血能力"],
         "t": "normal", "i": 0},
        {"c": ["自由现金流覆盖短债年数", T.num(lp["years_to_repay"], 1), "FCF 为正时的年限"],
         "t": "tot", "i": 0},
    ]
    st.markdown(T.fin_table(["项目", "金额(亿)/倍数", "说明"], lrows), unsafe_allow_html=True)
    cw = ra.cash_waterfall(model)
    if cw:
        fig = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "total"],
            x=["经营现金流", "资本开支", "利息支出", "筹资净额", "现金净变动"],
            y=[cw["ocf"], -cw["capex"], -(cw["interest"] or 0), cw["fin"], cw["net"]],
            text=[T.num(v, 1) for v in [cw["ocf"], -cw["capex"], -(cw["interest"] or 0),
                                        cw["fin"], cw["net"]]],
            textposition="outside", textfont=dict(size=10),
            connector=dict(line=dict(color=C["line"])),
            increasing=dict(marker=dict(color=C["accent"])),
            decreasing=dict(marker=dict(color=C["bad"])),
            totals=dict(marker=dict(color=C["primary"]))))
        ui.show(fig, 250, "现金流覆盖阶梯（亿元）")

# ══════════ 压力测试 ══════════
ui.section("压力测试", "收入 / 毛利率 / 回款 / 融资成本同时承压")
preset = st.selectbox("情景", list(ra.PRESET_SCENARIOS.keys()), index=1)
p = ra.PRESET_SCENARIOS[preset]
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    d_rev = st.number_input("收入变动(%)", -50.0, 50.0, float(p.get("d_rev", 0)), 1.0)
with c2:
    d_gm = st.number_input("毛利率变动(pp)", -10.0, 10.0, float(p.get("d_gm", 0)), 0.5)
with c3:
    d_dso = st.number_input("DSO+天数", -60.0, 90.0, float(p.get("d_dso", 0)), 5.0)
with c4:
    d_dio = st.number_input("DIO+天数", -60.0, 90.0, float(p.get("d_dio", 0)), 5.0)
with c5:
    d_bp = st.number_input("利率+BP", -200.0, 400.0, float(p.get("d_rate_bp", 0)), 25.0)

res = ra.stress_test(model, d_rev=d_rev, d_gm=d_gm, d_dso=d_dso, d_dio=d_dio, d_rate_bp=d_bp)
good_keys = ("营业收入", "毛利率(%)", "EBIT", "净利润", "ROE(%)", "利息保障倍数", "自由现金流")
srows = []
for _, r in res["rows"].iterrows():
    cls = "" if r["变动"] is None else (
        "pos" if (r["指标"] in good_keys and r["变动"] >= 0) or
                 (r["指标"] not in good_keys and r["变动"] <= 0) else "neg")
    srows.append({"c": [r["指标"], T.num(r["基准"], 2), T.num(r["压力情景"], 2),
                        (T.delta(r["变动"], 2), cls),
                        (T.delta(r["变动率(%)"], 1, "%") if r["变动率(%)"] is not None else "—", cls)],
                  "t": "sub" if r["指标"] in ("净利润", "ROE(%)") else "normal", "i": 0})
st.markdown(T.fin_table(["指标", "基准", "压力情景", "变动", "变动率"], srows),
            unsafe_allow_html=True)

sc = ra.scenario_compare(model)
if not sc.empty:
    crows = [{"c": [r["情景"], T.delta(r["收入变动(%)"], 0, "%"),
                    T.delta(r["毛利率变动(pp)"], 1, " pp"),
                    T.num(r["压力后净利润(亿元)"], 1),
                    (T.delta(r["较基准变动(亿元)"], 1, " 亿"),
                     "pos" if r["较基准变动(亿元)"] >= 0 else "neg"),
                    T.pct(r["压力后ROE(%)"], 2), T.num(r["压力后利息保障倍数"], 2)],
              "t": "normal", "i": 0} for _, r in sc.iterrows()]
    st.markdown(T.fin_table(["情景", "收入", "毛利率", "压力后净利(亿)",
                             "较基准", "ROE", "利息保障"], crows), unsafe_allow_html=True)
    worst = sc.loc[sc["较基准变动(亿元)"].idxmin()]
    ui.insight("压力测试结论", [
        ("What", f"「{worst['情景']}」下净利润 {T.num(worst['压力后净利润(亿元)'],1)} 亿元"
                 f"（{T.delta(worst['较基准变动(亿元)'])} 亿元），ROE {T.pct(worst['压力后ROE(%)'],2)}。"),
        ("SoWhat", "若压力情景下利息保障倍数跌破 1.5 或自由现金流转负，"
                   "公司将同时面临盈利下滑与现金紧张的双重压力。"),
        ("NowWhat", "① 设定压力情景触发线并配套应急预案；② 提前锁定备用授信；"
                    "③ 提高变动成本占比，让利润随收入自动调节。"),
    ], kind="d")

# ══════════ 传导链 ══════════
ui.section("风险传导链", "预警指标 → 业务根因 → 财务后果 → 管理动作")
tr = ra.transmission_rows(snap)
if tr.empty:
    ui.note("本期无预警指标。", "g")
else:
    trows = []
    for _, r in tr.iterrows():
        trows.append({"c": [r["指标"], f"{T.num(r['当前值'], 2)}{r['单位']}",
                            ("预警" if r["状态"] == "danger" else "关注",
                             "neg" if r["状态"] == "danger" else ""),
                            r["业务根因"], r["管理动作"]],
                      "t": "sub" if r["状态"] == "danger" else "normal", "i": 0})
    st.markdown(T.fin_table(["预警指标", "当前值", "级别", "业务根因", "管理动作"], trows),
                unsafe_allow_html=True)
    st.download_button("⇩ 导出整改清单", data=tr.to_csv(index=False).encode("utf-8-sig"),
                       file_name="风险传导清单.csv", mime="text/csv")

ui.drill_bar([
    {"label": "④ 预算与战略：怎么补", "target": "pages/4_预算与战略.py",
     "context": {"from": "财务风险", "focus": "风险应对"}},
    {"label": "⑤ 生成分析报告", "target": "pages/5_分析报告.py",
     "context": {"from": "财务风险", "focus": "风险章节"}},
], label="下一步")
