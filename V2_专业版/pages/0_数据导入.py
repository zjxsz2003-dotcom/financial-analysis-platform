"""
数据导入 — V2
四步：加载报表 → 数据质量诊断 → 补充经营数据 → 报表预览
支持 CSMAR 标准格式与简版表格（年份×科目）
"""
import os
import io
import numpy as np
import pandas as pd
import streamlit as st

from utils.shell import init
from utils import ui
from utils import tables as T
from modules import parser
from modules import data_loader as dl
from modules import quality
from config import C, REPORT_LAYOUT, ITEM_ALIASES

init("数据导入", "📥", need_data=False, step=0)

st.markdown(
    '<div class="page-head"><div class="t">📥 数据导入与质量诊断</div>'
    '<div class="s">支持 CSMAR 标准导出与简版报表（首列年份 / 首列科目）；'
    '分部、客户集中度等为可选补充项，缺失时相关分析自动降级</div></div>',
    unsafe_allow_html=True)

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "data", "立讯精密财务报表")


# ════════════════════════════════════════════════════════════
# 报表渲染（会企标准格式）
# ════════════════════════════════════════════════════════════
def _v(row, key):
    try:
        v = row.get(key)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        return float(v)
    except Exception:
        return None


def _rows(items, df, years, dec=1):
    out = []
    for tp, label, key in items:
        cells = [label]
        if tp == "G" or key is None:
            cells += [""] * len(years)
        else:
            for y in years:
                r = df[df["年份"] == y]
                val = _v(r.iloc[0], key) if not r.empty else None
                cells.append(T.num(val, dec) if val is not None else "—")
        out.append({"c": cells, "t": {"G": "grp", "D": "normal", "S": "sub",
                                      "T": "tot"}.get(tp, "normal"),
                    "i": 0 if tp in ("G",) else 1})
    return out


def render_balance(bs: pd.DataFrame):
    years = [int(y) for y in bs["年份"]]
    lay = REPORT_LAYOUT["资产负债表"]
    st.markdown(f'<div class="sec"><span class="bar"></span>'
                f'<span class="t">{lay["title"]}</span>'
                f'<span class="d">单位：亿元</span></div>', unsafe_allow_html=True)
    ca, cb = st.columns(2)
    with ca:
        st.markdown(T.fin_table([lay["left_title"]] + [f"{y}年" for y in years],
                                _rows(lay["left"], bs, years)), unsafe_allow_html=True)
    with cb:
        st.markdown(T.fin_table([lay["right_title"]] + [f"{y}年" for y in years],
                                _rows(lay["right"], bs, years)), unsafe_allow_html=True)
    r = bs[bs["年份"] == years[-1]].iloc[0]
    ta, tl, te = _v(r, "资产总计"), _v(r, "负债合计"), _v(r, "股东权益合计")
    if None not in (ta, tl, te):
        ok = abs(ta - tl - te) < max(abs(ta) * 0.005, 0.5)
        ui.note(f"{years[-1]} 年勾稽校验：资产 {ta:,.1f} = 负债 {tl:,.1f} + 权益 {te:,.1f} "
                f"= {tl+te:,.1f}　{'✓ 平衡' if ok else '⚠ 不平衡'}",
                "g" if ok else "d")


def render_income(inc: pd.DataFrame):
    years = [int(y) for y in inc["年份"]]
    lay = REPORT_LAYOUT["利润表"]
    st.markdown(f'<div class="sec"><span class="bar"></span>'
                f'<span class="t">{lay["title"]}</span>'
                f'<span class="d">单位：亿元</span></div>', unsafe_allow_html=True)
    st.markdown(T.fin_table(["项目"] + [f"{y}年" for y in years],
                            _rows(lay["items"], inc, years)), unsafe_allow_html=True)


