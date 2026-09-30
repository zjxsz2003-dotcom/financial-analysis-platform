"""
各页面「核心结论」生成器
把本页最关键的 3–5 条发现写成一段可读的文字，放在页面最顶部
"""
from __future__ import annotations
from typing import Optional
import numpy as np

from modules import finance_core as fc
from modules.kpi import snapshot, alerts
from modules import risk_analysis as ra
from modules import business_context as bc
from config import C

_DASH = "—"


def _f(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):,.{dec}f}"


def _p(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):.{dec}f}%"


def _sg(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):+,.{dec}f}"


def trend_word(v, good_up=True, hi=3.0, lo=-3.0):
    if v is None:
        return "变动不大"
    if good_up:
        return "明显改善" if v > hi else ("小幅改善" if v > 0 else
                                         ("小幅走弱" if v > lo else "明显走弱"))
    return "明显改善" if v < -hi else ("小幅改善" if v < 0 else
                                      ("小幅走弱" if v < -lo else "明显走弱"))


# ════════════════════════════════════════════════════════════
# 0 / 首页
# ════════════════════════════════════════════════════════════
def _cash_verdict(model):
    """
    利润含金量的综合判断：不仅看 OCF/NI 的绝对水平，
    还要看「现金流与利润的变动方向是否背离」——后者往往更早暴露问题
    """
    i = model["n"] - 1
    ocf, ni = fc._last(model["ocf"]), fc._last(model["net_profit"])
    ocf0 = model["ocf"][i - 1] if model["n"] >= 2 else None
    ni0 = model["net_profit"][i - 1] if model["n"] >= 2 else None
    ratio = fc._last(model["ocf_to_ni"])
    if None in (ocf, ocf0, ni, ni0) or not ocf0 or not ni0:
        return ratio, "neutral", ""
    g_ocf = (ocf - ocf0) / abs(ocf0) * 100
    g_ni = (ni - ni0) / abs(ni0) * 100
    diverge = g_ocf < -15 and g_ni > 5
    if diverge:
        return ratio, "bad", (
            f"OCF/净利润 {_f(ratio,2)} 看似达标，但经营现金流同比 {_sg(g_ocf)}% "
            f"而净利润同比 {_sg(g_ni)}%，<b>现金流与利润明显背离</b>——"
            f"这正是比静态比率更早的危险信号。")
    if (ratio or 0) < 0.8:
        return ratio, "bad", (f"OCF/净利润 {_f(ratio,2)} 低于 0.8，"
                              f"利润未能充分转化为现金，需核查应收回款与存货占用。")
    return ratio, "good", (f"OCF/净利润 {_f(ratio,2)}，利润基本转化为现金，含金量良好。")


def summary_home(model, snap, rs, health) -> tuple:
    i = model["n"] - 1
    rev = fc._last(model["revenue"])
    g_rev = fc._last(model["rev_growth"])
    g_np = fc._last(model["np_growth"])
    roe = fc._last(model["roe"])
    gm = fc._last(model["gross_margin"])
    ocf_ni = fc._last(model["ocf_to_ni"])
    al = alerts(snap)
    lv, stt = ra.risk_level(rs["total"])
    top = max(rs["dims"].items(), key=lambda kv: kv[1]["score"] or 0)

    if (g_np or 0) > (g_rev or 0):
        quality = (f"净利润增速（{_p(g_np)}）快于收入增速（{_p(g_rev)}），"
                   f"说明<b>盈利能力在提升，增长是有质量的</b>。")
    else:
        quality = (f"净利润增速（{_p(g_np)}）慢于收入增速（{_p(g_rev)}），"
                   f"存在<b>「增收不增利」</b>的压力，需从毛利率与费用两端找原因。")

    headline = (
        f"{model['years'][-1]} 年营业收入 {_f(rev)} 亿元（{_sg(g_rev)}%），"
        f"净利润 {_f(fc._last(model['net_profit']))} 亿元（{_sg(g_np)}%），"
        f"ROE {_p(roe,2)}、毛利率 {_p(gm,2)}。"
        f"综合健康度 <b>{health:.0f} 分</b>，财务风险 <b>{lv}</b>（{_f(rs['total'],0)} 分）。"
    )
    _, cash_state, cash_txt = _cash_verdict(model)
    bullets = [
        ("增长与盈利", quality),
        ("利润含金量", cash_txt),
        ("最大风险敞口", f"<b>{top[0]}</b> 得分 {_f(top[1]['score'],0)} 分，"
                         f"是当前最需要优先处理的风险维度。"),
    ]
    if al:
        bullets.append(("预警信号",
                        f"共 {len(al)} 项指标触发预警，其中 "
                        + "、".join(f"{a['name']} {_f(a['value'], a['dec'])}{a['unit']}"
                                   for a in al[:3])
                        + (" 等。" if len(al) > 3 else "。")))
    else:
        bullets.append(("预警信号", "本期全部监控指标均在阈值安全区间内。"))
    return headline, bullets, ("d" if (rs["total"] or 0) >= 62 else
                               ("w" if (rs["total"] or 0) >= 45 else "g"))


