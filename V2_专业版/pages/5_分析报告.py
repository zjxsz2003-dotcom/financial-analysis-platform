"""
⑤ 分析报告 —— 一键输出给管理层的成果
"""
import numpy as np
import pandas as pd
import streamlit as st

from utils.shell import init
from utils import ui
from utils import tables as T
from modules import finance_core as fc
from modules import report_engine as re_
from modules import llm_writer
from modules.kpi import snapshot, alerts
from modules import page_summary as ps
from modules.data_loader import get_company_name, get_years

init("分析报告", "📄", step=5)

model = fc.build_model()
snap = snapshot(model)
al = alerts(snap)
company = get_company_name()
years = get_years()

ui.page_head(f"{company}　⑤ 分析报告",
             "一键生成结构化深度报告，可导出 Markdown / HTML / PDF")

c1, c2, c3 = st.columns([1, 1, 1.6])
with c1:
    rtype = st.selectbox("报告类型", ["年度综合经营分析报告", "季度经营分析报告", "月度经营快报"],
                         index=0)
with c2:
    use_ai = st.checkbox("AI 润色摘要", value=True,
                         help="需配置 API Key；未配置或校验不通过时自动回退为系统模板")
with c3:
    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
    gen = st.button("📄 生成报告", type="primary", use_container_width=True)

key_map = {"年度综合经营分析报告": "annual", "季度经营分析报告": "quarterly",
           "月度经营快报": "monthly"}

if gen:
    with st.spinner("正在生成…"):
        rep = re_.build_report(model, key_map[rtype])
        st.session_state.report = rep
        if use_ai:
            L = lambda k: fc._last(model.get(k, []))
            facts = {
                "营业收入": f"{T.num(L('revenue'),1)} 亿元（同比 {T.delta(L('rev_growth'),1,'%')}）",
                "净利润": f"{T.num(L('net_profit'),1)} 亿元（同比 {T.delta(L('np_growth'),1,'%')}）",
                "ROE": T.pct(L("roe"), 2), "毛利率": T.pct(L("gross_margin"), 2),
                "净利率": T.pct(L("net_margin"), 2), "资产负债率": T.pct(L("debt_ratio"), 2),
                "经营现金流": f"{T.num(L('ocf'),1)} 亿元",
                "经营现金流/净利润": T.num(L("ocf_to_ni"), 2),
                "自由现金流": f"{T.num(L('fcf'),1)} 亿元",
                "现金转换周期": f"{T.num(L('ccc'),0)} 天",
                "应收账款周转天数": f"{T.num(L('dso'),0)} 天",
                "存货周转天数": f"{T.num(L('dio'),0)} 天",
                "综合风险评分": f"{T.num(rep['risk_score'],0)} 分（{rep['risk_level']}）",
            }
            st.session_state.ai_summary = llm_writer.polish(facts, al, company, rep["period"])

rep = st.session_state.get("report")
if not rep:
    ui.note("点击「生成报告」后在此查看完整内容，可导出 Markdown / HTML / PDF。")
    st.stop()

st.success(f"✅ {rep['title']} 已生成")

try:
    h, bl, tone = ps.summary_report(rep)
    ui.exec_summary(h, bl, tone, title="核心结论")
except Exception as e:
    st.caption(f"（结论生成跳过：{e}）")

ui.section("执行摘要")
ai = st.session_state.get("ai_summary")
if ai:
    st.caption("🤖 AI 生成（数值已校验）" if ai["ai"] else "📋 系统模板（AI 未通过校验或未配置）")
    st.markdown(ai["text"])
else:
    st.markdown(rep["sections"][0]["note"])

ui.section("报告正文")
for s in rep["sections"]:
    st.markdown(f'<div class="sec"><span class="bar"></span>'
                f'<span class="t">{s["h"]}</span></div>', unsafe_allow_html=True)
    if s.get("body"):
        st.markdown(s["body"])
    tbl = s.get("table")
    if tbl is not None and not tbl.empty:
        st.dataframe(tbl, use_container_width=True, hide_index=True,
                     height=min(60 + 32 * len(tbl), 400))

ui.section("导出")
md = re_.to_markdown(rep)
html = re_.to_html(rep)
d1, d2, d3 = st.columns(3)
with d1:
    st.download_button("⇩ Markdown", data=md.encode("utf-8"),
                       file_name=f"{company}_{rep['period']}_经营分析报告.md",
                       mime="text/markdown", use_container_width=True)
with d2:
    st.download_button("⇩ HTML（可打印为PDF）", data=html.encode("utf-8"),
                       file_name=f"{company}_{rep['period']}_经营分析报告.html",
                       mime="text/html", use_container_width=True)
with d3:
    pdf = re_.to_pdf(rep)
    if pdf:
        st.download_button("⇩ PDF", data=pdf,
                           file_name=f"{company}_{rep['period']}_经营分析报告.pdf",
                           mime="application/pdf", use_container_width=True)
    else:
        st.warning("PDF 需系统中文字体，建议改用 HTML 导出后打印。")

with st.expander("预览 Markdown 全文"):
    st.code(md, language="markdown")
