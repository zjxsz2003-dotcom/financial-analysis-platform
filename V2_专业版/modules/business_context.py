"""
业务知识库 — V2
把「财务数字的波动」翻译成「业务上发生了什么」

设计原则（保持泛化）：
  * 档案按【股票代码】精确匹配，匹配不到则完全不显示任何公司特定内容，
    只给出通用行业变量清单 —— 换任何公司都不会串台
  * 所有业务事实带来源与期间标注，可追溯
  * 业务档案只做「解释与提示」，不参与任何指标计算，不污染数值口径
"""
from __future__ import annotations
from typing import Optional
import streamlit as st

from modules import finance_core as fc

_DASH = "—"


def _f(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):,.{dec}f}"


def _p(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):.{dec}f}"


def _sg(v, dec=1):
    return _DASH if v is None or v != v else f"{float(v):+,.{dec}f}"


# ════════════════════════════════════════════════════════════
# 公司业务档案库（按股票代码索引）
# ════════════════════════════════════════════════════════════
PROFILES = {
    "002475": {
        "name": "立讯精密",
        "alias": ["立讯", "LUXSHARE", "002475.SZ"],
        "industry": "消费电子 / 精密智造（申万：电子—消费电子—消费电子零部件及组装）",
        "positioning": (
            "全球领先的精密智造解决方案提供商。从消费电子连接器起家，"
            "通过「垂直一体化 + 连续并购」扩张为覆盖消费电子、通信及数据中心、汽车三大板块的"
            "零组件—模组—整机系统集成全栈供应商。核心客户为全球头部消费电子品牌（苹果）。"
        ),
        "business_model": (
            "代工/ODM-JDM 模式为主：收入由客户订单驱动、定价权偏弱、毛利率天然承压；"
            "增长主要靠【份额提升 + 品类扩张 + 并购并表】三条路径，"
            "因此收入高增长常伴随「毛利率低位 + 资本开支高企 + 营运资金占用上升」。"
        ),
        "segments": [
            {"name": "消费电子", "rev_2025": 2642.66, "share": 79.52, "growth": 13.37,
             "margin": 10.64, "margin_chg": 1.16,
             "desc": "声/光/电/散热/射频等精密零组件、模组与整机组装。AI 端侧硬件（AI 手机、AI PC、"
                     "智能眼镜/手表）普及驱动微型化与集成度升级，公司凭垂直一体化绑定头部品牌基本盘。",
             "driver": "份额提升 + 新品类（AI 眼镜等）价值量提升 + 闻泰 ODM 资产包并表"},
            {"name": "汽车电子", "rev_2025": 392.55, "share": 11.81, "growth": 185.34,
             "margin": 15.75, "margin_chg": -0.05,
             "desc": "整车线束、高低压及高速连接器、智能座舱、ADAS，并孵化底盘域控、后轮转向等部件。"
                     "按 2025 年收入计，全球汽车线束（PIMS）市场排名第四、中国大陆企业第一，份额约 7.6%。",
             "driver": "【外延】2025 年 7 月完成收购德国莱尼集团（Leoni）交割并表；"
                       "【内生】智能座舱/智驾域控在多品牌客户端导入"},
            {"name": "通讯及数据中心", "rev_2025": 245.68, "share": 7.39, "growth": 33.81,
             "margin": 18.40, "margin_chg": 2.00,
             "desc": "高速铜连接、光模块、热管理。为 ETH-X 超节点等 AI 算力基座提供互连方案，"
                     "800G/1.6T 光模块已小批量供货。三大板块中毛利率最高。",
             "driver": "AI 算力资本开支周期 + 高毛利产品占比提升"},
        ],
        "events": [
            {"date": "2025-07", "title": "完成收购德国莱尼集团（Leoni）交割并全面整合",
             "impact": "汽车业务营收占比由 5.12% 跃升至 11.81%，同比 +185.34%；"
                       "海外制造版图扩展至东南亚、欧洲、北非、美洲；"
                       "代价是营运资金占用上升、管理费用增加约 20 亿元、产生 4.8 亿元负商誉收益"},
            {"date": "2025 全年", "title": "收购闻泰 ODM 业务资产包",
             "impact": "扩充安卓系客户来源，是苹果占比下降的另一推手；同样带来并表收入与整合成本"},
            {"date": "2025 全年", "title": "资本开支 179.04 亿元（同比 +57.94 亿）",
             "impact": "前瞻性布局 AI 端侧与 AI 数据中心，用于设备技术升级、产品迭代与全球产能建设；"
                       "直接导致自由现金流承压"},
            {"date": "2025Q4", "title": "美元贬值造成较大汇兑损失",
             "impact": "财务费用同比激增 316.21% 至 10.88 亿元（其中利息费用 17.65 亿、同比 +3.02 亿）"},
            {"date": "2026-04", "title": "发布 2025 年报及 2026Q1 预告",
             "impact": "2025 营收 3323.44 亿（+23.64%）、归母净利 166.00 亿（+24.20%）；"
                       "2026Q1 预告归母净利 36.52–37.13 亿（同比 +20%~22%）"},
            {"date": "在推进", "title": "港股二次上市",
             "impact": "带来短期股权稀释预期，但可补充海外扩张所需资本"},
        ],
        "explanations": [
            {
                "signal": "cash_divergence",
                "title": "「利润涨、现金跌」背离",
                "cause": "经营现金流净额 173.25 亿元、同比 −36.11%，而营收 +23.64%、归母净利 +24.20%。"
                         "公司口径原因：业务规模增长导致备货库存增加；收购业务（莱尼、闻泰 ODM）"
                         "客户回款节奏变化与过往货款支付影响；经营性应付项目增加额减少。"
                         "前三季度经营现金流仅 34.78 亿元（同比 −47.89%），四季度集中回款才把全年拉回 173 亿。",
                "so_what": "利润的现金含量明显下降，若回款与库存周转不能在 1–2 个季度内恢复，"
                           "将持续消耗流动性并推高有息负债。",
                "verify": "关注 2026 中报的经营现金流是否回到与净利润匹配水平；"
                          "关注存货与应收周转天数是否继续走高。",
            },
            {
                "signal": "leverage_up",
                "title": "资产负债率与短债快速上升",
                "cause": "资产负债率由 2023 年 56.61% 升至 2025 年 66.07%（+3.91pp），"
                         "流动比率由 1.26 降至 1.11，短期借款由 353.13 亿升至 601.38 亿。"
                         "原因：业务规模增长带来的经营性负债增加 + 为并购与资本开支适度增加的有息负债。",
                "so_what": "公司口径利息保障倍数 19.85 倍、整体偿债能力仍稳定，"
                           "但货币资金对短期有息债务的覆盖已连续三年下滑，再融资频率上升、利率敏感性强。",
                "verify": "关注是否用长期资金替换短债、是否启动股权融资（含港股 IPO）。",
            },
            {
                "signal": "margin_low",
                "title": "毛利率长期低位（约 11%–12%）",
                "cause": "代工/组装模式决定：收入体量巨大但附加值集中在品牌方，"
                         "且消费电子板块毛利率仅 10.64%。2025 年整体毛利率 11.91%（+1.5pp）"
                         "主要来自高毛利的通讯及数据中心（18.40%，+2pp）占比提升与消费电子改善（+1.16pp）。",
                "so_what": "毛利率每 1pp 对应约 33 亿元净利润，是利润最敏感的杠杆；"
                           "但代工模式下毛利率上行空间有限，更现实的路径是「结构升级」而非「提价」。",
                "verify": "跟踪通讯与汽车板块收入占比是否继续提升（2025 年三大板块合计占比已突破 20%）。",
            },
            {
                "signal": "customer_concentration",
                "title": "单一大客户依赖正在缓解但未根本化解",
                "cause": "第一大客户（苹果）收入占比：2023 年 75.24% → 2024 年 70.74% → 2025 年 56.68%，"
                         "两年下降近 20 个百分点，主要靠收购 ODM 资产包、汽车与通信业务放量实现。"
                         "但第二大客户占比仅 2.86%，尚未形成真正的替代支柱。",
                "so_what": "客户结构改善是真实的，但「半壁江山仍系于单一客户」的格局未变，"
                           "一旦核心客户产品周期调整或订单份额被削减，业绩波动会非常剧烈。",
                "verify": "跟踪第一大客户占比能否继续降至 50% 以下、第二大客户能否培育起来。",
            },
            {
                "signal": "nonrecurring_high",
                "title": "非经常性损益占比偏高",
                "cause": "2025 年投资收益 67.64 亿元（+48.76%），含联营企业收益、理财收益 13.81 亿元、"
                         "远期外汇避险收益 10.98 亿元；另有收购莱尼产生 4.8 亿元负商誉计入营业外收入。"
                         "扣非归母净利 141.69 亿元（+21.16%）低于归母净利 166.00 亿元（+24.20%）。",
                "so_what": "归母净利增速被非经常项抬高，评估真实经营改善应以扣非口径为准。",
                "verify": "用扣非净利而非归母净利做同比与趋势判断。",
            },
            {
                "signal": "merger_integration",
                "title": "跨国并购整合风险",
                "cause": "公司历史上多次靠并购跨越（2011 年博硕科技/昆山联滔切入苹果链、2021 年立铠精密、"
                         "2025 年莱尼与闻泰资产）。并购目的是买产能、买客户、买时间，"
                         "但此轮赌注显著大于以往。过往印度闻泰项目曾暴露尽调不足之处。",
                "so_what": "商誉减值、跨文化管理效率损失、协同不及预期是三大潜在爆点。",
                "verify": "关注莱尼能否如期扭亏、商誉余额及其减值测试假设。",
            },
            {
                "signal": "geopolitics",
                "title": "地缘政治与关税",
                "cause": "外销占比 85.22%，已在近 30 个国家部署超 100 个生产基地。"
                         "美国对东南亚部分地区加征关税的潜在动作会直接推高越南、墨西哥工厂成本。",
                "so_what": "全球化产能既是护城河也是成本敞口；关税变动会侵蚀本已微薄的毛利率。",
                "verify": "跟踪关税政策、海外产能爬坡与客户「属地化交付」要求。",
            },
        ],
        "watch_list": [
            "莱尼（Leoni）整合进展与扭亏节奏",
            "800G/1.6T 光模块与 AI 算力订单放量节奏",
            "第一大客户占比能否降至 50% 以下",
            "经营现金流能否回到与净利润匹配的水平",
            "港股 IPO 进度与股权稀释幅度",
            "关税与海外产能成本",
            "商誉减值测试",
        ],
        "sources": [
            "立讯精密 2025 年年度报告（2026-04-14 披露）",
            "立讯精密 2026 年 4 月 16–20 日投资者关系活动记录表",
            "证券时报、中证网、中国网财经相关报道",
        ],
        "as_of": "2026-09",
    },
}

