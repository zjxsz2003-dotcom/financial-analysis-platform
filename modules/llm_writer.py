"""
AI文本生成模块 v2 — 防幻觉机制
核心原则：AI只写文字，不碰数字
"""
import os
import re
from openai import OpenAI

# 严格控制AI行为的System Prompt
SYSTEM_PROMPT = """你是一位资深企业财务分析专家（FP&A），为管理层撰写经营分析报告。

**严格规则（违反将导致输出被拒绝）：**
1. 只能使用我提供的指标数据，不得编造、推测、修改任何数值
2. 引用数据时必须与提供值完全一致，包括小数位数和单位
3. 不得虚构趋势（如"连续三年增长"除非我明确提供了三年数据）
4. 不得提及未经提供的数据源（如"根据年报""数据显示"除非我在prompt中标注）
5. 不得量化未提供的信息（如"预计增长X%"）
6. 不确定时使用"建议关注""有待进一步分析"等措辞

**输出要求：**
1. 语言专业简洁，适合管理层阅读（200-300字）
2. 先总览（一句话），再3-4点关键发现
3. 对预警信号给出管理建议
4. 不要"本报告"开头，直接切入正题"""


def get_deepseek_client():
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("DEEPSEEK_API_KEY", "")
        except:
            pass
    if api_key:
        return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    return None


def validate_ai_output(text: str, known_values: set) -> dict:
    """
    AI输出校验：扫描AI生成文本中的数字，标记不在已知值集合中的可疑数字
    known_values: 所有系统计算的合法数值集合
    """
    # 提取所有数字（含小数）
    numbers_found = re.findall(r'\d+\.?\d*', text)
    suspicious = []
    verified = []

    for n in numbers_found:
        f = float(n)
        # 检查是否在已知值中（容差0.1）
        matched = False
        for kv in known_values:
            try:
                if abs(float(kv) - f) < 0.15:
                    matched = True
                    verified.append(n)
                    break
            except (ValueError, TypeError):
                pass
        if not matched:
            # 跳过明显不是财务数字的（年份、百分比符号中的数字等）
            if f > 1900 or f < 0.01:  # 年份或太小的数字
                continue
            suspicious.append(n)

    return {
        "has_suspicious": len(suspicious) > 0,
        "suspicious_values": suspicious,
        "verified_count": len(verified),
        "total_numbers": len(numbers_found),
    }


def collect_known_values(highlights: dict, alerts: list) -> set:
    """从系统计算数据中收集所有合法数值"""
    known = set()
    for v in highlights.values():
        # 提取数字
        nums = re.findall(r'\d+\.?\d*', str(v))
        for n in nums:
            known.add(float(n))
    for a in alerts:
        val = str(a.get("value", ""))
        nums = re.findall(r'\d+\.?\d*', val)
        for n in nums:
            known.add(float(n))
    return known


def generate_report_summary(company_name: str, period: str, report_type: str,
                            highlights: dict, alerts: list) -> dict:
    """
    生成报告摘要（含防幻觉校验结果）
    返回: {"text": "...", "ai_generated": True/False, "validation": {...}, "label": "🤖 AI" / "📋 模板"}
    """
    client = get_deepseek_client()

    alert_text = ""
    if alerts:
        alert_items = []
        for a in alerts:
            icon = "🔴" if a["status"] == "danger" else "🟡"
            alert_items.append(f"- {icon} {a['indicator']}: {a['value']}")
        alert_text = "\n".join(alert_items)
    else:
        alert_text = "本期未触发重大预警"

    highlight_text = "\n".join([f"- {k}: {v}" for k, v in highlights.items()])

    prompt = f"""公司：{company_name} | 期间：{period} | 类型：{report_type}

【核心指标】
{highlight_text}

【预警信号】
{alert_text}

请撰写报告摘要。"""

    if client:
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,  # 降低温度减少幻觉
                max_tokens=600,
            )
            ai_text = response.choices[0].message.content

            # 校验输出
            known_vals = collect_known_values(highlights, alerts)
            validation = validate_ai_output(ai_text, known_vals)

            # 标注来源
            labeled_text = f"{ai_text}\n\n---\n*🤖 AI辅助分析 | 数据已校验*"
            if validation["has_suspicious"]:
                labeled_text += f"\n*⚠️ 检测到可能异常数值：{', '.join(validation['suspicious_values'][:5])}*"

            return {
                "text": labeled_text,
                "ai_generated": True,
                "validation": validation,
                "label": "🤖 AI生成（已校验）",
            }
        except Exception:
            pass

    # Fallback
    fallback_text = _template_summary(company_name, period, highlights, alerts)
    return {
        "text": fallback_text,
        "ai_generated": False,
        "validation": {"has_suspicious": False, "suspicious_values": []},
        "label": "📋 模板生成（API未配置）",
    }