def render_cash(cf: pd.DataFrame):
    years = [int(y) for y in cf["年份"]]
    lay = REPORT_LAYOUT["现金流量表"]
    st.markdown(f'<div class="sec"><span class="bar"></span>'
                f'<span class="t">{lay["title"]}</span>'
                f'<span class="d">单位：亿元</span></div>', unsafe_allow_html=True)
    st.markdown(T.fin_table(["项目"] + [f"{y}年" for y in years],
                            _rows(lay["items"], cf, years)), unsafe_allow_html=True)


def render_quality(diag: dict):
    st.markdown('<div class="sec"><span class="bar"></span>'
                '<span class="t">数据质量诊断</span></div>', unsafe_allow_html=True)
    grade_color = {"优秀": "g", "良好": "g", "基本可用（存在较多提示）": "w", "不可用": "d"}
    ui.note(f"数据质量评级：<b>{diag['grade']}</b>　｜　识别到 {diag['n_years']} 个报告期",
            grade_color.get(diag["grade"], ""))
    if diag["errors"]:
        for e in diag["errors"]:
            ui.note("❌ " + e, "d")
    for w in diag["warnings"]:
        ui.note("⚠ " + w, "w")
    for n in diag["infos"]:
        ui.note("ℹ " + n)
    if diag.get("completeness"):
        rows = [{"报表": k, "已识别科目": f"{v[0]}/{v[1]}", "完备度(%)": round(v[2], 0)}
                for k, v in diag["completeness"].items()]
        st.markdown(T.fin_table(["报表", "已识别科目", "完备度(%)"],
                                [{"c": [r["报表"], r["已识别科目"], f"{r['完备度(%)']:.0f}"],
                                  "t": "normal", "i": 0} for r in rows]),
                    unsafe_allow_html=True)


def after_load(parsed: dict, source: str, name: str = "", code: str = ""):
    dl.load(parsed, source, name, code)
    st.success(f"✅ 已加载：{dl.get_company_name()}（{dl.get_company_code()}）"
               f"　{parsed['years'][0]}–{parsed['years'][-1]} 年，共 {len(parsed['years'])} 期")
    diag = quality.diagnose(parsed.get("income"), parsed.get("balance"),
                            parsed.get("cashflow"), parsed.get("years", []))
    render_quality(diag)
    with st.expander("📋 财务报表预览", expanded=True):
        if not parsed["balance"].empty:
            render_balance(parsed["balance"])
        if not parsed["income"].empty:
            render_income(parsed["income"])
        if not parsed["cashflow"].empty:
            render_cash(parsed["cashflow"])


# ════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs(["① 快速体验", "② 上传报表", "③ 补充经营数据", "④ 手动录入"])

# ── ① 快速体验 ──
with tab1:
    st.markdown("### 内置示例：立讯精密（002475）")
    st.caption("CSMAR 标准导出格式，2020–2025 年合并报表，已换算为亿元")
    a, b = st.columns([1, 1.4])
    with a:
        st.info("**用途**\n- 快速查看平台全部分析能力\n- 作为数据格式参考样本\n\n"
                "**包含**\n- 资产负债表 / 利润表 / 现金流量表\n- 现金流量表（间接法，含折旧摊销）")
    with b:
        st.success("加载后可立即使用：经营全景 · 盈利质量 · 预算偏差 · 财务风险 · "
                   "战略追踪 · 行业对标 · 分析报告")
    if st.button("🚀 加载示例数据", type="primary", use_container_width=True):
        if not os.path.exists(SAMPLE_DIR):
            st.error(f"未找到示例数据目录：{SAMPLE_DIR}")
        else:
            with st.spinner("解析中…"):
                parsed = parser.parse_folder(SAMPLE_DIR)
            after_load(parsed, "内置示例（CSMAR）")
            # 一并载入真实分部数据与客户结构（年报披露值）
            try:
                from sample_data import luxshare
                luxshare.apply_to_session(parsed["years"])
                st.info("已同时载入年报披露的分部数据（消费电子 / 汽车电子 / 通讯及数据中心，"
                        "2024–2025 年）与第一大客户收入占比，"
                        "板块结构分析、客户集中度风险将自动启用。")
            except Exception as e:
                st.caption(f"（分部数据载入跳过：{e}）")
            st.rerun()

    if dl.is_loaded():
        st.divider()
        st.markdown("**当前已加载**")
        st.markdown(T.fin_table(
            ["项目", "内容"],
            [{"c": ["公司", dl.get_company_name()], "t": "normal", "i": 0},
             {"c": ["代码", dl.get_company_code()], "t": "normal", "i": 0},
             {"c": ["期间", f"{dl.get_years()[0]}–{dl.get_years()[-1]}"], "t": "normal", "i": 0},
             {"c": ["来源", dl.get_data_source()], "t": "normal", "i": 0}]),
            unsafe_allow_html=True)
        if st.button("→ 进入经营驾驶舱", type="primary", use_container_width=True):
            st.switch_page("app.py")

