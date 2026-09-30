"""
报告引擎 — V2
生成结构化深度经营分析报告（Markdown / HTML / PDF）
所有数值均由计算引擎产出，AI 仅用于文字润色且带防幻觉校验
"""
from __future__ import annotations
from typing import Optional
import io
import numpy as np
import pandas as pd

from modules import finance_core as fc
from modules import business_deep as bd
from modules import budget_analysis as ba
from modules import risk_analysis as ra
from modules import strategy as stg
from modules.kpi import snapshot, alerts, dim_stats
from modules.data_loader import (get_company_name, get_company_code, get_years,
                                 get_industry_name, get_strategy)
from config import C


def _f(v, dec=1, dash="—"):
    return dash if v is None or v != v else f"{float(v):,.{dec}f}"


def _p(v, dec=1, dash="—"):
    return dash if v is None or v != v else f"{float(v):.{dec}f}%"


def _sg(v, dec=1, dash="—"):
    return dash if v is None or v != v else f"{float(v):+,.{dec}f}"


def _md_table(df: pd.DataFrame, floatfmt="{:,.2f}") -> str:
    if df is None or df.empty:
        return ""
    d = df.copy()

    def fmt(x):
        if isinstance(x, float):
            if x != x:
                return "—"
            return floatfmt.format(x)
        return str(x)
    for c in d.columns:
        d[c] = d[c].map(fmt)
    return d.to_markdown(index=False)


