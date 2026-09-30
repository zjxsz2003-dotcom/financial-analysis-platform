"""
④ 预算与战略 —— 离目标多远、怎么补？
预算偏差归因 · 滚动预测 · 战略进度 · 情景模拟 · 盈亏平衡
"""
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from utils.shell import init
from utils import ui
from utils import tables as T
from modules import finance_core as fc
from modules import budget_analysis as ba
from modules import strategy as stg
from modules import page_summary as ps
from modules.data_loader import get_company_name, get_years, get_budget, set_budget, get_strategy, set_strategy
from config import C, STATUS_COLOR

init("预算与战略", "🎯", step=4)

model = fc.build_model()
years = get_years()
company = get_company_name()
budget = get_budget()

ui.page_head(f"{company}　④ 预算与战略",
             "回答「离目标多远、怎么补」—— 偏差归因 · 达成缺口 · 情景模拟 · 盈亏平衡")

if not budget:
    ui.note("数据不足，无法生成参考预算（至少需要 2 个报告期）。", "d")
    st.stop()

bv = ba.budget_vs_actual(model, budget)
pb = ba.profit_bridge(model, bv)

# ══════════ 核心结论 ══════════
targets = get_strategy(model)
if "strategy_cache" not in st.session_state:
    set_strategy(targets)
tp = st.slider("时间进度基准(%)", 10, 100, 50, 5, help="用于判断目标进度是否跟上时间")
prog = stg.progress(targets, float(tp))
try:
    h, bl, tone = ps.summary_strategy(prog, fc.operating_leverage(model), model)
    ui.exec_summary(h, bl, tone, title="核心结论")
except Exception as e:
    st.caption(f"（结论生成跳过：{e}）")

tab1, tab2, tab3 = st.tabs(["预算执行与归因", "目标进度与情景", "改善措施"])