# ── ② 上传报表 ──
with tab2:
    st.markdown("### 上传财务报表")
    ui.note("支持两种格式：① **CSMAR 标准导出**（第1行字段名 / 第2行中文名 / 第3行单位）；"
            "② **简版表格** —— 首列为年份、其余列为科目，或首列为科目、其余列为年份。"
            "金额为元/万元/亿元均可自动识别。")
    c1, c2 = st.columns(2)
    with c1:
        f_bs = st.file_uploader("资产负债表（FS_Combas）", type=["xlsx", "xls", "csv"], key="u_bs")
        f_is = st.file_uploader("利润表（FS_Comins）", type=["xlsx", "xls", "csv"], key="u_is")
    with c2:
        f_cf = st.file_uploader("现金流量表（FS_Comscfd）", type=["xlsx", "xls", "csv"], key="u_cf")
        f_ci = st.file_uploader("现金流量表·间接法（选填，用于折旧摊销）",
                                type=["xlsx", "xls", "csv"], key="u_ci")
    cname = st.text_input("公司名称（选填，留空则自动识别）", placeholder="例如：某某股份有限公司")
    ccode = st.text_input("股票代码（选填）", placeholder="例如：000001")

    if st.button("📤 解析并加载", type="primary", use_container_width=True):
        if not (f_bs or f_is):
            st.error("请至少上传资产负债表或利润表")
        else:
            files = {}
            for f, k in ((f_bs, "balance"), (f_is, "income"), (f_cf, "cashflow"), (f_ci, "indirect")):
                if f:
                    tmp = f"_v2_tmp_{k}_{f.name}"
                    with open(tmp, "wb") as w:
                        w.write(f.getbuffer())
                    files[k] = tmp
            try:
                with st.spinner("解析中…"):
                    parsed = parser.parse_uploaded(files)
                after_load(parsed, "用户上传", cname, ccode)
            except Exception as e:
                st.error(f"解析失败：{e}")
            finally:
                for p in files.values():
                    try:
                        os.remove(p)
                    except Exception:
                        pass

    st.divider()
    st.markdown("#### 格式示例")
    st.code("简版格式 A（首列年份）：\n年份 | 营业收入 | 营业成本 | 净利润 | 资产总计 | 负债合计\n"
            "2023 | 1000 | 800 | 80 | 1500 | 900\n2024 | 1200 | 950 | 95 | 1700 | 1000",
            language="text")
    st.code("简版格式 B（首列科目）：\n项目 | 2023 | 2024\n营业收入 | 1000 | 1200\n"
            "营业成本 | 800 | 950\n净利润 | 80 | 95", language="text")

