"""
业财融合看板 v3 — 7区深度分析 + 四步法
"""
import streamlit as st
import pandas as pd
from config import COLORS
from modules.data_loader import is_data_loaded, get_company_name, get_income, get_balance, get_years, get_segment_data, get_special_metrics
from modules.kpi_engine import calc_all_kpis
from modules.business_finance import *
from utils.ui_helpers import bi_kpi_row, bi_breadcrumb, bi_drill_bar, four_step_card, bi_section, show_watermark
show_watermark()

if not is_data_loaded():
    st.switch_page("pages/0_📥_数据导入.py")

def compact_chart(fig):
    """统一图表尺寸 - 必须在使用前定义"""
    fig.update_layout(height=220, margin=dict(l=5,r=5,t=25,b=5), font=dict(size=9),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

company = get_company_name()
inc = get_income(); bs = get_balance(); years = get_years(); latest = years[-1]
drill = st.session_state.get("drill_context", {})
bi_breadcrumb("业财看板", drill)
st.markdown(f"<h3>📊 业财融合深度分析 — {company}</h3>", unsafe_allow_html=True)

# === KPI顶栏（8列紧凑） ===
total_rev = float(inc[inc["年份"]==latest]["营业收入"].values[0])
prev_rev = float(inc[inc["年份"]==years[-2]]["营业收入"].values[0])
np_val = float(inc[inc["年份"]==latest]["净利润"].values[0])
equity = float(bs[bs["年份"]==latest]["股东权益合计"].values[0])
total_assets = float(bs[bs["年份"]==latest]["资产总计"].values[0])
rd_fee = float(inc[inc["年份"]==latest]["研发费用"].values[0])
gross = round((total_rev-float(inc[inc["年份"]==latest]["营业成本"].values[0]))/total_rev*100,1)
roe = round(np_val/equity*100,1)
top5 = get_special_metrics()["前五大客户收入占比"][-1]

bi_kpi_row([
    {"label":"营业收入","value":f"{total_rev:.0f}亿","delta":f"{round((total_rev-prev_rev)/prev_rev*100,1):+.1f}%","status":"normal"},
    {"label":"净利润","value":f"{np_val:.1f}亿","delta":"","status":"normal" if np_val>0 else "danger"},
    {"label":"ROE","value":f"{roe:.1f}%","delta":"","status":"normal" if roe>10 else "warning"},
    {"label":"毛利率","value":f"{gross:.1f}%","delta":"","status":"normal" if gross>15 else "warning"},
    {"label":"总资产","value":f"{total_assets:.0f}亿","delta":"","status":"normal"},
    {"label":"研发费用率","value":f"{round(rd_fee/total_rev*100,1):.1f}%","delta":"","status":"normal"},
    {"label":"前5大客户","value":f"{top5:.1f}%","delta":"","status":"warning" if top5>70 else "normal"},
    {"label":"期间","value":f"{years[0]}-{latest}","delta":"","status":"normal"},
], cols_per_row=8)

st.divider()

# ============================================================
# 表格0：杜邦分析速览表
# ============================================================
with st.expander("📐 杜邦分析 — 五年趋势拆解", expanded=True):
    dp_data = []
    for yr in years:
        row_i = inc[inc["年份"]==yr].iloc[0]; row_b = bs[bs["年份"]==yr].iloc[0]
        rev_y = float(row_i["营业收入"]); np_y = float(row_i["净利润"])
        ta_y = float(row_b["资产总计"]); eq_y = float(row_b["股东权益合计"])
        npm = round(np_y/rev_y*100,2); ato = round(rev_y/ta_y,3); em = round(ta_y/eq_y,2)
        roe_y = round(npm*ato*em/100,1)
        dp_data.append({"年份":int(yr), "ROE(%)":roe_y, "净利率(%)":npm, "总资产周转率(次)":ato,
                        "权益乘数":em, "净利润(亿)":round(np_y,1), "收入(亿)":round(rev_y,1),
                        "总资产(亿)":round(ta_y,1), "股东权益(亿)":round(eq_y,1)})
    dp_df = pd.DataFrame(dp_data)

    # ROE变化拆解
    st.markdown("**ROE = 净利率 × 总资产周转率 × 权益乘数**")
    st.dataframe(dp_df, use_container_width=True, hide_index=True, height=200)

    # 变化趋势解读
    if len(dp_data) >= 3:
        first = dp_data[0]; last = dp_data[-1]
        roe_chg = last["ROE(%)"] - first["ROE(%)"]
        npm_chg = last["净利率(%)"] - first["净利率(%)"]
        ato_chg = last["总资产周转率(次)"] - first["总资产周转率(次)"]
        em_chg = last["权益乘数"] - first["权益乘数"]

        # 因素分析：ROE变化 ≈ 净利率贡献 + 周转率贡献 + 杠杆贡献
        npm_contrib = npm_chg * first["总资产周转率(次)"] * first["权益乘数"] / 100
        ato_contrib = last["净利率(%)"] * ato_chg * first["权益乘数"] / 100
        em_contrib = last["净利率(%)"] * last["总资产周转率(次)"] * em_chg / 100

        st.markdown(f"""
        <div style="font-size:11px;line-height:1.7;background:#fff;padding:10px 14px;border-left:3px solid {COLORS['accent']};margin:8px 0;">
        <b>📌 What — ROE变化趋势</b><br>
        ROE从{first["年份"]}年<b>{first["ROE(%)"]}%</b>变为{last["年份"]}年<b>{last["ROE(%)"]}%</b>，累计变化<b>{roe_chg:+.1f}%</b><br><br>
        <b>🔍 Why — 因素连环替代法拆解</b><br>
        ① 净利率变化贡献 ≈ <b>{npm_contrib:+.2f}pp</b>（{'盈利能力改善' if npm_chg>0 else '盈利能力下滑'}，净利率从{first['净利率(%)']}%→{last['净利率(%)']}%）<br>
        ② 周转率变化贡献 ≈ <b>{ato_contrib:+.2f}pp</b>（{'资产效率提升' if ato_chg>0 else '资产效率下降'}，周转率从{first['总资产周转率(次)']}→{last['总资产周转率(次)']}）<br>
        ③ 杠杆变化贡献 ≈ <b>{em_contrib:+.2f}pp</b>（{'杠杆增加' if em_chg>0 else '杠杆降低'}，权益乘数从{first['权益乘数']}→{last['权益乘数']}）<br><br>
        <b>⚠️ So What — 核心驱动因素</b><br>
        最大驱动因素是<b>{"净利率" if abs(npm_contrib)>=abs(ato_contrib) and abs(npm_contrib)>=abs(em_contrib) else ("周转率" if abs(ato_contrib)>=abs(em_contrib) else "杠杆")}</b>，
        {'需关注盈利可持续性' if abs(npm_contrib)>=abs(ato_contrib) else ('需关注资产运营效率' if abs(ato_contrib)>=abs(em_contrib) else '需关注财务杠杆风险')}<br><br>
        <b>💡 Now What — 管理建议</b><br>
        {'→ 提升净利率：优化产品结构+控制成本费用率' if npm_chg<0 else '→ 维持盈利优势：持续研发投入+品牌溢价'}<br>
        {'→ 加速周转：降低存货+加快应收回收+优化固定资产利用率' if ato_chg<0 else '→ 保持效率：关注产能利用率+防止过度扩张'}<br>
        {'→ 控制杠杆：优化债务结构+关注利息保障倍数' if em_chg>0 and em_chg>0.3 else '→ 适度杠杆：可利用低息环境扩大投资回报'}
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# 区块1：业务板块收入概览
# ============================================================
st.divider()
c1, c2 = st.columns(2)
with c1: st.plotly_chart(compact_chart(get_segment_revenue_chart()), use_container_width=True)
with c2: st.plotly_chart(compact_chart(get_segment_margin_chart()), use_container_width=True)
w, wh, sw, nw = segment_fourstep()
four_step_card("业务板块收入与毛利分析", w, wh, sw, nw)

st.divider()

# ============================================================
# 区块2：收入驱动归因 + 区块3：成本差异 并排
# ============================================================
c3, c4 = st.columns(2)
with c3:
    st.plotly_chart(compact_chart(revenue_attribution_chart()), use_container_width=True)
    w, wh, sw, nw = revenue_attribution_fourstep()
    four_step_card("收入驱动归因（因素分析）", w, wh, sw, nw)
with c4:
    st.plotly_chart(compact_chart(cost_structure_chart()), use_container_width=True)
    w, wh, sw, nw = cost_analysis_fourstep()
    four_step_card("成本差异分析（料工费追溯）", w, wh, sw, nw)

st.divider()

# ============================================================
# 区块4：应收账款 + 区块5：存货 并排
# ============================================================
c5, c6 = st.columns(2)
with c5:
    st.plotly_chart(compact_chart(ar_quality_chart()), use_container_width=True)
    w, wh, sw, nw = ar_quality_fourstep()
    four_step_card("应收账款质量分析", w, wh, sw, nw)
with c6:
    st.plotly_chart(compact_chart(inventory_structure_chart()), use_container_width=True)
    w, wh, sw, nw = inventory_fourstep()
    four_step_card("存货结构与跌价风险评估", w, wh, sw, nw)

st.divider()

# ============================================================
# 区块6：费用效能 + 区块7：研发+客户
# ============================================================
c7, c8 = st.columns(2)
with c7:
    st.plotly_chart(compact_chart(fee_roi_chart()), use_container_width=True)
    w, wh, sw, nw = fee_roi_fourstep()
    four_step_card("费用效能ROI分析", w, wh, sw, nw)
with c8:
    st.plotly_chart(compact_chart(get_rd_efficiency_chart()), use_container_width=True)
    st.plotly_chart(compact_chart(get_customer_concentration_chart()), use_container_width=True)
    st.caption("🔍 上：研发费用率+资本化比例 | 下：客户集中度趋势(30%警戒线)")

st.divider()

# === 穿透 ===
bi_drill_bar([
    {"label":"查看预警指标","target":"pages/2_🚨_指标监控预警.py","context":{"from":"业财看板","focus":"异常指标"}},
    {"label":"查看预算偏差","target":"pages/3_💰_预算偏差分析.py","context":{"from":"业财看板","focus":"预算根因"}},
    {"label":"行业对比分析","target":"pages/6_🏭_行业对比分析.py","context":{"from":"业财看板","focus":"行业对标"}},
])