# ════════════════════════════════════════════════════════════
# 1 / 经营全景
# ════════════════════════════════════════════════════════════
def summary_overview(model, snap) -> tuple:
    roe0, roe1 = model["roe"][0], fc._last(model["roe"])
    dp = fc.dupont_decompose(model, 0, model["n"] - 1)
    main = max(dp, key=lambda x: abs(x[1])) if dp else None
    weak = min(dp, key=lambda x: x[1]) if dp else None
    profit_side = sum(x[1] for x in dp[:3]) if dp else None
    turn_side = sum(x[1] for x in dp[3:]) if dp else None

    headline = (f"ROE 从 {_p(roe0,2)} 变动至 {_p(roe1,2)}"
                f"（{_sg((roe1 or 0)-(roe0 or 0),2," pp".strip())}），"
                f"按五因素连环替代法分解，"
                + (f"最主要的驱动因素是 <b>{main[0]}</b>（贡献 {_sg(main[1],2)}pp）。"
                   if main else "可用数据不足。"))
    bullets = []
    if profit_side is not None:
        src = "利润率端（产品竞争力/成本）" if abs(profit_side) >= abs(turn_side) else "周转与杠杆端"
        bullets.append(("回报来源",
                        f"利润率类三因素合计贡献 {_sg(profit_side,2)}pp，"
                        f"周转+杠杆合计贡献 {_sg(turn_side,2)}pp——"
                        f"ROE 变化主要来自<b>{src}</b>。"))
    if weak:
        bullets.append(("最弱一环", f"<b>{weak[0]}</b> 贡献 {_sg(weak[1],2)}pp，是拖累项。"))
    ato = fc._last(model["asset_turnover"])
    ato0 = model["asset_turnover"][0] if model["asset_turnover"] else None
    bullets.append(("资产效率",
                    f"总资产周转率 {_f(ato,2)} 次"
                    + (f"（{model['years'][0]} 年 {_f(ato0,2)} 次，" if ato0 else "（")
                    + f"{trend_word((ato or 0)-(ato0 or 0) if ato0 else None)}）"
                    + ("，资产扩张快于收入，需关注新增产能的利用率。"
                       if ato0 and ato and ato < ato0 else "。")))
    dr = fc._last(model["debt_ratio"])
    dr0 = model["debt_ratio"][0] if model["debt_ratio"] else None
    bullets.append(("资本结构",
                    f"资产负债率 {_p(dr)}"
                    + (f"（{model['years'][0]} 年 {_p(dr0)}，{_sg(dr-dr0)}pp）" if dr0 else "")
                    + "，杠杆变化直接影响 ROE 与财务弹性。"))
    return headline, bullets, ""