def _template_summary(company: str, period: str, highlights: dict, alerts: list) -> str:
    """备选模板——所有数字来自系统计算"""
    lines = [f"{company}{period}经营表现总体平稳。"]

    # 用真实数据填充模板
    for k, v in list(highlights.items())[:5]:
        lines.append(f"- {k}：{v}")

    danger = [a for a in alerts if a["status"] == "danger"]
    warning = [a for a in alerts if a["status"] == "warning"]

    if danger:
        lines.append(f"\n**需重点关注：**")
        for a in danger:
            lines.append(f"- 🔴 {a['indicator']}触发红色预警（{a['value']}），建议优先处理")
    elif warning:
        lines.append(f"\n**建议关注：**")
        for a in warning:
            lines.append(f"- 🟡 {a['indicator']}处于关注区间（{a['value']}），建议持续监控")
    else:
        lines.append(f"\n**本期无预警信号触发。**")

    lines.append(f"\n---\n*📋 系统模板生成 | 数据来源：CSMAR/Wind公开披露*")
    return "\n".join(lines)


def generate_kpi_commentary(indicator_name: str, current_value, unit: str,
                            status: str, trend: str, known_reasons: list = None) -> dict:
    """
    为单个KPI生成简短AI解读
    """
    client = get_deepseek_client()

    if not client:
        return {
            "text": _template_kpi_comment(indicator_name, current_value, unit, status),
            "ai_generated": False,
            "label": "📋",
        }

    status_cn = {"normal": "正常", "warning": "关注", "danger": "预警"}.get(status, "")
    trend_cn = {"up": "上升", "down": "下降", "stable": "稳定"}.get(trend, "")

    reasons_text = ""
    if known_reasons:
        reasons_text = "可能原因：" + "、".join(known_reasons)

    prompt = f"""指标：{indicator_name}
当前值：{current_value}{unit}
状态：{status_cn}
趋势：{trend_cn}
{reasons_text}

请用1-2句话简要分析该指标（50字以内）。只能使用上述数据，不得编造。"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=150,
        )
        text = response.choices[0].message.content

        # 简单校验
        known = {float(current_value) if isinstance(current_value, (int, float)) else 0}
        validation = validate_ai_output(text, known)

        label = "🤖" if not validation["has_suspicious"] else "🤖⚠️"
        return {"text": text, "ai_generated": True, "label": label}
    except:
        return {
            "text": _template_kpi_comment(indicator_name, current_value, unit, status),
            "ai_generated": False,
            "label": "📋",
        }


def _template_kpi_comment(name: str, value, unit: str, status: str) -> str:
    """KPI解读模板"""
    if status == "danger":
        return f"{name}为{value}{unit}，触发红色预警，需重点关注并制定改善计划。"
    elif status == "warning":
        return f"{name}为{value}{unit}，处于关注区间，建议持续监控趋势变化。"
    return f"{name}为{value}{unit}，处于正常区间。"
