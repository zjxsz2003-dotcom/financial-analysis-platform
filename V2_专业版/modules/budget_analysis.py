"""
预算偏差分析 — V2（升级版）
核心升级：
  1) 利润桥：预算净利润 → 收入/成本/费用偏差 → 实际净利润（瀑布）
  2) 毛利偏差的「规模效应 × 毛利率效应」两因素分解（精确无残差）
  3) 费用偏差的「规模效应 × 费率效应」两因素分解
  4) 滚动预测：进度外推全年 → 达成缺口 → 剩余期间所需提速幅度
  5) 改善措施量化：每项动作对净利润/现金流的贡献可测算
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from modules.data_loader import get_budget, get_segments
from modules import finance_core as fc
from config import C

_DASH = "—"


def _f(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):,.{dec}f}"


def _p(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):.{dec}f}%"


def _sg(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):+,.{dec}f}"


def _status(dev_pct, tol=5.0, higher_better=True):
    """偏差状态"""
    if dev_pct is None:
        return "na"
    d = dev_pct if higher_better else -dev_pct
    if d < -tol * 2:
        return "danger"
    if d < -tol:
        return "warning"
    return "normal"


# ════════════════════════════════════════════════════════════
# 1. 预算 vs 实际 全口径
# ════════════════════════════════════════════════════════════
def budget_vs_actual(model: dict, budget: dict = None) -> dict:
    budget = budget or get_budget()
    if not budget or not model:
        return {}
    i = model["n"] - 1
    rev_a = fc._last(model["revenue"])
    cogs_a = fc._last(model["cogs"])
    seg = get_segments()

    res = {"收入": {}, "成本": {}, "费用": {}, "利润": {}}

    # 收入
    for name, b in budget.get("收入预算", {}).items():
        if name == "合计":
            continue
        a = None
        if len(seg) >= 2 and name in seg:
            a = seg[name]["收入"][i] if i < len(seg[name]["收入"]) else None
        elif len(seg) < 2:
            a = rev_a
        if a is None:
            a = rev_a
        dev = None if (a is None or b is None) else a - b
        dp = None if (dev is None or not b) else dev / b * 100
        res["收入"][name] = {"预算": b, "实际": a, "偏差": dev, "偏差率": dp,
                             "完成率": (a / b * 100) if (a is not None and b) else None,
                             "status": _status(dp, 5.0, True)}
    b_tot = budget.get("收入预算", {}).get("合计")
    if b_tot:
        a_tot = sum(v["实际"] for v in res["收入"].values() if v["实际"] is not None) or rev_a
        res["收入"]["合计"] = {"预算": b_tot, "实际": a_tot, "偏差": a_tot - b_tot,
                               "偏差率": (a_tot - b_tot) / b_tot * 100 if b_tot else None,
                               "完成率": a_tot / b_tot * 100 if b_tot else None,
                               "status": _status((a_tot - b_tot) / b_tot * 100 if b_tot else None, 5.0, True)}

    # 成本（越低越好）
    for name, b in budget.get("成本预算", {}).items():
        if name == "合计":
            continue
        a = None
        if len(seg) >= 2 and name in seg:
            a = seg[name]["成本"][i] if i < len(seg[name]["成本"]) else None
        elif len(seg) < 2:
            a = cogs_a
        if a is None:
            a = cogs_a
        dev = None if (a is None or b is None) else a - b
        dp = None if (dev is None or not b) else dev / b * 100
        res["成本"][name] = {"预算": b, "实际": a, "偏差": dev, "偏差率": dp,
                             "完成率": (a / b * 100) if (a is not None and b) else None,
                             "status": _status(dp, 5.0, False)}

    # 费用（越低越好）
    fee_series = {"销售费用": "sell", "管理费用": "admin",
                  "研发费用": "rd", "财务费用": "fin"}
    for name, b in budget.get("费用预算", {}).items():
        a = fc._last(model[fee_series.get(name, "sell")]) if name in fee_series else None
        dev = None if (a is None or b is None) else a - b
        dp = None if (dev is None or not b) else dev / b * 100
        res["费用"][name] = {"预算": b, "实际": a, "偏差": dev, "偏差率": dp,
                             "完成率": (a / b * 100) if (a is not None and b) else None,
                             "status": _status(dp, 8.0, False)}

    # 利润
    for name, b in budget.get("利润预算", {}).items():
        a = fc._last(model["op_profit"]) if name == "营业利润" else fc._last(model["net_profit"])
        dev = None if (a is None or b is None) else a - b
        dp = None if (dev is None or not b) else dev / b * 100
        res["利润"][name] = {"预算": b, "实际": a, "偏差": dev, "偏差率": dp,
                             "完成率": (a / b * 100) if (a is not None and b) else None,
                             "status": _status(dp, 5.0, True)}
    res["_assumption"] = budget.get("_assumption", {})
    return res


# ════════════════════════════════════════════════════════════
# 2. 利润桥（预算净利润 → 实际净利润）
# ════════════════════════════════════════════════════════════
def profit_bridge(model: dict, bv: dict) -> Optional[dict]:
    """
    Δ净利润 = 收入偏差(按预算毛利率折算) + 毛利率偏差 + 费用偏差 + 其他（税/营业外/所得税）
    逐步桥接，最后一项为「未解释项」保证闭合
    """
    if not bv or "利润" not in bv or "净利润" not in bv["利润"]:
        return None
    np_b = bv["利润"]["净利润"]["预算"]
    np_a = bv["利润"]["净利润"]["实际"]
    if np_b is None or np_a is None:
        return None

    rev_b = bv["收入"].get("合计", {}).get("预算") or sum(
        v["预算"] for k, v in bv["收入"].items() if k != "合计" and v["预算"])
    rev_a = bv["收入"].get("合计", {}).get("实际") or sum(
        v["实际"] for k, v in bv["收入"].items() if k != "合计" and v["实际"])

    cogs_b = sum(v["预算"] for k, v in bv["成本"].items() if v["预算"] is not None)
    cogs_a = sum(v["实际"] for k, v in bv["成本"].items() if v["实际"] is not None)
    fee_b = sum(v["预算"] for v in bv["费用"].values() if v["预算"] is not None)
    fee_a = sum(v["实际"] for v in bv["费用"].values() if v["实际"] is not None)

    gm_b = (rev_b - cogs_b) / rev_b if rev_b else 0.0
    gm_a = (rev_a - cogs_a) / rev_a if rev_a else 0.0

    # 收入规模效应：以预算毛利率承接增量收入
    vol_eff = (rev_a - rev_b) * gm_b
    # 毛利率效应：实际收入 × 毛利率差
    margin_eff = rev_a * (gm_a - gm_b)
    # 费用效应（费用增加为负向）
    fee_eff = -(fee_a - fee_b)
    explained = vol_eff + margin_eff + fee_eff
    total = np_a - np_b
    other = total - explained    # 税、营业外、投资收益等

    steps = [
        {"name": "预算净利润", "value": np_b, "type": "total"},
        {"name": "收入规模效应", "value": vol_eff, "type": "delta"},
        {"name": "毛利率效应", "value": margin_eff, "type": "delta"},
        {"name": "期间费用效应", "value": fee_eff, "type": "delta"},
        {"name": "税项及其他", "value": other, "type": "delta"},
        {"name": "实际净利润", "value": np_a, "type": "total"},
    ]
    return {"steps": steps, "total": total, "rev_b": rev_b, "rev_a": rev_a,
            "gm_b": gm_b * 100, "gm_a": gm_a * 100,
            "vol": vol_eff, "margin": margin_eff, "fee": fee_eff, "other": other}


def profit_bridge_chart(pb: dict, height=300) -> go.Figure:
    from utils.ui import waterfall
    steps = pb["steps"]
    x = [s["name"] for s in steps]
    y = [s["value"] for s in steps]
    measure = ["absolute"] + ["relative"] * (len(steps) - 2) + ["total"]
    return waterfall(x, y, measure, height=height, title="净利润预算偏差桥（亿元）",
                     text_fmt="{:+,.1f}")


# ════════════════════════════════════════════════════════════
# 3. 毛利偏差两因素分解（规模 × 毛利率），分板块
# ════════════════════════════════════════════════════════════
def gross_profit_variance(model: dict, bv: dict) -> Optional[pd.DataFrame]:
    """
    ΔGP = Σ ΔRev_i × GM_b,i  (规模效应)  + Σ Rev_a,i × ΔGM_i (毛利率效应)
    两效应之和精确等于 ΔGP
    """
    if not bv or not bv.get("收入"):
        return None
    rows = []
    for name, d in bv["收入"].items():
        if name == "合计":
            continue
        rev_b, rev_a = d["预算"], d["实际"]
        cb = bv.get("成本", {}).get(name, {}).get("预算")
        ca = bv.get("成本", {}).get(name, {}).get("实际")
        if None in (rev_b, rev_a, cb, ca) or not rev_b:
            continue
        gm_b = (rev_b - cb) / rev_b
        gm_a = (rev_a - ca) / rev_a if rev_a else 0
        vol = (rev_a - rev_b) * gm_b
        mar = rev_a * (gm_a - gm_b)
        rows.append({
            "板块": name,
            "预算收入": rev_b, "实际收入": rev_a,
            "预算毛利率(%)": gm_b * 100, "实际毛利率(%)": gm_a * 100,
            "规模效应(亿元)": vol, "毛利率效应(亿元)": mar,
            "毛利偏差(亿元)": vol + mar,
            "主因": "规模" if abs(vol) >= abs(mar) else "毛利率",
        })
    if not rows:
        return None
    return pd.DataFrame(rows)


def revenue_variance_detail(bv: dict) -> pd.DataFrame:
    rows = []
    for name, d in bv.get("收入", {}).items():
        rows.append({
            "板块": name, "预算收入(亿元)": d["预算"], "实际收入(亿元)": d["实际"],
            "偏差(亿元)": d["偏差"], "偏差率(%)": d["偏差率"],
            "完成率(%)": d["完成率"], "状态": d["status"],
        })
    return pd.DataFrame(rows)


def expense_variance(bv: dict, model: dict) -> pd.DataFrame:
    """费用偏差 = 规模效应(收入增量×预算费率) + 费率效应(实际收入×费率差)"""
    rev_b = bv["收入"].get("合计", {}).get("预算")
    rev_a = bv["收入"].get("合计", {}).get("实际") or fc._last(model["revenue"])
    rows = []
    for name, d in bv.get("费用", {}).items():
        b, a = d["预算"], d["实际"]
        if None in (b, a, rev_b, rev_a) or not rev_b:
            rows.append({"科目": name, "预算": b, "实际": a, "偏差": None if None in (a, b) else a - b,
                         "偏差率(%)": d["偏差率"], "规模效应": None, "费率效应": None,
                         "状态": d["status"], "评价": _DASH})
            continue
        rate_b = b / rev_b
        rate_a = a / rev_a if rev_a else 0
        vol = (rev_a - rev_b) * rate_b
        rate = rev_a * (rate_a - rate_b)
        rows.append({
            "科目": name, "预算": b, "实际": a, "偏差": a - b, "偏差率(%)": d["偏差率"],
            "规模效应": vol, "费率效应": rate, "状态": d["status"],
            "评价": "费率受控" if rate <= 0 else "费率上行",
        })
    return pd.DataFrame(rows)


# ════════════════════════════════════════════════════════════
# 4. 滚动预测 / 进度外推
# ════════════════════════════════════════════════════════════
SEASONALITY = {
    "均匀分布": [1 / 12] * 12,
    "消费电子（旺季后置）": [0.070, 0.058, 0.072, 0.075, 0.078, 0.082, 0.085, 0.088,
                            0.092, 0.095, 0.085, 0.120],
    "工程项目（年末确认）": [0.045, 0.040, 0.060, 0.065, 0.070, 0.080, 0.085, 0.090,
                            0.095, 0.100, 0.110, 0.160],
    "零售（节假日驱动）": [0.100, 0.115, 0.070, 0.068, 0.072, 0.075, 0.078, 0.080,
                          0.082, 0.085, 0.085, 0.090],
}
SEASON_LABELS = ["1月", "2月", "3月", "4月", "5月", "6月",
                 "7月", "8月", "9月", "10月", "11月", "12月"]


def rolling_forecast(model: dict, bv: dict, months: int = 6,
                     ytd_revenue: float = None, ytd_profit: float = None,
                     season: str = "均匀分布") -> dict:
    """
    进度外推：全年预计 = 迄今实际 / 累计季节权重
    → 达成缺口、剩余期间所需月均、所需提速幅度
    """
    rev_a = bv["收入"].get("合计", {}).get("实际") if bv.get("收入", {}).get("合计") else None
    rev_a = rev_a or fc._last(model["revenue"])
    np_a = bv["利润"].get("净利润", {}).get("实际")
    np_a = np_a if np_a is not None else fc._last(model["net_profit"])
    rev_b = bv["收入"].get("合计", {}).get("预算")
    np_b = bv["利润"].get("净利润", {}).get("预算")

    w = SEASONALITY.get(season, SEASONALITY["均匀分布"])
    cum = sum(w[:months]) or (months / 12)
    ytd = ytd_revenue if ytd_revenue is not None else (rev_a * cum if rev_a else None)
    ytd_p = ytd_profit if ytd_profit is not None else (np_a * cum if np_a else None)

    fc_rev = ytd / cum if (ytd is not None and cum) else None
    fc_np = ytd_p / cum if (ytd_p is not None and cum) else None

    def gap(f, b):
        return None if (f is None or b is None) else b - f

    remain_m = 12 - months
    need_monthly = gap(fc_rev, rev_b) / remain_m if (remain_m and None not in (fc_rev, rev_b)) else None
    cur_monthly = ytd / months if (ytd is not None and months) else None
    speedup = (need_monthly / cur_monthly - 1) * 100 if (need_monthly and cur_monthly) else None

    return {
        "months": months, "season": season, "cum_weight": cum,
        "ytd_revenue": ytd, "ytd_profit": ytd_p,
        "fc_revenue": fc_rev, "fc_profit": fc_np,
        "budget_revenue": rev_b, "budget_profit": np_b,
        "gap_revenue": gap(fc_rev, rev_b), "gap_profit": gap(fc_np, np_b),
        "complete_rate": (ytd / rev_b * 100) if (ytd is not None and rev_b) else None,
        "time_rate": cum * 100,
        "need_monthly": need_monthly, "cur_monthly": cur_monthly, "speedup": speedup,
        "remain_months": remain_m,
    }


# ════════════════════════════════════════════════════════════
# 5. 改善措施量化
# ════════════════════════════════════════════════════════════
def action_quantification(model: dict) -> list:
    """把管理动作换算成对净利润的影响（亿元）"""
    rev = fc._last(model["revenue"]) or 0
    gm = fc._last(model["gross_margin"]) or 0
    cogs = fc._last(model["cogs"]) or 0
    per_day_rev = rev / 365 if rev else 0
    per_day_cogs = cogs / 365 if cogs else 0
    actions = [
        {"措施": "销售毛利率 +1pp", "口径": "收入 × 1%",
         "影响净利润(亿元)": rev * 0.01, "难度": "中", "周期": "2-3 个季度",
         "说明": "通过涨价、结构升级或降本实现，需业务与采购协同"},
        {"措施": "期间费用率 -0.5pp", "口径": "收入 × 0.5%",
         "影响净利润(亿元)": rev * 0.005, "难度": "中", "周期": "1-2 个季度",
         "说明": "零基预算 + 费用立项审批，优先压缩弹性费用"},
        {"措施": "营业成本率 -1pp", "口径": "收入 × 1%",
         "影响净利润(亿元)": rev * 0.01, "难度": "高", "周期": "3-4 个季度",
         "说明": "BOM 降本、良率提升、工艺优化，需供应链深度参与"},
        {"措施": "DSO 缩短 10 天", "口径": "日收入 × 10",
         "影响净利润(亿元)": per_day_rev * 10 * 0.05, "难度": "中", "周期": "1-2 个季度",
         "说明": "释放营运资金，按 5% 资金成本折算年化收益"},
        {"措施": "DIO 缩短 10 天", "口径": "日成本 × 10",
         "影响净利润(亿元)": per_day_cogs * 10 * 0.05, "难度": "中", "周期": "2-3 个季度",
         "说明": "降低跌价风险与资金占用，按 5% 资金成本折算"},
        {"措施": "收入 +5%（增量毛利）", "口径": "收入 × 5% × 毛利率",
         "影响净利润(亿元)": rev * 0.05 * gm / 100, "难度": "高", "周期": "年度",
         "说明": "增量收入按当前毛利率转化为毛利，未计增量费用"},
    ]
    return actions


def budget_slack_check(bv: dict) -> dict:
    """预算松弛度：若多数科目大幅超额完成，说明预算偏松"""
    rates = []
    for cat in ("收入", "利润"):
        for name, d in bv.get(cat, {}).items():
            if d.get("完成率") is not None:
                rates.append(d["完成率"])
    if not rates:
        return {"ok": False}
    avg = float(np.mean(rates))
    if avg > 115:
        lvl, txt = "danger", "预算明显偏松（平均完成率 >115%），预算对经营的约束作用被削弱，建议引入零基预算与更激进的目标设定"
    elif avg > 105:
        lvl, txt = "warning", "预算偏松（平均完成率 105%-115%），建议提高目标挑战性"
    elif avg < 90:
        lvl, txt = "warning", "预算偏紧或执行不力（平均完成率 <90%），需区分是目标不合理还是执行问题"
    else:
        lvl, txt = "normal", "预算完成率处于合理区间（90%-105%），目标设定与执行较为匹配"
    return {"ok": True, "avg": avg, "level": lvl, "text": txt}