# 通用行业变量清单（未匹配公司档案时使用）
GENERIC_WATCH = [
    "下游需求周期与订单能见度",
    "主要原材料/零部件价格传导能力",
    "大客户集中度与议价能力",
    "产能利用率与资本开支回收期",
    "应收账款账龄与回款节奏",
    "存货结构与跌价风险",
    "融资成本与债务期限结构",
    "行业政策、关税与地缘风险",
]


# ════════════════════════════════════════════════════════════
# 匹配
# ════════════════════════════════════════════════════════════
def get_profile(code: str = "", name: str = "") -> Optional[dict]:
    """按股票代码优先、名称次之匹配业务档案"""
    from modules.data_loader import get_company_code, get_company_name
    code = str(code or get_company_code() or "").strip()
    name = str(name or get_company_name() or "").strip()
    for k, p in PROFILES.items():
        if code and (k == code or k == code.split(".")[0] or code.zfill(6) == k):
            return p
        if name and (name == p["name"] or name in p.get("alias", [])):
            return p
    return None


def has_profile() -> bool:
    return get_profile() is not None


# ════════════════════════════════════════════════════════════
# 财务现象 → 业务解释（规则触发）
# ════════════════════════════════════════════════════════════
def detect_signals(model: dict) -> list:
    """
    从计算结果中识别「需要业务解释」的异常现象，返回 signal 名称列表
    """
    sig = []
    if not model:
        return sig
    i = model["n"] - 1
    ocf = model["ocf"][i]
    ocf0 = model["ocf"][i - 1] if model["n"] >= 2 else None
    ni = model["net_profit"][i]
    ni0 = model["net_profit"][i - 1] if model["n"] >= 2 else None
    rev_g = model["rev_growth"][i]

    # 利润涨现金跌
    if None not in (ocf, ocf0, ni, ni0) and ocf0 and ni0:
        if (ocf - ocf0) / abs(ocf0) < -0.15 and (ni - ni0) / abs(ni0) > 0.05:
            sig.append("cash_divergence")

    # 杠杆抬升
    dr = fc._last(model["debt_ratio"])
    dr0 = fc._prev(model["debt_ratio"])
    if None not in (dr, dr0) and dr - dr0 > 2:
        sig.append("leverage_up")
    cr = fc._last(model["current_ratio"])
    if cr is not None and cr < 1.2:
        sig.append("leverage_up") if "leverage_up" not in sig else None

    # 毛利率低位
    gm = fc._last(model["gross_margin"])
    if gm is not None and gm < 15:
        sig.append("margin_low")

    # 客户集中度
    try:
        from modules.data_loader import get_extra
        ex = get_extra() or {}
        t1 = (ex.get("第一大客户占比") or [None])[-1]
        if t1 and t1 > 45:
            sig.append("customer_concentration")
    except Exception:
        pass

    # 非经常损益占比
    nr = fc._last(model["nonrecurring_ratio"])
    if nr is not None and abs(nr) > 5:
        sig.append("nonrecurring_high")

    return list(dict.fromkeys(sig))


