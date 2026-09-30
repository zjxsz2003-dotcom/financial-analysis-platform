"""
示例数据包：立讯精密（002475）真实分部与客户结构
数据来源：2025 年年度报告（2026-04-14 披露）、投资者关系活动记录表、
证券时报 / 中证网公开报道。单位：亿元。

分部数据仅有 2024、2025 两年为年报披露值，其余年度留空——
系统会自动处理缺失年度，不会用估算值填充。
"""
from __future__ import annotations

# 板块：（2024收入, 2024成本, 2025收入, 2025成本）
SEGMENTS_RAW = {
    "消费电子":      (2330.90, 2109.90, 2642.66, 2361.50),   # 毛利率 9.48% → 10.64%
    "汽车电子":      (137.60, 115.90, 392.55, 330.73),       # 毛利率 15.80% → 15.75%
    "通讯及数据中心": (183.60, 153.50, 245.68, 200.48),        # 毛利率 16.40% → 18.40%
}

# 客户结构：第一大客户（苹果）收入占比，来源为年报「前五名客户」披露
CUSTOMER_TOP1 = {2023: 75.24, 2024: 70.74, 2025: 56.68}
CUSTOMER_TOP2 = {2025: 2.86}


def build_segments(years: list) -> dict:
    """按 years 长度对齐，缺失年份填 None"""
    n = len(years)
    out = {}
    idx_2024 = years.index(2024) if 2024 in years else None
    idx_2025 = years.index(2025) if 2025 in years else None
    for name, (r24, c24, r25, c25) in SEGMENTS_RAW.items():
        rev = [None] * n
        cost = [None] * n
        if idx_2024 is not None:
            rev[idx_2024], cost[idx_2024] = r24, c24
        if idx_2025 is not None:
            rev[idx_2025], cost[idx_2025] = r25, c25
        out[name] = {"收入": rev, "成本": cost}
    return out


def build_extra(years: list) -> dict:
    """客户集中度：第一大客户占比（年报披露值）"""
    n = len(years)
    top1 = [CUSTOMER_TOP1.get(int(y)) for y in years]
    return {"第一大客户占比": top1}


def apply_to_session(years: list):
    import streamlit as st
    st.session_state.segments = build_segments(list(years))
    st.session_state.extra_metrics = build_extra(list(years))
