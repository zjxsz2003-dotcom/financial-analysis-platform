"""
业财穿透分析 — V2
把「比率变化」翻译成「业务动因 → 财务后果 → 管理动作」
所有结论均由数据规则推导，不绑定具体公司
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from modules.data_loader import get_segments, get_extra
from modules import finance_core as fc

_DASH = "—"


def _f(v, dec=1, dash=_DASH):
    if v is None or v != v:
        return dash
    return f"{float(v):,.{dec}f}"


def _p(v, dec=1, dash=_DASH):
    if v is None or v != v:
        return dash
    return f"{float(v):.{dec}f}%"


def _sg(v, dec=1, dash=_DASH):
    if v is None or v != v:
        return dash
    return f"{float(v):+,.{dec}f}"


def _last(a):
    return fc._last(a)


def _prev(a):
    return fc._prev(a)


# ════════════════════════════════════════════════════════════
# 1. 业务板块
# ════════════════════════════════════════════════════════════
def segment_overview(model: dict) -> Optional[dict]:
    seg = get_segments()
    if len(seg) < 2:
        return None
    years = model["years"]
    n = model["n"]
    rows = []
    for name, d in seg.items():
        rev = [x if x is None or not (isinstance(x, float) and np.isnan(x)) else None for x in d.get("收入", [])]
        cost = [x if x is None or not (isinstance(x, float) and np.isnan(x)) else None for x in d.get("成本", [])]
        r1, r0 = _last(rev), _prev(rev)
        c1, c0 = _last(cost), _prev(cost)
        gp = None if (r1 is None or c1 is None) else r1 - c1
        gm = None if (gp is None or not r1) else gp / r1 * 100
        gm0 = None if (r0 is None or c0 is None or not r0) else (r0 - c0) / r0 * 100
        g = None if (r1 is None or r0 is None or not r0) else (r1 / r0 - 1) * 100
        tot = sum(v for v in [_last(seg[k].get("收入", [])) for k in seg] if v)
        share = r1 / tot * 100 if (r1 and tot) else None
        rows.append({
            "板块": name, "收入": r1, "收入_上期": r0, "增速": g, "毛利": gp,
            "毛利率": gm, "毛利率_上期": gm0, "毛利率变动": None if (gm is None or gm0 is None) else gm - gm0,
            "收入占比": share,
        })
    df = pd.DataFrame(rows).sort_values("收入", ascending=False, na_position="last")

    tot_rev = df["收入"].sum()
    tot_prev = df["收入_上期"].sum()
    fastest = df.loc[df["增速"].idxmax()] if df["增速"].notna().any() else None
    biggest = df.iloc[0]
    weakest = df.loc[df["增速"].idxmin()] if df["增速"].notna().any() else None
    low_margin = df[df["毛利率"] < df["毛利率"].median()] if df["毛利率"].notna().any() else pd.DataFrame()

    what = (f"本期营业总收入 {_f(tot_rev,1)} 亿元"
            + (f"，同比 {_sg((tot_rev/tot_prev-1)*100) if tot_prev else ''}%")
            + f"。{'、'.join(f'{r.板块}占{_p(r.收入占比,1)}' for r in df.itertuples())}；"
            + (f"增速最快的是 {fastest.板块}（{_sg(fastest.增速)}%），" if fastest is not None else "")
            + f"规模最大的是 {biggest.板块}（{_f(biggest.收入,1)} 亿元）。")

    why_parts = []
    if fastest is not None and biggest is not None:
        contrib = (fastest.收入 - fastest.收入_上期) / (tot_rev - tot_prev) * 100 if (tot_rev != tot_prev) else None
        if contrib is not None:
            why_parts.append(
                f"{fastest.板块} 贡献了本期收入增量的 {_p(contrib,1)}"
                f"（增量 {_f(fastest.收入 - fastest.收入_上期,1)} 亿元），是增长主引擎")
    if weakest is not None and weakest.增速 is not None and weakest.增速 < 0:
        why_parts.append(f"{weakest.板块} 收入 {_sg(weakest.增速)}%，处于收缩状态，需确认是需求走弱、价格竞争还是主动收缩")
    if not df["毛利率变动"].isna().all():
        up = df.loc[df["毛利率变动"].idxmax()]
        dn = df.loc[df["毛利率变动"].idxmin()]
        why_parts.append(
            f"毛利率方面 {up.板块} 提升 {_sg(up.毛利率变动,2)}pp，{dn.板块} 下降 {_sg(dn.毛利率变动,2)}pp，"
            f"说明盈利改善并非全业务普涨，而是结构性的")
    why = "；".join(why_parts) if why_parts else "各板块变动幅度接近，未出现明显结构性分化。"

    hhi = (df["收入占比"] / 100).pow(2).sum() if df["收入占比"].notna().any() else None
    sowhat_parts = []
    if hhi is not None:
        sowhat_parts.append(
            f"业务集中度 HHI={hhi:.3f}（{'>0.25 为高度集中' if hhi>0.25 else ('0.15-0.25 中等集中' if hhi>0.15 else '较分散')}），"
            f"单一板块波动会显著放大整体业绩波动")
    if not low_margin.empty:
        sowhat_parts.append(f"{'、'.join(low_margin['板块'].tolist())} 毛利率低于公司中位数，对整体毛利形成拖累")
    weighted = (df["毛利率"] * df["收入占比"] / 100).sum() if df["毛利率"].notna().any() else None
    if weighted is not None:
        sowhat_parts.append(f"收入加权毛利率 {_p(weighted,2)}，整体毛利池 {_f(df['毛利'].sum(),1)} 亿元")
    sowhat = "；".join(sowhat_parts) if sowhat_parts else "板块结构与毛利率均处于常态区间。"

    nowwhat = []
    if fastest is not None:
        nowwhat.append(f"① 资源向 {fastest.板块} 倾斜：保障产能、交付与研发投入，锁定增长红利")
    if weakest is not None and weakest.增速 is not None and weakest.增速 < 0:
        nowwhat.append(f"② 对 {weakest.板块} 做专项复盘：拆分量、价、客户三要素，判断是周期性还是结构性下滑")
    if not low_margin.empty:
        nowwhat.append(f"③ 对 {'、'.join(low_margin['板块'].tolist())} 启动成本对标：BOM 降本、良率提升、制程优化")
    nowwhat.append("④ 建立板块级月度毛利看板，把毛利率变动在「价格 / 成本 / 结构」三端归因到责任人")
    return {
        "df": df, "hhi": hhi, "weighted_margin": weighted, "total_rev": tot_rev,
        "insight": [("What", what), ("Why", why), ("SoWhat", sowhat),
                    ("NowWhat", " ".join(nowwhat))],
    }


# ════════════════════════════════════════════════════════════
# 2. 成本结构
# ════════════════════════════════════════════════════════════
def cost_structure(model: dict) -> dict:
    i = model["n"] - 1
    rev = _last(model["revenue"])
    cogs = _last(model["cogs"])
    items = {"营业成本": cogs, "税金及附加": _last(model["tax_surcharge"]),
             "销售费用": _last(model["sell"]), "管理费用": _last(model["admin"]),
             "研发费用": _last(model["rd"]), "财务费用": _last(model["fin"])}
    items = {k: v for k, v in items.items() if v is not None}
    total = sum(v for k, v in items.items() if k != "营业成本")

    # 弹性：成本/费用增速 vs 收入增速
    g_rev = _last(model["rev_growth"])
    elastic = {}
    for k in ("营业成本", "销售费用", "管理费用", "研发费用", "财务费用"):
        arr = {"营业成本": "cogs", "销售费用": "sell", "管理费用": "admin",
               "研发费用": "rd", "财务费用": "fin"}[k]
        g = None
        s = model[arr]
        v1, v0 = _last(s), _prev(s)
        if v1 is not None and v0 not in (None, 0):
            g = (v1 / v0 - 1) * 100
        elastic[k] = {"增速": g, "弹性": (g / g_rev) if (g is not None and g_rev) else None,
                      "占收入比": (v1 / rev * 100) if (v1 is not None and rev) else None}

    gm1, gm0 = _last(model["gross_margin"]), _prev(model["gross_margin"])
    d_gm = None if (gm1 is None or gm0 is None) else gm1 - gm0

    # 毛利率每变动 1pp 对净利润的影响
    sens = rev * 0.01 if rev else None

    what = (f"本期总成本费用 {_f(sum(v for v in items.values() if v is not None),1)} 亿元，"
            f"占收入 {_p(sum(v for v in items.values() if v is not None)/rev*100 if rev else None,1)}；"
            f"其中营业成本 {_f(cogs,1)} 亿元（占收入 {_p(cogs/rev*100 if rev else None,1)}），"
            f"期间费用合计 {_f(total,1)} 亿元（占收入 {_p(total/rev*100 if rev else None,1)}）。")

    parts = []
    el = {k: v for k, v in elastic.items() if v["弹性"] is not None}
    worst = max(el.items(), key=lambda kv: kv[1]["弹性"]) if el else None
    best = min(el.items(), key=lambda kv: kv[1]["弹性"]) if el else None
    if worst:
        parts.append(f"{worst[0]} 增速 {_sg(worst[1]['增速'])}%，收入增速弹性 {worst[1]['弹性']:.2f}"
                     + ("（>1，费用扩张快于收入，存在规模不经济）" if worst[1]["弹性"] > 1.15 else "（与收入基本同步）"))
    if best and best[0] != worst[0]:
        parts.append(f"{best[0]} 弹性 {best[1]['弹性']:.2f}，控制较好")
    if d_gm is not None:
        parts.append(f"毛利率 {_p(gm1,2)}（{_sg(d_gm,2)}pp）"
                     + ("，成本端压力大于售价端改善" if d_gm < 0 else "，售价/结构改善覆盖成本上升"))
    why = "；".join(parts) if parts else "成本费用变动幅度与收入基本匹配。"

    sowhat = (f"按当前收入规模，毛利率每变动 1pp 对应净利润约 {_f(sens,1)} 亿元；"
              f"期间费用率每上升 1pp 对应净利润约 {_f(rev*0.01 if rev else None,1)} 亿元。"
              f"因此成本端的微小改善具有明显的利润杠杆。")
    nowwhat = ("① 建立「成本率 - 费用率」双红线预算，按季度滚动监控；"
               "② 对弹性 >1.2 的费用科目启动零基预算复盘；"
               "③ 把毛利率变动拆到「售价 / 单位成本 / 产品结构」三端，明确归属部门；"
               "④ 对原材料占比高的品类建立价格联动与套期保值机制。")
    return {"items": items, "elastic": elastic, "sens": sens,
            "insight": [("What", what), ("Why", why), ("SoWhat", sowhat), ("NowWhat", nowwhat)]}


# ════════════════════════════════════════════════════════════
# 3. 费用效能
# ════════════════════════════════════════════════════════════
def expense_efficiency(model: dict) -> dict:
    rev = _last(model["revenue"])
    rows = []
    for k, sname in (("销售费用", "sell"), ("管理费用", "admin"),
                     ("研发费用", "rd"), ("财务费用", "fin")):
        v1, v0 = _last(model[sname]), _prev(model[sname])
        r1, r0 = _last(model["revenue"]), _prev(model["revenue"])
        ratio = v1 / r1 * 100 if (v1 is not None and r1) else None
        ratio0 = v0 / r0 * 100 if (v0 is not None and r0) else None
        g = (v1 / v0 - 1) * 100 if (v1 is not None and v0) else None
        gr = (r1 / r0 - 1) * 100 if (r1 is not None and r0) else None
        rows.append({
            "科目": k, "金额": v1, "费用率": ratio, "费用率_上期": ratio0,
            "费用率变动": None if (ratio is None or ratio0 is None) else ratio - ratio0,
            "费用增速": g, "收入增速": gr,
            "弹性": (g / gr) if (g is not None and gr) else None,
            "单位费用创收": (r1 / v1) if (v1 and r1) else None,
        })
    df = pd.DataFrame(rows)
    ok = df[df["弹性"].notna()]
    bad = ok[ok["弹性"] > 1.2]

    what = "；".join(f"{r.科目}率 {_p(r.费用率,2)}" for r in df.itertuples() if r.费用率 is not None)
    why = ("费用弹性（费用增速/收入增速）："
           + "；".join(f"{r.科目} {r.弹性:.2f}" for r in ok.itertuples())
           + ("。弹性 >1 表示费用扩张快于收入，规模效应未显现。"
              if (ok["弹性"] > 1).any() else "。全部小于 1，费用增长慢于收入，规模效应为正。"))
    sowhat = (f"合计期间费用率 {_p(df[df['科目']!='研发费用']['费用率'].sum(),2)}"
              f"（不含研发），每降低 1pp 可释放净利润约 {_f(rev*0.01 if rev else None,1)} 亿元。")
    if not bad.empty:
        sowhat += f" 其中 {'、'.join(bad['科目'].tolist())} 弹性偏高，是费用管控的重点。"
    nowwhat = ("① 对弹性 >1.2 的科目做零基预算；"
               "② 销售费用按「获客成本 / 客户生命周期价值」核算 ROI；"
               "③ 管理费用按人头与项目双维度拆解；"
               "④ 财务费用结合融资结构优化（置换高息负债、拉长久期）。")
    return {"df": df, "insight": [("What", what), ("Why", why),
                                  ("SoWhat", sowhat), ("NowWhat", nowwhat)]}


# ════════════════════════════════════════════════════════════
# 4. 研发投入
# ════════════════════════════════════════════════════════════
def rd_analysis(model: dict) -> Optional[dict]:
    if all(v is None for v in model["rd"]):
        return None
    rev = _last(model["revenue"])
    rd1, rd0 = _last(model["rd"]), _prev(model["rd"])
    ratio1 = _last(model["rd_ratio"])
    gm1, gm0 = _last(model["gross_margin"]), _prev(model["gross_margin"])
    ex = get_extra()
    cap = (ex.get("研发资本化率") or [None])[-1] if ex.get("研发资本化率") else None

    what = f"研发费用 {_f(rd1,1)} 亿元，占收入 {_p(ratio1,2)}" + (
        f"，同比 {_sg((rd1/rd0-1)*100) if rd0 else ''}%" if rd0 else "") + "。"
    why_parts = []
    if len(model["rd"]) >= 3 and len(model["gross_margin"]) >= 3:
        a = [v for v in model["rd_ratio"] if v is not None][-5:]
        b = [v for v in model["gross_margin"] if v is not None][-5:]
        if len(a) >= 3 and len(b) >= 3 and len(a) == len(b):
            corr = float(np.corrcoef(a, b)[0, 1])
            why_parts.append(
                f"研发费用率与毛利率近 {len(a)} 期相关系数 {corr:+.2f}"
                + ("（正相关，研发投入已体现在产品溢价上）" if corr > 0.3
                   else ("（弱相关，研发成果向毛利率的转化尚不明显）" if corr > -0.1 else "（负相关，需警惕投入产出错配）")))
    if rd0:
        why_parts.append(f"研发投入同比 {_sg((rd1/rd0-1)*100)}%，"
                         + ("快于收入增速，属于主动加码" if (rd1/rd0-1)*100 > (_last(model["rev_growth"]) or 0) else "慢于收入增速，投入强度相对收缩"))
    why = "；".join(why_parts) if why_parts else "研发投入强度基本稳定。"

    sowhat = f"研发费用每变动 1pp 费用率对应净利润约 {_f(rev*0.01 if rev else None,1)} 亿元。"
    if cap:
        sowhat += (f" 研发资本化率 {_p(cap,1)}，资本化部分当期不进费用，"
                   + ("比例偏高会虚增当期利润，需关注资本化政策的谨慎性。" if cap > 20 else "处于相对稳健水平。"))
    nowwhat = ("① 建立研发项目台账，按项目归集投入并与后续收入/毛利挂钩核算 ROI；"
               "② 区分「维持性研发」与「增长性研发」，分别设定投入红线；"
               "③ 关注研发资本化率变化，避免利润被资本化政策扰动；"
               "④ 用「新品收入占比」验证研发转化效率。")
    return {"rd": rd1, "ratio": ratio1, "cap": cap, "gm": gm1,
            "insight": [("What", what), ("Why", why), ("SoWhat", sowhat), ("NowWhat", nowwhat)]}


# ════════════════════════════════════════════════════════════
# 5. 应收账款质量
# ════════════════════════════════════════════════════════════
def ar_quality(model: dict) -> dict:
    ar1, ar0 = _last(model["ar"]), _prev(model["ar"])
    rev1, rev0 = _last(model["revenue"]), _prev(model["revenue"])
    dso1, dso0 = _last(model["dso"]), _prev(model["dso"])
    g_ar = (ar1 / ar0 - 1) * 100 if (ar1 is not None and ar0) else None
    g_rev = (rev1 / rev0 - 1) * 100 if (rev1 is not None and rev0) else None

    what = (f"应收账款 {_f(ar1,1)} 亿元，周转天数 DSO {_f(dso1,0)} 天"
            + (f"（上年 {_f(dso0,0)} 天，{_sg(dso1-dso0,0)} 天）" if dso0 is not None else "")
            + f"，占收入 {_p(ar1/rev1*100 if (ar1 and rev1) else None,1)}。")
    why = ""
    if g_ar is not None and g_rev is not None:
        gap = g_ar - g_rev
        why = (f"应收增速 {_sg(g_ar)}% vs 收入增速 {_sg(g_rev)}%，差 {_sg(gap)}pp——"
               + ("应收扩张快于收入，提示信用政策放宽、客户回款变慢或存在渠道压货；"
                  if gap > 3 else
                  ("基本同步，应收增长由业务规模驱动；" if abs(gap) <= 3 else
                   "应收增速低于收入增速，回款效率改善。")))
    ocf_ni = _last(model["ocf_to_ni"])
    why += f" 经营现金流/净利润 {_f(ocf_ni,2)}" + ("（利润含金量偏弱）。" if (ocf_ni or 0) < 0.8 else "（利润基本转化为现金）。")

    # 量化：DSO 每增加 10 天占用的资金
    per_day = (rev1 / 365) if rev1 else None
    occ = per_day * 10 if per_day else None
    sowhat = (f"按当前收入规模，DSO 每延长 10 天将额外占用资金约 {_f(occ,1)} 亿元"
              f"（按 5% 资金成本年化约 {_f(occ*0.05 if occ else None,2)} 亿元利息）；"
              f"若 DSO 恶化至 {_f((dso1 or 0)+30,0)} 天，占用将再增加约 {_f(occ*3 if occ else None,1)} 亿元。")
    nowwhat = ("① 建立客户信用分级与授信额度模型，按账龄设置预警阈值；"
               "② 对超 90 天应收启动专人催收并与销售提成挂钩；"
               "③ 评估应收账款保理/无追索贴现，权衡成本与现金回流；"
               "④ 将 DSO 纳入销售团队考核，避免为冲收入放宽账期。")
    return {"ar": ar1, "dso": dso1, "dso0": dso0, "g_ar": g_ar, "g_rev": g_rev,
            "occ": occ, "insight": [("What", what), ("Why", why),
                                    ("SoWhat", sowhat), ("NowWhat", nowwhat)]}


# ════════════════════════════════════════════════════════════
# 6. 存货质量
# ════════════════════════════════════════════════════════════
def inventory_quality(model: dict) -> dict:
    inv1, inv0 = _last(model["inv"]), _prev(model["inv"])
    cogs1, cogs0 = _last(model["cogs"]), _prev(model["cogs"])
    dio1, dio0 = _last(model["dio"]), _prev(model["dio"])
    g_inv = (inv1 / inv0 - 1) * 100 if (inv1 is not None and inv0) else None
    g_cogs = (cogs1 / cogs0 - 1) * 100 if (cogs1 is not None and cogs0) else None
    assets = _last(model["assets"])

    what = (f"存货 {_f(inv1,1)} 亿元（占总资产 {_p(inv1/assets*100 if (inv1 and assets) else None,1)}），"
            f"周转天数 DIO {_f(dio1,0)} 天"
            + (f"（上年 {_f(dio0,0)} 天，{_sg(dio1-dio0,0)} 天）" if dio0 is not None else "") + "。")
    why = ""
    if g_inv is not None and g_cogs is not None:
        gap = g_inv - g_cogs
        why = (f"存货增速 {_sg(g_inv)}% vs 营业成本增速 {_sg(g_cogs)}%，差 {_sg(gap)}pp——"
               + ("存货扩张快于销售，需区分战略备货与滞销积压；"
                  if gap > 3 else
                  ("基本同步，备货节奏与销售匹配；" if abs(gap) <= 3 else "库存增速低于成本增速，去库存见效。")))
    turn1, turn0 = _last(model["inv_turnover"]), _prev(model["inv_turnover"])
    why += f" 存货周转率 {_f(turn1,2)} 次" + (f"（上年 {_f(turn0,2)} 次）" if turn0 is not None else "") + "。"

    loss = inv1 * 0.03 if inv1 else None
    sowhat = (f"在当前 {_f(dio1,0)} 天库龄下，若 3% 的存货需计提跌价，将影响利润约 {_f(loss,1)} 亿元；"
              f"DIO 每增加 10 天额外占用资金约 {_f(cogs1/365*10 if cogs1 else None,1)} 亿元。")
    nowwhat = ("① 建立库龄看板（<90 天 / 90-180 天 / >180 天）并按品类设安全库存；"
               "② 对长库龄物料制定专项消化计划（折价、替代、返修）；"
               "③ 推动供应商寄售 VMI 与 JIT 配送，降低自有库存；"
               "④ 将存货周转纳入供应链考核，与采购批量决策联动。")
    return {"inv": inv1, "dio": dio1, "dio0": dio0, "g_inv": g_inv, "g_cogs": g_cogs,
            "loss": loss, "insight": [("What", what), ("Why", why),
                                      ("SoWhat", sowhat), ("NowWhat", nowwhat)]}


# ════════════════════════════════════════════════════════════
# 7. 营运资本 / 现金转换周期
# ════════════════════════════════════════════════════════════
def working_capital(model: dict) -> dict:
    dso1, dio1, dpo1 = _last(model["dso"]), _last(model["dio"]), _last(model["dpo"])
    ccc1, ccc0 = _last(model["ccc"]), _prev(model["ccc"])
    rev = _last(model["revenue"])
    cogs = _last(model["cogs"])
    per_day_rev = rev / 365 if rev else None
    per_day_cogs = cogs / 365 if cogs else None

    what = (f"现金转换周期 CCC = {_f(ccc1,0)} 天"
            + (f"（上年 {_f(ccc0,0)} 天，{_sg(ccc1-ccc0,0)} 天）" if ccc0 is not None else "")
            + f"；其中 DSO {_f(dso1,0)} 天 + DIO {_f(dio1,0)} 天 - DPO {_f(dpo1,0)} 天。")
    parts = []
    if ccc0 is not None:
        parts.append(f"CCC {'延长' if ccc1 > ccc0 else '缩短'} {abs(round(ccc1-ccc0))} 天，"
                     + ("意味着营运资本占用增加，现金回流变慢" if ccc1 > ccc0 else "营运资本效率改善，现金回流加快"))
    if dpo1 is not None and dso1 is not None:
        parts.append(f"对上游的账期（DPO {_f(dpo1,0)} 天）"
                     + ("长于" if dpo1 > dso1 else "短于") +
                     f"对下游的账期（DSO {_f(dso1,0)} 天），"
                     + ("公司在产业链中处于占款地位，议价能力较强" if dpo1 > dso1 else "公司需先垫资再回款，处于被占款地位"))
    why = "；".join(parts)

    release = (per_day_rev + per_day_cogs) * 10 if (per_day_rev and per_day_cogs) else None
    neg_note = ("　<b>CCC 为负</b>说明对上游的付款账期长于「应收+存货」的周转周期，"
                "营运资本实际上由供应商提供，公司在产业链中处于占款地位；"
                "但一旦上游收紧账期，现金压力会立刻显现。"
                if (ccc1 or 0) < 0 else "")
    sowhat = (f"CCC 每缩短 10 天，可释放营运资金约 {_f(release,1)} 亿元"
              f"（应收端 {_f(per_day_rev*10 if per_day_rev else None,1)} 亿 + 存货端 {_f(per_day_cogs*10 if per_day_cogs else None,1)} 亿）；"
              f"反之每延长 10 天需额外融资同额资金。{neg_note}")
    nowwhat = ("① 把 CCC 拆解到事业部与产品线，明确各端责任；"
               "② 应收端推行预收/分期收款，缩短账期；"
               "③ 存货端推行按需生产与 VMI；"
               "④ 应付端在不损害供应商关系的前提下争取更长账期与票据结算。")
    return {"ccc": ccc1, "ccc0": ccc0, "dso": dso1, "dio": dio1, "dpo": dpo1,
            "release": release,
            "insight": [("What", what), ("Why", why), ("SoWhat", sowhat), ("NowWhat", nowwhat)]}


# ════════════════════════════════════════════════════════════
# 8. 客户 / 供应商集中度（可选数据）
# ════════════════════════════════════════════════════════════
def concentration() -> Optional[dict]:
    ex = get_extra()
    top5 = (ex.get("前五大客户占比") or [None])[-1]
    top1 = (ex.get("第一大客户占比") or [None])[-1]
    sup5 = (ex.get("前五大供应商占比") or [None])[-1]
    if top5 is None and top1 is None and sup5 is None:
        return None
    parts = []
    if top5 is not None:
        parts.append(f"前五大客户收入占比 {_p(top5,1)}")
    if top1 is not None:
        parts.append(f"第一大客户占比 {_p(top1,1)}")
    if sup5 is not None:
        parts.append(f"前五大供应商采购占比 {_p(sup5,1)}")
    what = "；".join(parts) + "。"

    hhi = None
    if top5 is not None and top1 is not None:
        # 粗略 HHI：第一大客户 + 其余四家平均分配
        rest = (top5 - top1) / 4
        hhi = ((top1 / 100) ** 2 + 4 * (rest / 100) ** 2) if rest > 0 else (top5 / 100) ** 2
    lvl = None
    if top5 is not None:
        lvl = "高度集中（单一客户风险显著）" if top5 > 70 else (
            "中等集中" if top5 > 45 else "较为分散")
    why = (f"客户集中度定位为{lvl or '—'}"
           + (f"；估算 HHI 约 {hhi:.3f}（>0.25 属高度集中）" if hhi else "") + "。")
    sowhat = ("高集中度意味着：① 单一客户订单波动会直接冲击收入；"
              "② 议价权偏弱，容易被压价与延长账期；"
              "③ 若客户发生经营或合规风险，冲击具有突发性。")
    nowwhat = ("① 制定客户结构优化目标（如 Top1 占比逐年下降 3-5pp）；"
               "② 拓展第二增长曲线与新行业客户，降低单一依赖；"
               "③ 对大客户建立经营状况持续跟踪机制；"
               "④ 在合同层面争取更长订单可见度与价格调整条款。")
    return {"top5": top5, "top1": top1, "sup5": sup5, "hhi": hhi, "level": lvl,
            "insight": [("What", what), ("Why", why), ("SoWhat", sowhat), ("NowWhat", nowwhat)]}
