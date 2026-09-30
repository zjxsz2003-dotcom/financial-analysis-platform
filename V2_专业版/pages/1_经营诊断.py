"""
① 经营诊断 —— 公司现在怎么样？
五维指标体检 + 杜邦五因素归因 + 行业对标定位
"""
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.shell import init
from utils import ui
from utils import tables as T
from modules import finance_core as fc
from modules import industry_bench as ib
from modules.kpi import snapshot, alerts, dim_stats
from modules import page_summary as ps
from modules import business_context as bc
from modules.data_loader import get_company_name, get_years, get_industry_name
from config import C, INDUSTRY_META, BENCHMARK_DISCLAIMER

init("经营诊断", "📈", step=1)

model = fc.build_model()
snap = snapshot(model)
years = get_years()
company = get_company_name()
L = lambda k: fc._last(model.get(k, []))

ui.page_head(f"{company}　① 经营诊断",
             f"回答「公司现在怎么样」—— 五维体检 · 回报归因 · 行业定位　｜　{years[0]}–{years[-1]}")

# ══════════ 核心结论 ══════════
try:
    h, bl, tone = ps.summary_overview(model, snap)
    ui.exec_summary(h, bl, tone, title="核心结论")
except Exception as e:
    st.caption(f"（结论生成跳过：{e}）")

# ══════════ 五维体检 ══════════
ui.section("五维指标体检", "● 正常　◉ 关注　⬤ 预警")
ds = dim_stats(snap)
cols = st.columns(len(ds))
for j, d in enumerate(ds):
    with cols[j]:
        col, icon = ((C["bad"], "⬤") if d["danger"] else
                     (C["warn"], "◉") if d["warning"] else (C["good"], "●"))
        st.markdown(
            f'<div class="kpi" style="border-top-color:{col}">'
            f'<div class="l">{icon} {d["name"]}</div>'
            f'<div class="v" style="font-size:18px;color:{col}">'
            f'{d["normal"]}/{d["warning"]}/{d["danger"]}</div>'
            f'<div class="n">正常/关注/预警（{d["total"]} 项）</div></div>',
            unsafe_allow_html=True)

al = alerts(snap)
if al:
    ui.note("　".join(
        f'{"🔴" if a["status"]=="danger" else "🟡"} <b>{a["name"]}</b> '
        f'{T.num(a["value"], a["dec"])}{a["unit"]}' for a in al[:8]),
        "d" if any(a["status"] == "danger" for a in al) else "w")
else:
    ui.note("本期全部监控指标均处于阈值安全区间。", "g")

# ══════════ 杜邦归因 ══════════
ui.section("股东回报归因", "ROE = 税负负担 × 利息负担 × EBIT利润率 × 总资产周转率 × 权益乘数")
dp = fc.dupont_decompose(model, 0, model["n"] - 1)
c1, c2 = st.columns([1, 1.25])
with c1:
    dpr = []
    for _, r in fc.dupont_table(model).iterrows():
        dpr.append({"c": [f"{int(r['年份'])}年", T.num(r["ROE(%)"], 2),
                          T.num(r["税负负担率"], 3), T.num(r["利息负担率"], 3),
                          T.num(r["EBIT利润率(%)"], 2), T.num(r["总资产周转率"], 3),
                          T.num(r["权益乘数"], 2)],
                    "t": "tot" if r["年份"] == years[-1] else "normal", "i": 0})
    st.markdown(T.fin_table(["年份", "ROE(%)", "税负负担", "利息负担",
                             "EBIT利润率(%)", "周转率", "权益乘数"], dpr),
                unsafe_allow_html=True)
with c2:
    if dp:
        names = [n for n, c, a, b, d in dp] + ["ROE 合计"]
        vals = [c for n, c, a, b, d in dp]
        vals.append(sum(vals))
        fig = go.Figure(go.Waterfall(
            orientation="v", measure=["relative"] * len(dp) + ["total"],
            x=names, y=vals, text=[f"{v:+.2f}pp" for v in vals],
            textposition="outside", textfont=dict(size=10),
            connector=dict(line=dict(color=C["line"])),
            increasing=dict(marker=dict(color=C["accent"])),
            decreasing=dict(marker=dict(color=C["bad"])),
            totals=dict(marker=dict(color=C["primary"]))))
        ui.show(fig, 280, f"ROE 变动归因（{years[0]}→{years[-1]}）")
        drows = [{"c": [n, T.num(a, 3), T.num(b, 3),
                        (T.delta(c, 2, " pp"), "pos" if c >= 0 else "neg"), d],
                  "t": "normal", "i": 0} for n, c, a, b, d in dp]
        drows.append({"c": ["合计", "", "",
                            (T.delta(sum(x[1] for x in dp), 2, " pp"),
                             "pos" if sum(x[1] for x in dp) >= 0 else "neg"), ""],
                      "t": "tot", "i": 0})
        st.markdown(T.fin_table(["驱动因素", f"{years[0]}年", f"{years[-1]}年",
                                 "对ROE贡献", "口径"], drows), unsafe_allow_html=True)