# ── ③ 补充经营数据 ──
with tab3:
    st.markdown("### 补充经营数据（可选）")
    ui.note("以下数据非必填。补充后可启用：分部结构分析、客户集中度风险、人均效能、"
            "研发资本化谨慎性评估。未填写时相关分析会自动降级并标注。")
    if not dl.is_loaded():
        st.warning("请先加载财务报表")
    else:
        years = dl.get_years()
        n = len(years)
        st.markdown("#### ① 业务分部（收入 / 成本）")
        st.caption(f"填写 {years[-1]} 年各业务板块数据；往年可留空（留空时按本年占比回推）")
        seg_names = st.text_input("板块名称（逗号分隔）", value="业务一,业务二,业务三",
                                  help="例如：消费电子,汽车电子,通信互联")
        names = [s.strip() for s in seg_names.split(",") if s.strip()]
        if names:
            gc = st.columns(len(names) * 2)
            seg_data = {}
            for j, nm in enumerate(names):
                with gc[j * 2]:
                    r = st.number_input(f"{nm}·收入(亿元)", min_value=0.0, value=0.0,
                                        step=1.0, key=f"sg_r_{j}")
                with gc[j * 2 + 1]:
                    c = st.number_input(f"{nm}·成本(亿元)", min_value=0.0, value=0.0,
                                        step=1.0, key=f"sg_c_{j}")
                seg_data[nm] = {"收入": [None] * (n - 1) + [r if r else None],
                                "成本": [None] * (n - 1) + [c if c else None]}
            if st.button("💾 保存分部数据", use_container_width=True):
                tot = sum(v["收入"][-1] or 0 for v in seg_data.values())
                rev = fc_rev = None
                inc = dl.get_income()
                if inc is not None and not inc.empty:
                    rev = float(inc.iloc[-1]["营业收入"]) if pd.notna(inc.iloc[-1].get("营业收入")) else None
                if tot and rev and abs(tot - rev) / rev > 0.05:
                    st.warning(f"各板块收入合计 {tot:,.1f} 亿元与营业收入 {rev:,.1f} 亿元差异超过 5%，"
                               f"已按原值保存，但建议核对口径")
                for nm in seg_data:
                    if not seg_data[nm]["成本"][-1]:
                        r = seg_data[nm]["收入"][-1]
                        gm = dl.get_income()
                        rate = 0.85
                        if gm is not None and not gm.empty:
                            r0 = float(gm.iloc[-1].get("营业收入") or 0)
                            c0 = float(gm.iloc[-1].get("营业成本") or 0)
                            rate = c0 / r0 if r0 else 0.85
                        seg_data[nm]["成本"][-1] = (r or 0) * rate
                st.session_state.segments = seg_data
                st.session_state.pop("budget_cache", None)
                st.success("✅ 分部数据已保存")

        st.divider()
        st.markdown("#### ② 集中度与人员（最近一期）")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            top5 = st.number_input("前五大客户收入占比(%)", 0.0, 100.0, 0.0, 1.0, key="ex_top5")
        with c2:
            top1 = st.number_input("第一大客户收入占比(%)", 0.0, 100.0, 0.0, 1.0, key="ex_top1")
        with c3:
            sup5 = st.number_input("前五大供应商采购占比(%)", 0.0, 100.0, 0.0, 1.0, key="ex_sup5")
        with c4:
            staff = st.number_input("员工人数(人)", 0, 10000000, 0, 1000, key="ex_staff")
        capr = st.number_input("研发资本化率(%)", 0.0, 100.0, 0.0, 1.0, key="ex_cap")
        if st.button("💾 保存经营指标", use_container_width=True):
            ex = {}
            if top5:
                ex["前五大客户占比"] = [top5]
            if top1:
                ex["第一大客户占比"] = [top1]
            if sup5:
                ex["前五大供应商占比"] = [sup5]
            if staff:
                ex["员工人数"] = [staff]
            if capr:
                ex["研发资本化率"] = [capr]
            dl.set_extra(ex)
            st.success("✅ 已保存")

        st.divider()
        st.markdown("#### ③ 同业公司数据（用于分位排名，可选）")
        st.caption("上传 Excel/CSV：第一列为公司名称，其余列为指标（列名与系统指标名一致，"
                   "如「净资产收益率 ROE」「销售毛利率」）")
        f_peer = st.file_uploader("同业数据表", type=["xlsx", "xls", "csv"], key="u_peer")
        if f_peer:
            try:
                pdf = pd.read_excel(f_peer) if f_peer.name.endswith(("xlsx", "xls")) else pd.read_csv(f_peer)
                st.dataframe(pdf.head(10), use_container_width=True, hide_index=True)
                if st.button("💾 保存同业数据", use_container_width=True):
                    dl.set_peer_data(pdf)
                    st.success("✅ 同业数据已保存")
            except Exception as e:
                st.error(f"读取失败：{e}")

        cur = dl.get_segments()
        if cur:
            st.divider()
            st.markdown("**当前分部数据**")
            rows = []
            for nm, d in cur.items():
                r, c = d["收入"][-1], d["成本"][-1]
                rows.append({"c": [nm, T.num(r, 1), T.num(c, 1),
                                   T.pct((r - c) / r * 100 if (r and c is not None) else None)],
                             "t": "normal", "i": 0})
            st.markdown(T.fin_table(["板块", "收入(亿元)", "成本(亿元)", "毛利率"], rows),
                        unsafe_allow_html=True)

