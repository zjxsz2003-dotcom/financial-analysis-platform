"""
AI 文字润色（可选）— 防幻觉机制
原则：AI 只负责组织语言，数值必须来自系统计算结果，输出后做数字校验
"""
from __future__ import annotations
import os
import re

SYSTEM_PROMPT = """你是一位资深 FP&A 负责人，为管理层撰写经营分析报告。

严格规则（违反即视为失败）：
1. 只能使用我提供的数值，不得编造、推算、修改任何数字
2. 引用数据必须与提供值完全一致（含小数位与单位）
3. 不得虚构趋势、不得提及未提供的数据来源
4. 不得给出未在数据中体现的量化预测
5. 不确定时使用"建议进一步核实""有待验证"等措辞

输出要求：
1. 中文，专业简洁，面向管理层，250-400 字
2. 先一句总览，再 3-4 条关键发现，最后 1-2 条管理建议
3. 不要用"本报告""综上所述"开头"""


def _client():
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("DEEPSEEK_API_KEY", "")
        except Exception:
            pass
    if not key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=key, base_url="https://api.deepseek.com")
    except Exception:
        return None


def _check(text: str, allowed: set) -> list:
    """找出文本中出现但不在合法集合中的数字"""
    bad = []
    for n in re.findall(r"\d+(?:\.\d+)?", text):
        try:
            f = float(n)
        except ValueError:
            continue
        if f > 1900 or f < 0.005:
            continue          # 年份 / 极小值跳过
        if not any(abs(f - a) < 0.15 for a in allowed):
            bad.append(n)
    return bad


def polish(facts: dict, alerts: list, company: str, period: str) -> dict:
    """
    facts: {"指标名": "带单位的字符串"}  —— 系统计算的合法数值池
    返回 {"text","ai","suspicious"}
    """
    allowed = set()
    for v in facts.values():
        for n in re.findall(r"\d+(?:\.\d+)?", str(v)):
            try:
                allowed.add(float(n))
            except ValueError:
                pass
    for a in alerts:
        for n in re.findall(r"\d+(?:\.\d+)?", str(a.get("value", ""))):
            try:
                allowed.add(float(n))
            except ValueError:
                pass

    fallback = _template(facts, alerts, company, period)
    cli = _client()
    if not cli:
        return {"text": fallback, "ai": False, "suspicious": []}

    fact_txt = "\n".join(f"- {k}：{v}" for k, v in facts.items())
    alert_txt = "\n".join(
        f"- {'红色预警' if a.get('status')=='danger' else '黄色关注'} {a.get('name')}：{a.get('value')}{a.get('unit','')}"
        for a in alerts) or "本期未触发预警"
    prompt = f"公司：{company}\n期间：{period}\n\n【核心指标】\n{fact_txt}\n\n【预警信号】\n{alert_txt}\n\n请撰写执行摘要。"

    try:
        resp = cli.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": prompt}],
            temperature=0.4, max_tokens=700)
        txt = resp.choices[0].message.content.strip()
        bad = _check(txt, allowed)
        if bad:
            return {"text": fallback + f"\n\n> ⚠️ AI 输出含校验未通过的数值（{', '.join(bad[:5])}），已回退为系统模板。",
                    "ai": False, "suspicious": bad}
        return {"text": txt + "\n\n*🤖 AI 辅助撰写（数值已校验）*", "ai": True, "suspicious": []}
    except Exception:
        return {"text": fallback, "ai": False, "suspicious": []}


def _template(facts: dict, alerts: list, company: str, period: str) -> str:
    lines = [f"{company} {period} 经营情况如下："]
    for k, v in list(facts.items())[:8]:
        lines.append(f"- {k}：{v}")
    danger = [a for a in alerts if a.get("status") == "danger"]
    warn = [a for a in alerts if a.get("status") == "warning"]
    if danger:
        lines.append("\n**需优先处理：**")
        for a in danger[:4]:
            lines.append(f"- 🔴 {a.get('name')} {a.get('value')}{a.get('unit','')} 触发红色预警")
    elif warn:
        lines.append("\n**建议关注：**")
        for a in warn[:4]:
            lines.append(f"- 🟡 {a.get('name')} {a.get('value')}{a.get('unit','')} 处于关注区间")
    else:
        lines.append("\n本期核心指标均未触发预警阈值。")
    lines.append("\n*📋 系统模板生成（未配置 AI 或 AI 输出未通过校验）*")
    return "\n".join(lines)