# ══════════ 行业对标 ══════════
ui.section("行业对标定位")
ind = get_industry_name()
meta = INDUSTRY_META.get(ind, {})
grade = meta.get("grade", "经验参考值")
st.markdown(T.fin_table(
    ["当前基准", "数据性质", "来源", "时点", "口径"],
    [{"c": [ind, grade, meta.get("source", "—"),
            meta.get("as_of", "—"), meta.get("scope", "—")], "t": "normal", "i": 0}]),
    unsafe_allow_html=True)
ui.note(BENCHMARK_DISCLAIMER, "w" if "实测" not in grade else "")

c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(ib.radar_chart(snap, 320), use_container_width=True,
                    config={"displaylogo": False})
with c2:
    st.plotly_chart(ib.scatter_vs_bench(snap, 320), use_container_width=True,
                    config={"displaylogo": False})

summ = ib.industry_summary(snap)
ui.note(f"可比指标中 <b>{summ['n_better']} 项优于基准</b>、<b>{summ['n_worse']} 项低于基准</b>。"
        + ("优势：" + "、".join(n for n, d, u in summ["better"][:3]) + "。" if summ["better"] else "")
        + ("短板：" + "、".join(n for n, d, u in summ["worse"][:3]) + "。" if summ["worse"] else ""))

# ══════════ 关键指标矩阵 ══════════
with st.expander("▸ 关键指标年度矩阵（点击展开）", expanded=False):
    items = [
        ("利润表", "grp", 0, None),
        ("营业收入", "sub", 1, "revenue"), ("营业成本", "normal", 1, "cogs"),
        ("毛利", "normal", 1, "gross_profit"), ("毛利率(%)", "normal", 1, "gross_margin"),
        ("销售费用", "normal", 1, "sell"), ("管理费用", "normal", 1, "admin"),
        ("研发费用", "normal", 1, "rd"), ("财务费用", "normal", 1, "fin"),
        ("EBIT", "sub", 1, "ebit"), ("净利润", "tot", 1, "net_profit"),
        ("资产负债表", "grp", 0, None),
        ("货币资金", "normal", 1, "cash"), ("应收账款", "normal", 1, "ar"),
        ("存货", "normal", 1, "inv"), ("资产总计", "sub", 1, "assets"),
        ("有息负债", "normal", 1, "ibd"), ("负债合计", "normal", 1, "liab"),
        ("股东权益", "tot", 1, "equity"),
        ("现金流量", "grp", 0, None),
        ("经营现金流", "normal", 1, "ocf"), ("资本开支", "normal", 1, "capex"),
        ("自由现金流", "sub", 1, "fcf"), ("折旧摊销", "normal", 1, "da"),
        ("核心比率", "grp", 0, None),
        ("ROE(%)", "normal", 1, "roe"), ("ROA(%)", "normal", 1, "roa"),
        ("净利率(%)", "normal", 1, "net_margin"), ("资产负债率(%)", "normal", 1, "debt_ratio"),
        ("流动比率(倍)", "normal", 1, "current_ratio"),
        ("总资产周转率", "normal", 1, "asset_turnover"),
        ("利息保障倍数", "normal", 1, "interest_cover"),
        ("DSO(天)", "normal", 1, "dso"), ("DIO(天)", "normal", 1, "dio"),
        ("CCC(天)", "normal", 1, "ccc"),
    ]
    headers, rows, df_raw = T.build_year_table(items, years, model, first_header="项目", dec=1)
    st.markdown(T.fin_table(headers, rows), unsafe_allow_html=True)
    st.download_button("⇩ 导出关键指标 CSV",
                       data=df_raw.to_csv(index=False).encode("utf-8-sig"),
                       file_name="关键指标年度矩阵.csv", mime="text/csv")

# ══════════ 业务视角 ══════════
with st.expander("🏢 业务视角：数字背后的业务事件", expanded=False):
    bc.render_panel(model)

ui.drill_bar([
    {"label": "② 业财归因：为什么会这样", "target": "pages/2_业财归因.py",
     "context": {"from": "经营诊断", "focus": "回报归因"}},
    {"label": "③ 财务风险", "target": "pages/3_财务风险.py",
     "context": {"from": "经营诊断", "focus": "预警跟进"}},
], label="下一步")