# ══════════ TAB 1：预算 ══════════
with tab1:
    rev = bv["收入"].get("合计", {})
    npi = bv["利润"].get("净利润", {})
    cost_b = sum(v["预算"] for v in bv["成本"].values() if v["预算"] is not None)
    cost_a = sum(v["实际"] for v in bv["成本"].values() if v["实际"] is not None)
    fee_b = sum(v["预算"] for v in bv["费用"].values() if v["预算"] is not None)
    fee_a = sum(v["实际"] for v in bv["费用"].values() if v["实际"] is not None)
    ui.kpi_row([
        {"label": "收入完成率", "value": T.pct(rev.get("完成率"), 1),
         "delta": T.delta(rev.get("偏差率"), 1, "%"),
         "color": C["good"] if (rev.get("偏差率") or 0) >= 0 else C["bad"],
         "note": f"{T.num(rev.get('预算'),0)} → {T.num(rev.get('实际'),0)} 亿"},
        {"label": "成本执行", "value": T.pct((cost_a / cost_b * 100) if cost_b else None, 1),
         "delta": T.delta((cost_a - cost_b) / cost_b * 100 if cost_b else None, 1, "%"),
         "color": C["bad"] if (cost_a or 0) > (cost_b or 0) else C["good"],
         "note": "越低越好"},
        {"label": "费用执行", "value": T.pct((fee_a / fee_b * 100) if fee_b else None, 1),
         "delta": T.delta((fee_a - fee_b) / fee_b * 100 if fee_b else None, 1, "%"),
         "color": C["bad"] if (fee_a or 0) > (fee_b or 0) else C["good"], "note": "越低越好"},
        {"label": "净利润达成", "value": T.pct(npi.get("完成率"), 1),
         "delta": T.delta(npi.get("偏差率"), 1, "%"),
         "color": C["good"] if (npi.get("偏差率") or 0) >= 0 else C["bad"],
         "note": f"{T.num(npi.get('预算'),0)} → {T.num(npi.get('实际'),0)} 亿"},
    ])

    with st.expander("⚙️ 预算目标（可编辑）", expanded=False):
        asm = budget.get("_assumption", {})
        if asm:
            st.markdown(T.fin_table(["假设项", "取值"],
                                    [{"c": [k, T.pct(v, 1)], "t": "normal", "i": 0}
                                     for k, v in asm.items()]), unsafe_allow_html=True)
        ui.note("参考预算 = 上一期实际 × (1 + 历史增速中位数)，不使用当期数据，避免前视偏差。")
        cols = st.columns(4)
        for j, (k, v) in enumerate(budget.get("收入预算", {}).items()):
            if k == "合计":
                continue
            with cols[j % 4]:
                budget["收入预算"][k] = st.number_input(f"收入·{k}", value=float(v or 0),
                                                        step=10.0, key=f"bg_r_{k}")
        budget["收入预算"]["合计"] = round(sum(v for k, v in budget["收入预算"].items()
                                              if k != "合计"), 2)
        cols2 = st.columns(len(budget.get("费用预算", {})))
        for j, (k, v) in enumerate(budget.get("费用预算", {}).items()):
            with cols2[j]:
                budget["费用预算"][k] = st.number_input(f"费用·{k}", value=float(v or 0),
                                                        step=5.0, key=f"bg_f_{k}")
        cols3 = st.columns(2)
        for j, (k, v) in enumerate(budget.get("利润预算", {}).items()):
            with cols3[j]:
                budget["利润预算"][k] = st.number_input(f"{k}", value=float(v or 0),
                                                        step=5.0, key=f"bg_p_{k}")
        if st.button("💾 保存并重算"):
            set_budget(budget)
            st.rerun()

    if pb:
        ui.section("净利润偏差桥")
        st.plotly_chart(ba.profit_bridge_chart(pb, 300), use_container_width=True,
                        config={"displaylogo": False})
        items = [("收入规模", pb["vol"], "按预算毛利率承接收入增减"),
                 ("毛利率", pb["margin"], f"{T.pct(pb['gm_b'],2)} → {T.pct(pb['gm_a'],2)}"),
                 ("期间费用", pb["fee"], "超支为负、节余为正"),
                 ("税项及其他", pb["other"], "所得税、营业外、投资收益等")]
        main = max(items, key=lambda x: abs(x[1]))
        kind_map = {"收入规模": "销量 / 订单预测偏差", "毛利率": "定价与单位成本",
                    "期间费用": "费用管控", "税项及其他": "税负与非经常项"}
        st.markdown(T.fin_table(["归因项", "对净利润影响", "口径"],
                                [{"c": [n, (T.delta(v, 1, " 亿"), "pos" if v >= 0 else "neg"), d],
                                  "t": "sub" if n == main[0] else "normal", "i": 0}
                                 for n, v, d in items] +
                                [{"c": ["合计", (T.delta(pb["total"], 1, " 亿"),
                                                "pos" if pb["total"] >= 0 else "neg"),
                                        f"{T.num(pb['steps'][0]['value'],1)} → "
                                        f"{T.num(pb['steps'][-1]['value'],1)} 亿"],
                                  "t": "tot", "i": 0}]),
                    unsafe_allow_html=True)
        ui.note(f"偏差主因是 <b>{main[0]}效应</b>（{T.delta(main[1])} 亿元），"
                f"指向的是<b>{kind_map[main[0]]}</b>问题。")

    gdf = ba.gross_profit_variance(model, bv)
    if gdf is not None and not gdf.empty:
        ui.section("毛利偏差：卖得少还是卖得便宜")
        grows = [{"c": [r["板块"], T.num(r["预算收入"], 1), T.num(r["实际收入"], 1),
                        T.pct(r["预算毛利率(%)"], 2), T.pct(r["实际毛利率(%)"], 2),
                        (T.delta(r["规模效应(亿元)"], 1, " 亿"),
                         "pos" if r["规模效应(亿元)"] >= 0 else "neg"),
                        (T.delta(r["毛利率效应(亿元)"], 1, " 亿"),
                         "pos" if r["毛利率效应(亿元)"] >= 0 else "neg"), r["主因"]],
                  "t": "normal", "i": 0} for _, r in gdf.iterrows()]
        grows.append({"c": ["合计", T.num(gdf["预算收入"].sum(), 1), T.num(gdf["实际收入"].sum(), 1),
                            "", "", T.delta(gdf["规模效应(亿元)"].sum(), 1, " 亿"),
                            T.delta(gdf["毛利率效应(亿元)"].sum(), 1, " 亿"), ""],
                      "t": "tot", "i": 0})
        st.markdown(T.fin_table(["板块", "预算收入", "实际收入", "预算毛利率", "实际毛利率",
                                 "规模效应(亿)", "毛利率效应(亿)", "主因"], grows),
                    unsafe_allow_html=True)

    ui.section("滚动预测与达成缺口")
    c1, c2, c3 = st.columns([1, 1, 1.4])
    with c1:
        months = st.slider("已过去月数", 1, 12, 6, 1)
    with c2:
        season = st.selectbox("季节性", list(ba.SEASONALITY.keys()), index=0)
    with c3:
        ytd_rev = st.number_input("年初至今收入（亿元，留空按季节权重估算）",
                                  min_value=0.0, value=0.0, step=10.0)
    rf = ba.rolling_forecast(model, bv, months=months,
                             ytd_revenue=ytd_rev if ytd_rev else None, season=season)
    st.markdown(T.fin_table(["项目", "数值", "说明"], [
        {"c": ["全年预测收入", T.num(rf["fc_revenue"], 1), "亿元"], "t": "sub", "i": 0},
        {"c": ["收入预算", T.num(rf["budget_revenue"], 1), "亿元"], "t": "normal", "i": 0},
        {"c": ["达成缺口", (T.delta(-rf["gap_revenue"], 1, " 亿") if rf["gap_revenue"] is not None else "—",
                           "neg" if (rf["gap_revenue"] or 0) > 0 else "pos"), "亿元"], "t": "tot", "i": 0},
        {"c": ["进度完成率", T.pct(rf["complete_rate"], 1), f"时间进度 {T.pct(rf['time_rate'],1)}"],
         "t": "normal", "i": 0},
        {"c": ["剩余月均所需", T.num(rf["need_monthly"], 1), f"当前月均 {T.num(rf['cur_monthly'],1)} 亿"],
         "t": "normal", "i": 0},
    ]), unsafe_allow_html=True)
    if rf["speedup"] is not None:
        if rf["speedup"] <= 0:
            ui.note(f"按当前进度外推全年 {T.num(rf['fc_revenue'],1)} 亿元，已<b>超过</b>预算 "
                    f"{T.delta(-rf['gap_revenue'],1,' 亿')}，无需提速，可考虑上调目标。", "g")
        else:
            ui.note(f"剩余 {rf['remain_months']} 个月月均需从 {T.num(rf['cur_monthly'],1)} 亿提升至 "
                    f"<b>{T.num(rf['need_monthly'],1)} 亿</b>（提速 {T.pct(rf['speedup'],1)}）。",
                    "d" if rf["speedup"] > 20 else ("w" if rf["speedup"] > 5 else "g"))