# ── ④ 手动录入 ──
with tab4:
    st.markdown("### 手动录入（单期或多年）")
    st.caption("适合只有 1–2 期数据、或需要快速试算的场景")
    n_years = st.number_input("录入年数", 1, 10, 3, 1)
    years_in = st.text_input("年份（逗号分隔）", value="2022,2023,2024")
    ys = [int(x.strip()) for x in years_in.split(",") if x.strip().isdigit()][:int(n_years)]
    keys_show = ["营业收入", "营业成本", "销售费用", "管理费用", "研发费用", "财务费用",
                 "营业利润", "利润总额", "所得税费用", "净利润",
                 "货币资金", "应收账款净额", "存货净额", "流动资产合计", "资产总计",
                 "短期借款", "应付账款", "流动负债合计", "长期借款", "负债合计",
                 "股东权益合计", "未分配利润", "经营现金流量净额", "资本开支"]
    if ys:
        data = {}
        gcols = st.columns(4)
        for j, k in enumerate(keys_show):
            with gcols[j % 4]:
                vals = st.text_input(k, value="", placeholder="逗号分隔各年，单位亿元",
                                     key=f"mi_{k}")
                if vals:
                    arr = []
                    for x in vals.split(","):
                        x = x.strip()
                        arr.append(float(x) if x.replace(".", "").replace("-", "").isdigit() else None)
                    data[k] = arr + [None] * (len(ys) - len(arr))
        if st.button("💾 生成数据集", type="primary", use_container_width=True):
            inc_df = pd.DataFrame({"年份": ys})
            bs_df = pd.DataFrame({"年份": ys})
            cf_df = pd.DataFrame({"年份": ys})
            inc_keys = ["营业收入", "营业成本", "销售费用", "管理费用", "研发费用", "财务费用",
                        "营业利润", "利润总额", "所得税费用", "净利润"]
            bs_keys = ["货币资金", "应收账款净额", "存货净额", "流动资产合计", "资产总计",
                       "短期借款", "应付账款", "流动负债合计", "长期借款", "负债合计",
                       "股东权益合计", "未分配利润"]
            cf_keys = ["经营现金流量净额", "资本开支"]
            for k, v in data.items():
                tgt = inc_df if k in inc_keys else (bs_df if k in bs_keys else cf_df)
                tgt[k] = v
            parsed = {"income": inc_df, "balance": bs_df, "cashflow": cf_df,
                      "years": ys, "company_name": "手动录入公司",
                      "company_code": ""}
            after_load(parsed, "手动录入")