def narrative(model: dict, profile: dict = None, only_detected: bool = True) -> list:
    """
    返回业务解读条目：[{title, cause, so_what, verify}]
    only_detected=True 时只输出被当前数据触发的条目
    """
    profile = profile or get_profile()
    if not profile:
        return []
    sigs = detect_signals(model) if only_detected else None
    out = []
    for e in profile.get("explanations", []):
        if only_detected and e["signal"] not in sigs:
            continue
        out.append(e)
    return out


def full_narrative(model: dict, profile: dict = None) -> list:
    return narrative(model, profile, only_detected=False)


# ════════════════════════════════════════════════════════════
# 渲染：业务视角面板
# ════════════════════════════════════════════════════════════
def render_panel(model: dict = None, profile: dict = None, show_events: bool = True):
    """完整业务画像面板（放在分析页面顶部）"""
    profile = profile or get_profile()
    if not profile:
        st.markdown(
            '<div class="note">当前公司<b>没有内置业务档案</b>。'
            '业务档案用于解释「财务数字背后的业务事件」（如并购、产能周期、客户结构变化），'
            '是可选增强项，不影响任何指标计算。'
            '如需为该公司建立档案，可在 <code>modules/business_context.py</code> 的 '
            '<code>PROFILES</code> 中按股票代码新增。</div>', unsafe_allow_html=True)
        st.markdown("**通用行业变量清单**（适用于任何公司，可逐项核查）：")
        st.markdown("　·　" + "　·　".join(GENERIC_WATCH))
        return

    st.markdown(
        f'<div class="insight" style="border-left-color:#1B4F8A;padding:15px 18px">'
        f'<span class="hd">业务画像｜{profile["name"]}　'
        f'<span style="font-weight:400;color:#7A8798;font-size:11px">{profile["industry"]}</span></span>'
        f'<div class="ln" style="margin:4px 0 8px">{profile["positioning"]}</div>'
        f'<div class="ln" style="color:#4A5568"><b style="color:#0F2B46">商业模式｜</b>'
        f'{profile["business_model"]}</div></div>', unsafe_allow_html=True)

    # 板块构成
    segs = profile.get("segments", [])
    if segs:
        st.markdown("**业务板块构成**")
        rows = []
        for s in segs:
            rows.append({"c": [
                s["name"],
                _f(s.get("rev_2025"), 2),
                _p(s.get("share"), 2),
                (f'{s["growth"]:+.2f}%' if s.get("growth") is not None else _DASH,
                 "pos" if (s.get("growth") or 0) >= 0 else "neg"),
                _p(s.get("margin"), 2),
                (_sg(s.get("margin_chg"), 2) + "pp" if s.get("margin_chg") is not None else _DASH,
                 "pos" if (s.get("margin_chg") or 0) >= 0 else "neg"),
                s.get("desc", ""),
            ], "t": "normal", "i": 0})
        from utils.tables import fin_table
        st.markdown(fin_table(
            ["板块", "收入(亿元)", "占比", "同比", "毛利率", "毛利率变动", "业务说明"], rows),
            unsafe_allow_html=True)
        for s in segs:
            st.caption(f"**{s['name']}** 增长驱动：{s.get('driver','—')}")

    # 关键事件
    if show_events:
        evs = profile.get("events", [])
        if evs:
            st.markdown("**影响财务的关键事件**")
            for e in evs:
                st.markdown(
                    f'<div class="note" style="border-left-color:#1B4F8A">'
                    f'<b>{e["date"]}　{e["title"]}</b><br>'
                    f'<span style="color:#4A5568">{e["impact"]}</span></div>',
                    unsafe_allow_html=True)

    # 财务现象 → 业务解释
    if model:
        narr = narrative(model, profile, only_detected=True)
        if narr:
            st.markdown("**财务现象的业务解释**（系统自动匹配当期数据触发）")
            for e in narr:
                st.markdown(
                    f'<div class="insight" style="border-left-color:#C0392B">'
                    f'<span class="hd">{e["title"]}</span>'
                    f'<div class="ln"><span class="k k2">成因｜</span>{e["cause"]}</div>'
                    f'<div class="ln"><span class="k k3">影响｜</span>{e["so_what"]}</div>'
                    f'<div class="ln"><span class="k k4">验证｜</span>{e["verify"]}</div>'
                    f'</div>', unsafe_allow_html=True)

    # 跟踪清单 + 来源
    wl = profile.get("watch_list", GENERIC_WATCH)
    st.markdown("**需持续跟踪的业务变量**")
    st.markdown("　·　".join(wl))
    srcs = profile.get("sources", [])
    if srcs:
        st.caption("资料来源：" + "；".join(srcs) + f"（截至 {profile.get('as_of','—')}）")


def render_brief(model: dict = None, profile: dict = None):
    """精简版：只显示定位 + 被触发的业务解释（嵌在页面顶部结论区下方）"""
    profile = profile or get_profile()
    if not profile:
        return
    narr = narrative(model, profile, only_detected=True) if model else []
    if not narr:
        return
    items = "".join(
        f'<div class="ln" style="margin:5px 0"><b style="color:#0F2B46">{e["title"]}</b>　'
        f'<span style="color:#4A5568">{e["cause"]}</span></div>' for e in narr[:3])
    st.markdown(
        f'<div class="insight" style="border-left-color:#2E7FD1;padding:13px 16px">'
        f'<span class="hd" style="font-size:12px;color:#7A8798;letter-spacing:1px">'
        f'业务视角｜为什么会出现这些数字</span>{items}</div>', unsafe_allow_html=True)
