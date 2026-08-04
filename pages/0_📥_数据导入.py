"""
数据导入页面 — 会企标准财务报表格式
"""
import streamlit as st
import pandas as pd
import os
from config import COLORS
from modules.csmar_parser import CSMARParser
from modules.data_validator import validate_all

st.set_page_config(page_title="数据导入", page_icon="📥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<div style="text-align:center;font-size:11px;color:#8899aa;background:#f0f2f5;
padding:3px 0;letter-spacing:1px;border-bottom:1px solid #e0e4e8;margin:-1rem -1rem 0.5rem -1rem;">
邹嘉欣秋招使用 · 最后更新2026年7月 · 持续迭代中
</div>
""", unsafe_allow_html=True)

# ============================================================
# 辅助函数
# ============================================================
def v(row, key, default=None):
    try:
        val = row[key]
        if pd.isna(val) or val is None: return default
        return float(val)
    except: return default

def fmt(v, bold=False):
    if v is None: return "-"
    s = f"{v:,.2f}"
    return f"**{s}**" if bold else s

# ============================================================
# 资产负债表（会企01表）- 账户式
# ============================================================
def render_balance_sheet(df: pd.DataFrame):
    """资产负债表 - 所有年份"""
    st.markdown("""<div style="background:#33558B;color:#fff;text-align:center;padding:8px;font-size:14px;font-weight:bold;margin-top:12px;">资产负债表（会企01表）</div>""", unsafe_allow_html=True)

    years = sorted([int(y) for y in df["年份"].unique()])

    c1, c2, c3 = st.columns([5, 0.15, 5])
    with c1:
        st.markdown("**资  产**")
        asset_items = [
            ("H","流动资产："),("D","  货币资金","货币资金"),("D","  应收账款净额","应收账款净额"),
            ("D","  存货净额","存货净额"),("T","  流动资产合计","流动资产合计"),
            ("H","非流动资产："),("D","  固定资产净额","固定资产净额"),("D","  在建工程净额","在建工程净额"),
            ("D","  无形资产净额","无形资产净额"),("T","  非流动资产合计","非流动资产合计"),
            ("G","  资产总计","资产总计"),
        ]
        rows = []
        for tp, label, *rest in asset_items:
            key = rest[0] if rest else ""
            row = {"项目": f"**{label}**" if tp in ("H","G","T") else label}
            if key:
                for yr in years:
                    row_v = df[df["年份"]==yr].iloc[0]
                    val = v(row_v, key)
                    row[str(yr)] = f"**{val:,.1f}**" if (tp in ("T","G")) and val else (f"{val:,.1f}" if val else "-")
            else:
                for yr in years: row[str(yr)] = ""
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=420)

    with c2: st.markdown("<div style='width:1px;background:#ddd;min-height:420px;margin:auto;'></div>", unsafe_allow_html=True)

    with c3:
        st.markdown("**负债和所有者权益**")
        liab_items = [
            ("H","流动负债："),("D","  短期借款","短期借款"),("D","  应付账款","应付账款"),
            ("T","  流动负债合计","流动负债合计"),("H","非流动负债："),("D","  长期借款","长期借款"),
            ("T","  负债合计","负债合计"),("H","所有者权益："),("D","  实收资本(或股本)","实收资本（或股本）"),
            ("D","  未分配利润","未分配利润"),("T","  股东权益合计","股东权益合计"),
            ("G","  负债和权益总计","资产总计"),
        ]
        rows = []
        for tp, label, *rest in liab_items:
            key = rest[0] if rest else ""
            row = {"项目": f"**{label}**" if tp in ("H","G","T") else label}
            if key:
                for yr in years:
                    row_v = df[df["年份"]==yr].iloc[0]
                    val = v(row_v, key)
                    row[str(yr)] = f"**{val:,.1f}**" if (tp in ("T","G")) and val else (f"{val:,.1f}" if val else "-")
            else:
                for yr in years: row[str(yr)] = ""
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=420)

    # 勾稽
    latest_yr = years[-1]; rl = df[df["年份"]==latest_yr].iloc[0]
    ta = v(rl,"资产总计",0); tl = v(rl,"负债合计",0); te = v(rl,"股东权益合计",0)
    st.caption(f"✅ {latest_yr}年: 资产 {ta:,.1f} = 负债 {tl:,.1f} + 权益 {te:,.1f} = {tl+te:,.1f} {'✓' if abs(ta-tl-te)<0.1 else '⚠️'}")

# ============================================================
# 利润表（会企02表）- 多步式
# ============================================================
def render_income_statement(df: pd.DataFrame):
    """利润表 - 所有年份"""
    st.markdown("""<div style="background:#33558B;color:#fff;text-align:center;padding:8px;font-size:14px;font-weight:bold;margin-top:12px;">利润表（会企02表）</div>""", unsafe_allow_html=True)

    years = sorted([int(y) for y in df["年份"].unique()])
    items = [
        ("一、营业收入","营业收入",True),("  减：营业成本","营业成本",False),("  税金及附加","税金及附加",False),
        ("  销售费用","销售费用",False),("  管理费用","管理费用",False),("  研发费用","研发费用",False),
        ("  财务费用","财务费用",False),("二、营业利润","营业利润",True),
        ("三、利润总额","利润总额",True),("  减：所得税费用","所得税费用",False),
        ("四、净利润","净利润",True),("  基本每股收益(元)","基本每股收益",False),
    ]
    rows = []
    for label, key, is_total in items:
        row = {"项目": f"**{label}**" if is_total else label}
        for yr in years:
            rv = df[df["年份"]==yr].iloc[0]; val = v(rv, key)
            row[str(yr)] = f"**{val:,.1f}**" if is_total and val else (f"{val:,.2f}" if val else "-")
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=420)

# ============================================================
# 现金流量表（会企03表）
# ============================================================
def render_cashflow_statement(df: pd.DataFrame):
    """现金流量表 - 所有年份"""
    st.markdown("""<div style="background:#33558B;color:#fff;text-align:center;padding:8px;font-size:14px;font-weight:bold;margin-top:12px;">现金流量表（会企03表）</div>""", unsafe_allow_html=True)

    years = sorted([int(y) for y in df["年份"].unique()])
    items = [
        ("H","一、经营活动："),("D","  经营现金流入","经营现金流入"),("D","  经营现金流出","经营现金流出"),
        ("T","  经营现金流量净额","经营现金流量净额"),
        ("H","二、投资活动："),("D","  投资现金流入","投资现金流入"),("D","  投资现金流出","投资现金流出"),
        ("T","  投资现金流量净额","投资现金流量净额"),
        ("H","三、筹资活动："),("D","  筹资现金流入","筹资现金流入"),("D","  筹资现金流出","筹资现金流出"),
        ("T","  筹资现金流量净额","筹资现金流量净额"),
        ("D","  资本开支","资本开支"),
    ]
    rows = []
    for tp, label, *rest in items:
        key = rest[0] if rest else ""
        if tp == "H": rows.append({"项目": f"**{label}**", **{str(yr):"" for yr in years}}); continue
        row = {"项目": f"**{label}**" if tp=="T" else label}
        for yr in years:
            rv = df[df["年份"]==yr].iloc[0]; val = v(rv, key)
            row[str(yr)] = f"**{val:,.1f}**" if tp=="T" and val else (f"{val:,.1f}" if val else "-")
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=380)

# ============================================================
# 页面内容
# ============================================================
st.markdown(f"""
<div style="text-align:center;padding:10px 0;">
    <h1 style="color:{COLORS['ink']};margin:0;">📊 企业经营分析预警系统</h1>
    <p style="color:{COLORS['slate']};font-size:14px;margin:4px 0;">面向财务BP的业财融合智能分析平台</p>
</div>""", unsafe_allow_html=True)
st.divider()

tab1, tab2, tab3 = st.tabs(["🚀 快速体验", "📤 上传CSMAR数据", "✏️ 手动录入"])

with tab1:
    st.markdown("### 🚀 一键加载立讯精密（002475）")
    st.caption("数据来源：CSMAR 2020-2025年报 | 已脱敏")
    c_a, c_b = st.columns([1, 1])
    with c_a: st.info("**立讯精密 (002475)**\n- 行业：消费电子/精密制造\n- 期间：2020-2025年\n- 来源：CSMAR数据库")
    with c_b: st.success("加载后生成：📊业财看板 | 🚨指标预警 | 💰预算分析 | 🎯战略追踪 | 🏭行业对比 | 📄自动报告")

    if st.button("🚀 加载立讯精密数据", type="primary", use_container_width=True):
        with st.spinner("加载数据..."):
            # 尝试从本地CSMAR文件加载
            base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "立讯精密财务报表")
            if os.path.exists(base):
                parser = CSMARParser(base)
                bs = parser.parse_balance_sheet(); inc = parser.parse_income_statement(); cf = parser.parse_cashflow()
            else:
                # Streamlit Cloud fallback: 使用内嵌数据
                from sample_data.luxshare_data import INCOME_STATEMENT, BALANCE_SHEET, CASHFLOW, YEARS
                bs = pd.DataFrame(BALANCE_SHEET, index=YEARS).reset_index().rename(columns={"index": "年份"})
                inc = pd.DataFrame(INCOME_STATEMENT, index=YEARS).reset_index().rename(columns={"index": "年份"})
                cf = pd.DataFrame(CASHFLOW, index=YEARS).reset_index().rename(columns={"index": "年份"})

            st.session_state.balance_sheet = bs; st.session_state.income_statement = inc; st.session_state.cashflow = cf
            st.session_state.years = [int(y) for y in bs["年份"]]
            st.session_state.data_loaded = True
            try:
                st.session_state.company_name = parser._get_company_name()
                st.session_state.company_code = parser._get_company_code()
            except: st.session_state.company_name = "立讯精密"; st.session_state.company_code = "002475"
            st.session_state.data_source = "CSMAR"

        validation = validate_all(bs, inc, cf)
        if validation["all_valid"]: st.success(f"✅ {st.session_state.company_name} ({st.session_state.company_code})")
        if validation["all_warnings"]:
            for w in validation["all_warnings"]: st.warning(w)

        # === 标准财务报表格式 ===
        with st.expander("📋 财务报表预览（会企标准格式）", expanded=True):
            render_balance_sheet(bs)
            render_income_statement(inc)
            render_cashflow_statement(cf)

        st.divider(); st.markdown("### 🎯 开始分析")
        nav_cols = st.columns(6)
        for i, (label, target) in enumerate([
            ("📊 业财看板","pages/1_📊_业财融合看板.py"),("🚨 指标预警","pages/2_🚨_指标监控预警.py"),
            ("💰 预算分析","pages/3_💰_预算偏差分析.py"),("🎯 战略追踪","pages/4_🎯_战略目标追踪.py"),
            ("🏭 行业对比","pages/6_🏭_行业对比分析.py"),("📄 生成报告","pages/5_📄_分析报告生成.py"),
        ]):
            with nav_cols[i]:
                if st.button(label, key=f"nv_{i}", use_container_width=True): st.switch_page(target)

with tab2:
    st.markdown("### 📤 上传CSMAR格式财务报表")
    st.caption("支持CSMAR标准导出格式（.xlsx）")
    bs_f = st.file_uploader("资产负债表 (FS_Combas)", type=["xlsx"], key="bs_u")
    is_f = st.file_uploader("利润表 (FS_Comins)", type=["xlsx"], key="is_u")
    cf_f = st.file_uploader("现金流量表 (FS_Comscfd)", type=["xlsx"], key="cf_u")
    cname = st.text_input("公司名称（选填）", placeholder="自动识别")
    if st.button("📤 解析上传", type="primary", use_container_width=True):
        if not bs_f and not is_f: st.error("请至少上传一份报表")
        else:
            with st.spinner("解析中..."):
                uploaded = {}
                for f, key in [(bs_f,"bs"),(is_f,"is"),(cf_f,"cf")]:
                    if f:
                        tmp = f"_tmp_{f.name}"
                        with open(tmp,"wb") as wf: wf.write(f.getbuffer())
                        uploaded[key] = tmp
                parser = CSMARParser(); results = {}
                if "bs" in uploaded: results["balance_sheet"] = parser.parse_balance_sheet(uploaded["bs"])
                if "is" in uploaded: results["income_statement"] = parser.parse_income_statement(uploaded["is"])
                if "cf" in uploaded: results["cashflow"] = parser.parse_cashflow(uploaded["cf"])
                for k, v in results.items():
                    if k == "balance_sheet": st.session_state.balance_sheet = v; st.session_state.years = [int(y) for y in v["年份"]]
                    elif k == "income_statement": st.session_state.income_statement = v
                    elif k == "cashflow": st.session_state.cashflow = v
                st.session_state.data_loaded = True; st.session_state.data_source = "用户上传"
                st.session_state.company_name = cname or parser._get_company_name() if "bs" in uploaded else "导入公司"
                for p in uploaded.values():
                    try: os.remove(p)
                    except: pass
            st.success(f"✅ {st.session_state.company_name}")
            if "balance_sheet" in results: render_balance_sheet(results["balance_sheet"])
            if "income_statement" in results: render_income_statement(results["income_statement"])
            if "cashflow" in results: render_cashflow_statement(results["cashflow"])

with tab3:
    st.markdown("### ✏️ 手动录入")
    st.info("💡 手动录入模式后续完善。当前建议使用「快速体验」或「上传CSMAR数据」。")