# ════════════════════════════════════════════════════════════
# 报告构建
# ════════════════════════════════════════════════════════════
def build_report(model: dict, report_type: str = "annual") -> dict:
    company = get_company_name()
    code = get_company_code()
    years = get_years()
    latest = years[-1] if years else "—"
    snap = snapshot(model)
    al = alerts(snap)

    TYPE_CN = {"monthly": "月度经营快报", "quarterly": "季度经营分析报告",
               "annual": "年度综合经营分析报告"}
    title = f"{company}（{code}）{TYPE_CN.get(report_type, '经营分析报告')}"

    i = model["n"] - 1
    rev = fc._last(model["revenue"])
    npv = fc._last(model["net_profit"])
    roe = fc._last(model["roe"])
    gm = fc._last(model["gross_margin"])
    ocf = fc._last(model["ocf"])
    fcf = fc._last(model["fcf"])
    dr = fc._last(model["debt_ratio"])
    ccc = fc._last(model["ccc"])

    sections = []

    # ── 执行摘要 ──
    hl = [
        f"**营业收入** {_f(rev)} 亿元，同比 {_sg(fc._last(model['rev_growth']))}%",
        f"**净利润** {_f(npv)} 亿元，同比 {_sg(fc._last(model['np_growth']))}%",
        f"**ROE** {_p(roe, 2)}｜**毛利率** {_p(gm, 2)}｜**资产负债率** {_p(dr)}",
        f"**经营现金流** {_f(ocf)} 亿元，经营现金流/净利润 {_f(fc._last(model['ocf_to_ni']), 2)}",
        f"**自由现金流** {_f(fcf)} 亿元｜**现金转换周期** {_f(ccc, 0)} 天",
    ]
    rs = ra.risk_scorecard(model)
    lv, stt = ra.risk_level(rs["total"])
    alert_txt = ""
    if al:
        alert_txt = "\n\n**预警信号**\n" + "\n".join(
            [f"- {'🔴' if a['status']=='danger' else '🟡'} {a['name']}：{_f(a['value'], a['dec'])}{a['unit']}"
             for a in al[:8]])
    else:
        alert_txt = "\n\n本期未触发预警信号，各项指标处于阈值安全区间。"

    summary = (
        f"{company} {latest} 年度经营表现如下：营业收入 {_f(rev)} 亿元（{_sg(fc._last(model['rev_growth']))}%），"
        f"净利润 {_f(npv)} 亿元（{_sg(fc._last(model['np_growth']))}%），ROE {_p(roe, 2)}。"
        f"盈利质量方面，经营现金流/净利润 {_f(fc._last(model['ocf_to_ni']), 2)}，"
        f"自由现金流 {_f(fcf)} 亿元。"
        f"财务风险综合评分 {_f(rs['total'], 0)} 分（{lv}）。"
        + alert_txt
    )
    sections.append({"h": "一、执行摘要", "body": "\n".join(hl), "note": summary})

    # ── 杜邦分解 ──
    dp = fc.dupont_decompose(model, 0, model["n"] - 1)
    if dp:
        rows = [{"因素": n, "贡献(pp)": round(c, 2), f"{years[0]}年": _f(a, 3),
                 f"{years[-1]}年": _f(b, 3), "口径": d}
                for n, c, a, b, d in dp]
        df = pd.DataFrame(rows)
        total_roe_chg = (fc._last(model["roe"]) or 0) - (model["roe"][0] or 0)
        main = max(dp, key=lambda x: abs(x[1]))
        body = (f"ROE 由 {_p(model['roe'][0], 2)} 变动至 {_p(fc._last(model['roe']), 2)}"
                f"（{_sg(total_roe_chg, 2)}pp）。按连环替代法分解，"
                f"最主要的驱动因素是**{main[0]}**，贡献 {_sg(main[1], 2)}pp。")
        sections.append({"h": "二、股东回报：杜邦五因素分解", "body": body, "table": df})

    # ── 盈利质量 ──
    eq = fc.earnings_quality_score(model)
    cb = fc.cash_bridge(model)
    eq_rows = [{"评价维度": r["维度"], "得分": None if r["得分"] is None else round(r["得分"], 0),
                "权重": r["权重"]} for r in eq["items"]]
    body = (f"盈利质量综合得分 **{_f(eq['score'], 0)} 分**（满分 100）。\n\n"
            f"净利润 {_f(cb['净利润'])} 亿元 → 加回折旧摊销 {_f(cb['折旧摊销'])} 亿元 → "
            f"营运资本变动 {_sg(cb['营运资本变动'])} 亿元 → **经营现金流 {_f(cb['经营现金流'])} 亿元** → "
            f"扣除资本开支 {_f(cb['资本开支'])} 亿元 → **自由现金流 {_f(cb['自由现金流'])} 亿元**。")
    sections.append({"h": "三、盈利质量与现金流", "body": body,
                     "table": pd.DataFrame(eq_rows)})

    # ── 营运资本 ──
    wc = bd.working_capital(model)
    arq = bd.ar_quality(model)
    inq = bd.inventory_quality(model)
    wc_rows = pd.DataFrame([
        {"指标": "应收周转天数 DSO", "本期": _f(wc["dso"], 0), "变动": _sg((fc._last(model['dso']) or 0) - (fc._prev(model['dso']) or 0), 0)},
        {"指标": "存货周转天数 DIO", "本期": _f(wc["dio"], 0), "变动": _sg((fc._last(model['dio']) or 0) - (fc._prev(model['dio']) or 0), 0)},
        {"指标": "应付周转天数 DPO", "本期": _f(wc["dpo"], 0), "变动": _sg((fc._last(model['dpo']) or 0) - (fc._prev(model['dpo']) or 0), 0)},
        {"指标": "现金转换周期 CCC", "本期": _f(wc["ccc"], 0), "变动": _sg((wc["ccc"] or 0) - (wc["ccc0"] or 0), 0)},
    ])
    body = (f"现金转换周期 {_f(wc['ccc'], 0)} 天（DSO {_f(wc['dso'], 0)} + DIO {_f(wc['dio'], 0)} − DPO {_f(wc['dpo'], 0)}）。"
            f"CCC 每缩短 10 天可释放营运资金约 {_f(wc['release'])} 亿元。\n\n"
            f"- 应收：{arq['insight'][0][1]}\n- 存货：{inq['insight'][0][1]}")
    sections.append({"h": "四、营运资本效率", "body": body, "table": wc_rows})

    # ── 业务板块（如有） ──
    so = bd.segment_overview(model)
    if so:
        d = so["df"][["板块", "收入", "增速", "毛利率", "收入占比"]].copy()
        d.columns = ["业务板块", "收入(亿元)", "同比(%)", "毛利率(%)", "收入占比(%)"]
        sections.append({"h": "五、业务板块结构", "body": so["insight"][0][1],
                         "table": d})

    # ── 预算执行 ──
    bv = ba.budget_vs_actual(model)
    if bv:
        pb = ba.profit_bridge(model, bv)
        rows = []
        for cat in ("收入", "费用", "利润"):
            for name, d in bv.get(cat, {}).items():
                rows.append({"类别": cat, "项目": name, "预算": d["预算"],
                             "实际": d["实际"], "偏差": d["偏差"],
                             "偏差率(%)": d["偏差率"]})
        dfb = pd.DataFrame(rows)
        body = ""
        if pb:
            body = (f"净利润 {_f(pb['steps'][0]['value'])} 亿元（预算）→ {_f(pb['steps'][-1]['value'])} 亿元（实际），"
                    f"偏差 {_sg(pb['total'])} 亿元。其中：收入规模效应 {_sg(pb['vol'])} 亿元、"
                    f"毛利率效应 {_sg(pb['margin'])} 亿元、期间费用效应 {_sg(pb['fee'])} 亿元、"
                    f"税项及其他 {_sg(pb['other'])} 亿元。")
        sections.append({"h": "六、预算执行与偏差归因", "body": body, "table": dfb})

    # ── 风险 ──
    sc = ra.scorecard_df(rs)
    az = ra.altman_detail(model)
    body = f"综合风险评分 **{_f(rs['total'], 0)} 分（{lv}）**。\n\n"
    for _, r in sc.iterrows():
        body += f"- {r['风险维度']}：{_f(r['风险分'], 0)} 分（{r['等级']}），权重 {r['权重']:.0%}\n"
    if az:
        body += (f"\nAltman Z-Score（制造业口径）**{_f(az['z'], 2)}**，处于{az['zone'][0]}；"
                 f"私营企业口径 Z' **{_f(az['zp'], 2)}**，处于{az['zone_p'][0]}。")
    lp = ra.liquidity_profile(model)
    body += (f"\n\n流动性：货币资金 {_f(lp['cash'])} 亿元，短期有息负债 {_f(lp['short_total'])} 亿元，"
             f"现金/短债 {_f(lp['cover_short'], 2)} 倍；"
             f"经营现金流 {_f(lp['ocf'])} 亿元，资本开支 {_f(lp['capex'])} 亿元，"
             f"自由现金流 {_f(lp['fcf'])} 亿元。")
    sections.append({"h": "七、财务风险评估", "body": body, "table": sc})

    # ── 压力测试 ──
    sc_df = ra.scenario_compare(model)
    if not sc_df.empty:
        sections.append({"h": "八、情景压力测试", "body":
                         "在收入、毛利率、回款与融资成本同时承压时，净利润与偿债指标的变化如下"
                         "（假设期间费用刚性、营运资金占用按 5% 计资金成本）：",
                         "table": sc_df})

    # ── 战略 ──
    tg = stg.progress(get_strategy(model), 50.0)
    rows = [{"战略目标": t["name"], "当前": t["current_value"], "目标": t["target_value"],
             "完成率(%)": None if t["progress"] is None else round(t["progress"], 1)}
            for t in tg]
    sections.append({"h": "九、战略目标进度", "body":
                     "以下目标由系统基于历史经营数据自动生成，可在战略页面改写：",
                     "table": pd.DataFrame(rows)})

    # ── 行动清单 ──
    acts = ba.action_quantification(model)
    acts_df = pd.DataFrame(acts)[["措施", "影响净利润(亿元)", "难度", "周期", "说明"]]
    watch = []
    for a in al[:6]:
        t = ra.TRANSMISSION.get(a["key"])
        if t:
            watch.append({"优先级": "🔴 高" if a["status"] == "danger" else "🟡 中",
                          "预警指标": a["name"], "业务根因": t[0],
                          "管理动作": t[2]})
    if watch:
        acts_df = pd.concat([pd.DataFrame(watch).rename(columns={"预警指标": "措施"}),
                             acts_df], ignore_index=True)
    sections.append({"h": "十、管理层行动清单", "body":
                     "按「影响金额 × 紧迫度」排序，前项为预警指标对应的整改动作，后项为可量化的改善抓手：",
                     "table": acts_df})

    return {"title": title, "company": company, "period": f"{latest} 年度",
            "sections": sections, "risk_score": rs["total"], "risk_level": lv,
            "alerts": al, "industry": get_industry_name()}