# ════════════════════════════════════════════════════════════
# 2 / 盈利质量与业财穿透
# ════════════════════════════════════════════════════════════
def summary_earnings(model, snap) -> tuple:
    eq = fc.earnings_quality_score(model)
    cb = fc.cash_bridge(model)
    ocf_ni = fc._last(model["ocf_to_ni"])
    ccc = fc._last(model["ccc"])
    ccc0 = fc._prev(model["ccc"])
    level = "良好" if (eq["score"] or 0) >= 70 else ("一般" if (eq["score"] or 0) >= 50 else "偏弱")

    headline = (f"盈利质量 <b>{level}</b>（{_f(eq['score'],0)} 分）："
                f"净利润 {_f(cb['净利润'])} 亿元，经营现金流 {_f(cb['经营现金流'])} 亿元"
                f"（OCF/净利润 {_f(ocf_ni,2)}），自由现金流 {_f(cb['自由现金流'])} 亿元。")
    _, cash_state, cash_txt = _cash_verdict(model)
    cb_txt = (f"经营现金流与净利润出现背离：营运资本变动 {_sg(cb['营运资本变动'])} 亿元"
              f"是主要缺口，需核查应收回款与存货备货。"
              if cash_state == "bad" else
              f"利润基本转化为现金，营运资本对现金的占用处于可接受水平。")
    bullets = [
        ("现金转化", f"{cash_txt}　{cb_txt}" if cash_state == "bad" else cash_txt),
        ("营运资本", f"现金转换周期 {_f(ccc,0)} 天"
                     + (f"（上年 {_f(ccc0,0)} 天，{_sg((ccc or 0)-(ccc0 or 0),0)} 天）" if ccc0 is not None else "")
                     + ("；CCC 为负说明对上游的账期长于自身周转周期，"
                        "公司在产业链中处于<b>占用上游资金</b>的地位。"
                        if (ccc or 0) < 0 else "")
                     + f"；按当前规模，CCC 每缩短 10 天可释放营运资金约 "
                       f"{_f(fc.wc_release(model, 10)['净释放'] if fc.wc_release(model,10) else None)} 亿元。"),
    ]
    so = None
    try:
        from modules import business_deep as bd
        so = bd.segment_overview(model)
    except Exception:
        pass
    if so:
        df = so["df"]
        fast = df.loc[df["增速"].idxmax()] if df["增速"].notna().any() else None
        hi = df.loc[df["毛利率"].idxmax()] if df["毛利率"].notna().any() else None
        bullets.append(("板块结构",
                        (f"增速最快的是 <b>{fast.板块}</b>（{_sg(fast.增速)}%），"
                         if fast is not None else "")
                        + (f"毛利率最高的是 <b>{hi.板块}</b>（{_p(hi.毛利率,2)}）；"
                           if hi is not None else "")
                        + f"业务集中度 HHI {so['hhi']:.3f}。"))
        mb = fc.margin_bridge(model)
        if mb:
            leader = "结构效应" if abs(mb["mix"]) >= abs(mb["price"]) else "毛利率效应"
            bullets.append(("毛利率归因",
                            f"毛利率变动 {_sg(mb['total'],2)}pp 中，结构效应 {_sg(mb['mix'],2)}pp、"
                            f"毛利率效应 {_sg(mb['price'],2)}pp，"
                            f"主要由<b>{leader}</b>驱动。"))
    else:
        bullets.append(("板块结构", "未上传分部数据，板块级归因暂不可用——"
                                    "可在「数据导入 → 补充经营数据」中补充后自动启用。"))
    return headline, bullets, ("w" if (eq["score"] or 0) < 50 else "")


