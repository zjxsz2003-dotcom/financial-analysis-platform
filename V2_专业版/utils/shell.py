"""
页面外壳：主题注入 + 侧边栏 + 数据守卫
每个页面顶部一行 init() 即可
"""
from __future__ import annotations
import streamlit as st

from utils.theme import apply_theme, watermark
from utils import ui
from modules.data_loader import (is_loaded, get_company_name, get_company_code,
                                 get_data_source, get_years, available_flags,
                                 get_industry_name, set_industry, reset)
from config import C, INDUSTRY_PRESETS


def render_sidebar():
    with st.sidebar:
        st.markdown(
            f'<div style="padding:2px 0 6px">'
            f'<div style="font-size:15px;font-weight:700;color:{C["navy"]}">◧ 经营分析平台</div>'
            f'<div style="font-size:11px;color:{C["muted"]}">Enterprise Financial Analytics · V2.0</div>'
            f'</div>', unsafe_allow_html=True)
        st.divider()

        if is_loaded():
            years = get_years()
            st.markdown(
                f'<div style="background:{C["b050"]};border:1px solid {C["line"]};'
                f'border-radius:6px;padding:9px 11px;margin-bottom:6px">'
                f'<div style="font-size:10px;color:{C["muted"]}">当前分析对象</div>'
                f'<div style="font-size:14px;font-weight:700;color:{C["navy"]}">'
                f'{get_company_name()}　<span style="font-size:11px;color:{C["muted"]}">'
                f'{get_company_code()}</span></div>'
                f'<div style="font-size:10.5px;color:{C["muted"]}">'
                f'{years[0] if years else "—"}–{years[-1] if years else "—"} 年 · {get_data_source()}</div>'
                f'</div>', unsafe_allow_html=True)

        # 行业基准切换
        ind = st.selectbox("行业基准", list(INDUSTRY_PRESETS.keys()),
                           index=list(INDUSTRY_PRESETS.keys()).index(get_industry_name())
                           if get_industry_name() in INDUSTRY_PRESETS else 0)
        if ind != get_industry_name():
            set_industry(ind)
            st.session_state.pop("model_cache", None)
            st.rerun()

        with st.expander("⚙️ 分析设置"):
            st.checkbox("公司名称脱敏", key="anonymize")
            key = st.text_input("DeepSeek API Key（可选）", type="password",
                                placeholder="配置后报告摘要由 AI 润色")
            if key:
                import os
                os.environ["DEEPSEEK_API_KEY"] = key

        st.divider()
        st.caption("数据完备度")
        flags = available_flags()
        for k, v in flags.items():
            color = C["good"] if v else C["faint"]
            icon = "●" if v else "○"
            st.markdown(f'<div style="font-size:11px;color:{C["text2"]};'
                        f'line-height:1.7"><span style="color:{color}">{icon}</span> {k}</div>',
                        unsafe_allow_html=True)

        st.divider()
        if st.button("⇄ 重新导入数据", use_container_width=True):
            reset()
            st.switch_page("pages/0_数据导入.py")


# ════════════════════════════════════════════════════════════
# 分析主线（面试讲解的逻辑线：诊断 → 归因 → 风险 → 决策 → 输出）
# ════════════════════════════════════════════════════════════
FLOW = [
    ("数据导入", "pages/0_数据导入.py", "报表解析 · 勾稽校验 · 质量诊断"),
    ("① 经营诊断", "pages/1_经营诊断.py", "五维指标 · 杜邦分解 · 行业对标"),
    ("② 业财归因", "pages/2_业财归因.py", "盈利质量 · 板块与成本 · 营运资本"),
    ("③ 财务风险", "pages/3_财务风险.py", "评分卡 · Z值 · 压力测试"),
    ("④ 预算与战略", "pages/4_预算与战略.py", "利润桥 · 达成缺口 · 情景模拟"),
    ("⑤ 分析报告", "pages/5_分析报告.py", "一键生成 · 多格式导出"),
]

FLOW_LOGIC = ("数据 → 诊断「现在怎么样」→ 归因「为什么会这样」→ 风险「会出什么问题」"
              "→ 决策「离目标多远、怎么补」→ 输出「给管理层的报告」")


def flow_bar(current: int = 0):
    """顶部分析主线步骤条：当前步骤高亮，其余可点击跳转"""
    cols = st.columns(len(FLOW))
    for j, (name, path, desc) in enumerate(FLOW):
        with cols[j]:
            if j == current:
                st.markdown(
                    f'<div style="background:{C["primary"]};color:#fff;border-radius:5px;'
                    f'padding:7px 4px;text-align:center;font-size:12.5px;font-weight:700">'
                    f'{name}</div>', unsafe_allow_html=True)
            else:
                if st.button(name, key=f"flow_{j}", use_container_width=True, help=desc):
                    st.switch_page(path)
    st.caption(FLOW_LOGIC)


def init(page_title: str, icon: str = "◧", need_data: bool = True, step: int = 0):
    apply_theme(page_title, icon)
    watermark()
    if need_data and not is_loaded():
        # 跳转失败时不崩溃，改为就地给出引导（例如入口文件路径解析异常时）
        try:
            st.switch_page("pages/0_数据导入.py")
        except Exception:
            st.info("请先在「数据导入」页加载报表数据。")
        st.stop()
    render_sidebar()
    if step > 0:
        flow_bar(step)