def to_markdown(rep: dict) -> str:
    lines = [f"# {rep['title']}", "",
             f"> 分析对象：{rep['company']}　｜　期间：{rep['period']}　｜　"
             f"行业基准：{rep.get('industry','')}　｜　"
             f"综合风险：{_f(rep['risk_score'],0)} 分（{rep['risk_level']}）", ""]
    for idx, s in enumerate(rep["sections"], start=1):
        lines.append(f"## {idx}. {s['h'].split('、', 1)[-1]}")
        lines.append("")
        if s.get("body"):
            lines.append(s["body"])
            lines.append("")
        if s.get("table") is not None and not s["table"].empty:
            lines.append(_md_table(s["table"]))
            lines.append("")
        if s.get("note"):
            lines.append("---")
            lines.append("")
            lines.append(s["note"])
            lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*本报告由企业经营分析与风险预警平台自动生成，数据来源于导入的财务报表，"
                 "分析结论由规则引擎推导，仅供经营决策参考。*")
    return "\n".join(lines)


def to_html(rep: dict) -> str:
    css = """
    <style>
    body{font-family:"Microsoft YaHei","PingFang SC",sans-serif;color:#1F2937;
         max-width:960px;margin:24px auto;padding:0 20px;line-height:1.75;font-size:14px;}
    h1{color:#0F2B46;font-size:23px;border-bottom:3px solid #1B4F8A;padding-bottom:10px;}
    h2{color:#1B4F8A;font-size:17px;margin-top:26px;border-left:4px solid #1B4F8A;padding-left:10px;}
    blockquote{background:#F4F8FC;border-left:3px solid #2E7FD1;padding:8px 14px;
               margin:10px 0;color:#4A5568;font-size:13px;}
    table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13px;}
    th{background:#1B4F8A;color:#fff;padding:7px 10px;text-align:right;font-weight:600;}
    th:first-child{text-align:left;}
    td{padding:6px 10px;border-bottom:1px solid #EDF1F6;text-align:right;
       font-variant-numeric:tabular-nums;}
    td:first-child{text-align:left;}
    tr:nth-child(even) td{background:#F8FAFC;}
    hr{border:0;border-top:1px solid #DCE3EC;margin:18px 0;}
    .foot{color:#7A8798;font-size:12px;margin-top:24px;border-top:1px solid #DCE3EC;padding-top:10px;}
    @media print{body{margin:0;}}
    </style>"""
    parts = [f"<html><head><meta charset='utf-8'>{css}</head><body>",
             f"<h1>{rep['title']}</h1>",
             f"<blockquote>分析对象：{rep['company']}　｜　期间：{rep['period']}　｜　"
             f"行业基准：{rep.get('industry','')}　｜　"
             f"综合风险：{_f(rep['risk_score'],0)} 分（{rep['risk_level']}）</blockquote>"]
    for s in rep["sections"]:
        parts.append(f"<h2>{s['h']}</h2>")
        if s.get("body"):
            parts.append("<p>" + s["body"].replace("\n", "<br>") + "</p>")
        if s.get("table") is not None and not s["table"].empty:
            d = s["table"].copy()

            def fm(x):
                if isinstance(x, float):
                    return "—" if x != x else f"{x:,.2f}"
                return str(x)
            for c in d.columns:
                d[c] = d[c].map(fm)
            parts.append(d.to_html(index=False, escape=False))
        if s.get("note"):
            parts.append("<hr><p>" + s["note"].replace("\n", "<br>") + "</p>")
    parts.append("<div class='foot'>本报告由企业经营分析与风险预警平台自动生成，"
                 "数据来源于导入的财务报表，分析结论由规则引擎推导，仅供经营决策参考。</div>")
    parts.append("</body></html>")
    return "".join(parts)


