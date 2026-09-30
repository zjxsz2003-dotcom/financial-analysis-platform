"""
数据质量诊断 — V2
勾稽校验 + 科目完备度 + 异常值检测，直接决定「分析可信度」
"""
from __future__ import annotations
import numpy as np
import pandas as pd

CRITICAL_INCOME = ["营业收入", "营业成本", "净利润"]
CRITICAL_BALANCE = ["资产总计", "负债合计", "股东权益合计"]
CRITICAL_CASH = ["经营现金流量净额"]
IMPORTANT = {
    "利润表": ["营业收入", "营业成本", "销售费用", "管理费用", "财务费用", "营业利润",
               "利润总额", "净利润", "归母净利润"],
    "资产负债表": ["货币资金", "应收账款净额", "存货净额", "流动资产合计", "流动负债合计",
                   "短期借款", "应付账款", "长期借款", "负债合计", "股东权益合计",
                   "资产总计", "未分配利润"],
    "现金流量表": ["经营现金流量净额", "投资现金流量净额", "筹资现金流量净额", "资本开支"],
}


def _v(df, key):
    if df is None or df.empty or key not in df.columns:
        return None
    s = pd.to_numeric(df[key], errors="coerce")
    return None if s.dropna().empty else float(s.dropna().iloc[-1])


def diagnose(inc, bs, cf, years) -> dict:
    issues, warns, infos = [], [], []
    n = len(years)

    # 1) 期间覆盖
    if n == 0:
        issues.append("未识别到任何年度数据")
        return {"errors": issues, "warnings": warns, "infos": infos,
                "grade": "不可用", "n_years": 0}
    if n < 2:
        warns.append(f"仅识别到 {n} 个年度，同比分析、杜邦分解、趋势类指标将不可用（建议 ≥3 年）")
    elif n < 3:
        warns.append(f"仅 {n} 个年度，趋势判断与回归类分析（经营杠杆）样本偏少")

    # 2) 必缺科目
    for k in CRITICAL_INCOME:
        if _v(inc, k) is None:
            issues.append(f"利润表缺少关键科目「{k}」，核心盈利分析不可用")
    for k in CRITICAL_BALANCE:
        if _v(bs, k) is None:
            issues.append(f"资产负债表缺少关键科目「{k}」，偿债与资本结构分析不可用")
    if _v(cf, "经营现金流量净额") is None:
        issues.append("现金流量表缺少「经营现金流量净额」，现金流质量与自由现金流分析不可用")

    # 3) 勾稽校验
    ta = _v(bs, "资产总计")
    tl = _v(bs, "负债合计")
    te = _v(bs, "股东权益合计")
    if None not in (ta, tl, te):
        diff = ta - (tl + te)
        if abs(diff) > max(abs(ta) * 0.005, 0.5):
            warns.append(f"资产负债表不平：资产 {ta:,.1f} ≠ 负债 {tl:,.1f} + 权益 {te:,.1f}"
                         f"（差 {diff:+,.1f} 亿元）")
        else:
            infos.append(f"资产负债表勾稽平衡（资产 {ta:,.1f} = 负债 {tl:,.1f} + 权益 {te:,.1f}）")

    pt = _v(inc, "利润总额")
    npv = _v(inc, "净利润")
    tax = _v(inc, "所得税费用")
    if None not in (pt, npv, tax):
        d = pt - tax - npv
        if abs(d) > max(abs(pt) * 0.02, 0.5):
            warns.append(f"利润表勾稽偏差：利润总额 {pt:,.1f} − 所得税 {tax:,.1f} ≠ 净利润 {npv:,.1f}"
                         f"（差 {d:+,.1f} 亿元，可能含少数股东损益）")

    rev = _v(inc, "营业收入")
    cogs = _v(inc, "营业成本")
    if rev is not None and rev <= 0:
        issues.append("营业收入 ≤ 0，无法进行盈利能力分析")
    if None not in (rev, cogs) and rev and cogs / rev > 1.0:
        warns.append(f"营业成本率 {cogs/rev*100:.1f}% 超过 100%，毛利率为负，请确认口径")

    # 4) 科目完备度
    completeness = {}
    for stmt, keys in IMPORTANT.items():
        df = {"利润表": inc, "资产负债表": bs, "现金流量表": cf}[stmt]
        found = sum(1 for k in keys if not (df is None or df.empty or k not in df.columns
                                            or pd.to_numeric(df[k], errors="coerce").dropna().empty))
        completeness[stmt] = (found, len(keys), found / len(keys) * 100)
        if found < len(keys) * 0.6:
            warns.append(f"{stmt}科目完备度仅 {found}/{len(keys)}（{found/len(keys)*100:.0f}%），"
                         f"部分深度分析将自动降级")
    if _v(cf, "折旧摊销") is None:
        infos.append("未识别到「折旧摊销」，EBITDA 将按 EBIT 口径近似，盈利质量评分中相关项不计入")
    if _v(cf, "销售商品收到的现金") is None:
        infos.append("未识别到「销售商品、提供劳务收到的现金」，销售收现比不可用")

    # 5) 异常波动检测
    for name, df, key in (("营业收入", inc, "营业收入"), ("净利润", inc, "净利润"),
                          ("资产总计", bs, "资产总计"), ("经营现金流量净额", cf, "经营现金流量净额")):
        if df is None or df.empty or key not in df.columns:
            continue
        s = pd.to_numeric(df[key], errors="coerce").dropna()
        if len(s) < 3:
            continue
        g = s.pct_change().dropna()
        if (g.abs() > 0.6).any():
            warns.append(f"{name}存在单年变动超过 60% 的异常波动，建议确认是否含并表/重组/追溯调整")

    # 6) 评级
    if issues:
        grade = "不可用"
    elif len(warns) >= 3:
        grade = "基本可用（存在较多提示）"
    elif warns:
        grade = "良好"
    else:
        grade = "优秀"

    return {"errors": issues, "warnings": warns, "infos": infos,
            "grade": grade, "n_years": n, "completeness": completeness}