# ════════════════════════════════════════════════════════════
# 3 / 预算偏差
# ════════════════════════════════════════════════════════════
def summary_budget(model, bv, pb, rf) -> tuple:
    rev = bv["收入"].get("合计", {})
    npi = bv["利润"].get("净利润", {})
    headline = (f"收入预算完成率 <b>{_p(rev.get('完成率'),1)}</b>"
                f"（预算 {_f(rev.get('预算'),0)} 亿 / 实际 {_f(rev.get('实际'),0)} 亿），"
                f"净利润预算完成率 <b>{_p(npi.get('完成率'),1)}</b>"
                f"（{_f(npi.get('偏差'))} 亿偏差）。")
    bullets = []
    if pb:
        items = [("收入规模", pb["vol"]), ("毛利率", pb["margin"]),
                 ("期间费用", pb["fee"]), ("税项及其他", pb["other"])]
        main = max(items, key=lambda x: abs(x[1]))
        kind_map = {"收入规模": "销量 / 订单预测偏差",
                    "毛利率": "定价与单位成本（单位经济性）",
                    "期间费用": "费用管控",
                    "税项及其他": "税负、营业外收支与投资收益等"}
        bullets.append(("偏差主因",
                        f"净利润偏差 {_sg(pb['total'])} 亿元中，"
                        f"<b>{main[0]}效应</b>贡献 {_sg(main[1])} 亿元，"
                        f"指向的是<b>{kind_map[main[0]]}</b>问题。"))
    if rf["gap_revenue"] is not None:
        if rf["gap_revenue"] > 0:
            bullets.append(("达成压力",
                            f"按当前进度外推全年 {_f(rf['fc_revenue'],0)} 亿元，"
                            f"距预算还差 {_f(rf['gap_revenue'],0)} 亿元；"
                            + (f"剩余 {rf['remain_months']} 个月月均需从 "
                               f"{_f(rf['cur_monthly'],1)} 亿提升至 {_f(rf['need_monthly'],1)} 亿"
                               f"（提速 {_p(rf['speedup'],1)}）。"
                               if rf["speedup"] and rf["speedup"] > 0 else "")))
        else:
            bullets.append(("达成压力",
                            f"按当前进度外推全年 {_f(rf['fc_revenue'],0)} 亿元，"
                            f"已超预算 {_f(-rf['gap_revenue'],0)} 亿元，"
                            f"可考虑上调目标或把增量转为利润。"))
    return headline, bullets, ("d" if (npi.get("偏差率") or 0) < -10 else
                               ("w" if (npi.get("偏差率") or 0) < 0 else "g"))


# ════════════════════════════════════════════════════════════
# 4 / 风险
# ════════════════════════════════════════════════════════════
def summary_risk(model, rs, az, lp) -> tuple:
    lv, stt = ra.risk_level(rs["total"])
    top = max(rs["dims"].items(), key=lambda kv: kv[1]["score"] or 0)
    safe = min(rs["dims"].items(), key=lambda kv: kv[1]["score"] if kv[1]["score"] is not None else 999)
    headline = (f"综合风险 <b>{_f(rs['total'],0)} 分（{lv}）</b>；"
                f"六大维度中 <b>{top[0]}</b> 最高（{_f(top[1]['score'],0)} 分），"
                f"<b>{safe[0]}</b> 最低（{_f(safe[1]['score'],0)} 分）。")
    bullets = [
        ("流动性", f"货币资金 {_f(lp['cash'])} 亿元 vs 短期有息负债 {_f(lp['short_total'])} 亿元，"
                   f"现金/短债 {_f(lp['cover_short'],2)} 倍"
                   + ("（低于 1.5 倍的安全线，存在再融资压力）。"
                      if (lp["cover_short"] or 0) < 1.5 else "（处于安全区间）。")),
        ("现金流", f"经营现金流 {_f(lp['ocf'])} 亿元、资本开支 {_f(lp['capex'])} 亿元、"
                   f"自由现金流 {_f(lp['fcf'])} 亿元"
                   + ("（自由现金流为负，扩张依赖外部融资）。" if (lp["fcf"] or 0) < 0 else "。")),
    ]
    if az:
        bullets.append(("破产风险", f"Altman Z = {_f(az['z'],2)}，处于<b>{az['zone'][0]}</b>；"
                                    f"私营口径 Z′ = {_f(az['zp'],2)}，处于{az['zone_p'][0]}。"))
    carry = (lp["ocf"] or 0) - (lp["capex"] or 0)
    if carry < 0:
        bullets.append(("再融资依赖",
                        f"经营现金流扣除资本开支后为 {_f(carry)} 亿元，"
                        f"缺口需靠筹资活动弥补（本期筹资净额 {_f(model['fcf_fin'][-1])} 亿元），"
                        f"对融资环境的敏感度上升。"))
    return headline, bullets, ("d" if (rs["total"] or 0) >= 62 else
                               ("w" if (rs["total"] or 0) >= 45 else "g"))