def to_pdf(rep: dict) -> Optional[bytes]:
    """尽力而为：需要系统中文字体，失败返回 None"""
    try:
        from fpdf import FPDF
        import os
        font_path = None
        for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simsun.ttc",
                  r"C:\Windows\Fonts\simhei.ttf",
                  "/System/Library/Fonts/PingFang.ttc",
                  "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"):
            if os.path.exists(p):
                font_path = p
                break
        if not font_path:
            return None
        pdf = FPDF()
        pdf.add_font("cn", "", font_path, uni=True)
        pdf.set_font("cn", size=10.5)
        pdf.add_page()
        pdf.set_font("cn", size=15)
        pdf.cell(0, 10, rep["title"], ln=1)
        pdf.set_font("cn", size=9)
        pdf.set_text_color(110, 120, 135)
        pdf.cell(0, 6, f"{rep['company']} | {rep['period']} | 综合风险 {_f(rep['risk_score'],0)} 分", ln=1)
        pdf.set_text_color(30, 40, 55)
        pdf.ln(3)
        for s in rep["sections"]:
            pdf.set_font("cn", size=12)
            pdf.cell(0, 8, s["h"], ln=1)
            pdf.set_font("cn", size=9.5)
            if s.get("body"):
                for ln in str(s["body"]).split("\n"):
                    pdf.multi_cell(0, 5, ln)
            pdf.ln(2)
        return pdf.output(dest="S").encode("latin-1", errors="ignore")
    except Exception:
        return None