# ══════════ TAB 2：战略与情景 ══════════
with tab2:
    with st.expander("⚙️ 战略目标（可编辑）", expanded=False):
        ui.note("默认目标由历史最优值与行业基准推导，可逐项改写。")
        for j, t in enumerate(targets):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            with c1:
                t["name"] = st.text_input("名称", value=t["name"], key=f"st_n_{j}")
            with c2:
                t["unit"] = st.text_input("单位", value=t.get("unit", ""), key=f"st_u_{j}")
            with c3:
                t["target_value"] = st.number_input("目标", value=float(t.get("target_value") or 0),
                                                    step=0.1, key=f"st_t_{j}")
            with c4:
                t["current_value"] = st.number_input("当前", value=float(t.get("current_value") or 0),
                                                     step=0.1, key=f"st_c_{j}")
            t["lower_better"] = st.checkbox("越低越好", value=t.get("lower_better", False),
                                            key=f"st_l_{j}")
        if st.button("💾 保存目标", use_container_width=True):
            set_strategy(targets)
            st.rerun()

    if prog:
        st.plotly_chart(stg.progress_chart(prog, float(tp)), use_container_width=True,
                        config={"displaylogo": False})
    for t in prog:
        stt = t["status"]
        col = STATUS_COLOR.get(stt, C["muted"])
        lbl = {"normal": "进度正常", "warning": "略落后", "danger": "严重落后", "na": "数据不足"}.get(stt)
        st.markdown(
            f'<div class="insight" style="border-left-color:{col}">'
            f'<span class="hd">{t["name"]}</span>'
            f'<div class="ln">当前 <b>{T.num(t["current_value"],2)}{t.get("unit","")}</b>　'
            f'目标 <b>{T.num(t["target_value"],2)}{t.get("unit","")}</b>　'
            f'完成率 <b style="color:{col}">{T.pct(t["progress"],1)}</b>　'
            f'<span class="bdg {"bdg-n" if stt=="normal" else ("bdg-w" if stt=="warning" else "bdg-d")}">'
            f'{lbl}</span></div></div>', unsafe_allow_html=True)
        tree = t.get("kpi_tree", {})
        if tree:
            df = stg.kpi_tree_gap(t)
            with st.expander(f"　▸ KPI 分解树 · {t['name'][:16]}"):
                st.markdown(T.fin_table(
                    ["子指标", "权重", "当前", "目标", "完成率", "加权缺口贡献"],
                    [{"c": [r["子指标"], f"{r['权重']:.0%}", T.num(r["当前"], 2),
                            T.num(r["目标"], 2), T.pct(r["子目标完成率(%)"], 1),
                            T.num(r["加权缺口贡献"], 3)],
                      "t": "sub" if r["状态"] == "danger" else "normal", "i": 0}
                     for _, r in df.iterrows()]), unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:12.5px;color:{C["text2"]};margin:0 0 10px;'
                    f'line-height:1.7">💡 <b>缺口反推：</b>{stg.gap_actions(model, t)}</div>',
                    unsafe_allow_html=True)

    ui.section("What-if 情景模拟")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        w_rev = st.number_input("收入变动(%)", -30.0, 40.0, 0.0, 1.0, key="wi_rev")
    with c2:
        w_gm = st.number_input("毛利率(pp)", -6.0, 6.0, 0.0, 0.5, key="wi_gm")
    with c3:
        w_fee = st.number_input("费用率(pp)", -3.0, 3.0, 0.0, 0.25, key="wi_fee")
    with c4:
        w_dso = st.number_input("DSO(天)", -40.0, 60.0, 0.0, 5.0, key="wi_dso")
    with c5:
        w_debt = st.number_input("有息负债(亿)", -200.0, 300.0, 0.0, 10.0, key="wi_debt")
    res = stg.what_if(model, d_rev=w_rev, d_gm=w_gm, d_fee_rate=w_fee,
                      d_dso=w_dso, d_debt=w_debt)
    wrows = []
    for _, r in stg.what_if_rows(res).iterrows():
        good = r["指标"] in ("营业收入", "毛利率(%)", "EBIT", "净利润", "ROE(%)",
                             "利息保障倍数", "自由现金流", "现金")
        cls = "" if r["变动"] is None else ("pos" if (good and r["变动"] >= 0) or
                                                      (not good and r["变动"] <= 0) else "neg")
        wrows.append({"c": [r["指标"], T.num(r["基准"], 2), T.num(r["模拟情景"], 2),
                            (T.delta(r["变动"], 2), cls)],
                      "t": "sub" if r["指标"] in ("净利润", "ROE(%)") else "normal", "i": 0})
    st.markdown(T.fin_table(["指标", "基准", "模拟情景", "变动"], wrows), unsafe_allow_html=True)

    ol = fc.operating_leverage(model)
    if ol.get("ok"):
        ui.section("本量利与盈亏平衡")
        c1, c2 = st.columns([1.2, 1])
        with c1:
            st.markdown(T.fin_table(["指标", "数值", "说明"], [
                {"c": ["边际贡献率", T.pct(ol["cmr"], 2), "每 1 元收入的边际贡献"], "t": "normal", "i": 0},
                {"c": ["固定成本（估算）", T.num(ol["fixed"], 1), "亿元/年"], "t": "normal", "i": 0},
                {"c": ["盈亏平衡收入", T.num(ol["bep"], 1) if ol["bep"] else "—", "亿元"], "t": "sub", "i": 0},
                {"c": ["当前收入", T.num(ol["cur_rev"], 1), "亿元"], "t": "normal", "i": 0},
                {"c": ["安全边际率", T.pct(ol["safety"], 1) if ol["bep"] else "—", "缓冲空间"], "t": "normal", "i": 0},
                {"c": ["经营杠杆 DOL", T.num(ol["dol"], 2), "收入 1% → EBIT 变动"], "t": "normal", "i": 0},
                {"c": ["总杠杆 DTL", T.num(ol["dtl"], 2), "DOL × DFL"], "t": "tot", "i": 0},
            ]), unsafe_allow_html=True)
        with c2:
            if ol["bep"]:
                xs = list(np.linspace(0, max(ol["cur_rev"] * 1.25, ol["bep"] * 1.3), 60))
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=xs, y=xs, name="营业收入",
                                         line=dict(color=C["primary"], width=2)))
                fig.add_trace(go.Scatter(x=xs, y=[ol["fixed"]] * len(xs), name="固定成本",
                                         line=dict(color=C["warn"], width=1.8, dash="dash")))
                fig.add_trace(go.Scatter(x=xs, y=[ol["fixed"] + x * (1 - ol["cmr"] / 100) for x in xs],
                                         name="总成本", line=dict(color=C["bad"], width=2)))
                fig.add_vline(x=ol["bep"], line_dash="dot", line_color=C["good"],
                              annotation_text=f"盈亏平衡 {ol['bep']:,.0f}",
                              annotation_font=dict(size=10))
                fig.update_xaxes(title_text="营业收入（亿元）")
                fig.update_yaxes(title_text="金额（亿元）")
                ui.show(fig, 280, "盈亏平衡图")
        ui.insight("杠杆与盈亏平衡", [
            ("What", f"边际贡献率 {T.pct(ol['cmr'],2)}，固定成本约 {T.num(ol['fixed'],1)} 亿元，"
                     + (f"盈亏平衡收入 {T.num(ol['bep'],1)} 亿元，安全边际 {T.pct(ol['safety'],1)}。"
                        if ol["bep"] else "当前固定成本为负，盈亏平衡点不适用。")),
            ("SoWhat", "安全边际偏低意味着收入小幅下滑即可能逼近盈亏平衡；总杠杆越高，"
                       "业绩波动被放大的幅度越大。"),
            ("NowWhat", "① 提高变动成本占比降低固定成本刚性；② 下行期优先保边际贡献为正的产品线；"
                        "③ 用盈亏平衡点作为产能扩张的规模门槛。"),
        ])

# ══════════ TAB 3：改善措施 ══════════
with tab3:
    ui.section("可量化的改善抓手")
    acts = ba.action_quantification(model)
    arows = []
    for a in acts:
        arows.append({"c": [a["措施"], a["口径"],
                            (T.delta(a["影响净利润(亿元)"], 2, " 亿"), "pos"),
                            a["难度"], a["周期"], a["说明"]], "t": "normal", "i": 0})
    st.markdown(T.fin_table(["措施", "测算口径", "影响净利润", "难度", "周期", "说明"], arows),
                unsafe_allow_html=True)
    slack = ba.budget_slack_check(bv)
    if slack.get("ok"):
        ui.note(f"<b>预算松弛度：</b>{slack['text']}（平均完成率 {T.pct(slack['avg'],1)}）",
                {"normal": "g", "warning": "w", "danger": "d"}.get(slack["level"], ""))

ui.drill_bar([
    {"label": "⑤ 生成分析报告", "target": "pages/5_分析报告.py",
     "context": {"from": "预算与战略", "focus": "输出"}},
    {"label": "② 业财归因", "target": "pages/2_业财归因.py",
     "context": {"from": "预算与战略", "focus": "偏差根因"}},
], label="下一步")