# ════════════════════════════════════════════════════════════
# 5 / 战略
# ════════════════════════════════════════════════════════════
def summary_strategy(prog, ol, model) -> tuple:
    n_d = sum(1 for t in prog if t["status"] == "danger")
    n_w = sum(1 for t in prog if t["status"] == "warning")
    n_ok = sum(1 for t in prog if t["status"] == "normal")
    worst = None
    for t in prog:
        if t["status"] in ("danger", "warning") and (worst is None or t["progress"] < worst["progress"]):
            worst = t
    headline = (f"共 {len(prog)} 项战略目标：<b>{n_ok} 项进度正常</b>、{n_w} 项略落后、{n_d} 项严重落后。"
                + (f"最紧迫的是「{worst['name']}」（完成率 {_p(worst['progress'],1)}）。"
                   if worst else "全部目标进度符合预期。"))
    bullets = []
    if worst:
        tree = worst.get("kpi_tree", {}) or {}
        if tree:
            from modules import strategy as stg
            df = stg.kpi_tree_gap(worst)
            if not df.empty:
                bullets.append(("制约环节",
                                f"「{worst['name']}」的最大制约项是 <b>{df.iloc[0]['子指标']}</b>"
                                f"（缺口 {_f(df.iloc[0]['缺口'],2)}，"
                                f"加权缺口贡献 {_f(df.iloc[0]['加权缺口贡献'],3)}）。"))
    if ol.get("ok"):
        bullets.append(("盈亏平衡",
                        f"边际贡献率 {_p(ol['cmr'],2)}，固定成本约 {_f(ol['fixed'],1)} 亿元，"
                        + (f"盈亏平衡收入 {_f(ol['bep'],1)} 亿元，"
                           f"安全边际 <b>{_p(ol['safety'],1)}</b>；"
                           if ol["bep"] else "")
                        + f"总杠杆 DTL {_f(ol['dtl'],2)}，"
                        + ("业绩对收入波动的放大效应显著。" if (ol["dtl"] or 0) > 3 else "杠杆温和。")))
    return headline, bullets, ("d" if n_d else ("w" if n_w else "g"))


# ════════════════════════════════════════════════════════════
# 6 / 行业对标
# ════════════════════════════════════════════════════════════
def summary_industry(snap, summ, industry) -> tuple:
    headline = (f"以「{industry}」为基准，可比指标中 "
                f"<b>{summ['n_better']} 项优于基准</b>、<b>{summ['n_worse']} 项低于基准</b>。")
    bullets = []
    if summ["better"]:
        bullets.append(("优势项", "、".join(
            f"{n}（相对基准 {_p(d,1)}）" for n, d, u in summ["better"][:3])))
    if summ["worse"]:
        bullets.append(("短板项", "、".join(
            f"{n}（{_sg(d,2)}）" for n, d, u in summ["worse"][:3])))
    return headline, bullets, ("w" if summ["n_worse"] > summ["n_better"] else "g")


# ════════════════════════════════════════════════════════════
# 7 / 报告
# ════════════════════════════════════════════════════════════
def summary_report(rep) -> tuple:
    headline = f"《{rep['title']}》已生成，共 {len(rep['sections'])} 个章节，覆盖经营、盈利质量、营运、预算、风险与战略。"
    bullets = [
        ("核心结论", f"综合风险 {_f(rep['risk_score'],0)} 分（{rep['risk_level']}），"
                     f"触发预警 {len(rep['alerts'])} 项。"),
        ("章节", "、".join(s["h"] for s in rep["sections"][:6]) + " 等。"),
    ]
    return headline, bullets, ""
