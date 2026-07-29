"""
预警引擎
三色预警阈值判断 + 预警触发逻辑
"""
from config import ALERT_COLORS, DEFAULT_THRESHOLDS, KPI_NAMES_CN


def get_alert_status(indicator_key: str, current_value: float, industry_mean: float = 0, industry_std: float = 1) -> str:
    """
    判断单个指标的状态
    返回: "normal" | "warning" | "danger"
    """
    thresholds = DEFAULT_THRESHOLDS.get(indicator_key, {})

    # 资产负债率：越低越好
    if indicator_key == "资产负债率":
        red_high = thresholds.get("red_high", 80)
        yellow_high = thresholds.get("yellow_high", 65)
        if current_value >= red_high:
            return "danger"
        if current_value >= yellow_high:
            return "warning"
        return "normal"

    # 其他指标：越高越好或使用行业标准差判断
    yellow_low = thresholds.get("yellow_low")
    red_low = thresholds.get("red_low")

    if yellow_low is not None and red_low is not None:
        if current_value <= red_low:
            return "danger"
        if current_value <= yellow_low:
            return "warning"
    else:
        # 使用行业均值±标准差
        if industry_std > 0:
            if current_value <= industry_mean - 1.5 * industry_std:
                return "danger"
            if current_value <= industry_mean - 0.5 * industry_std:
                return "warning"

    return "normal"


def get_alert_color(status: str) -> str:
    """获取状态对应的颜色"""
    return ALERT_COLORS.get(status, "#888888")


def get_status_description(indicator_key: str, status: str, current_value: float) -> str:
    """根据状态生成文字描述"""
    name = KPI_NAMES_CN.get(indicator_key, indicator_key)
    thresholds = DEFAULT_THRESHOLDS.get(indicator_key, {})

    if status == "danger":
        if indicator_key == "资产负债率":
            return f"🔴 **{name}** 达到 {current_value}{thresholds.get('unit','')}，超过红色预警线 {thresholds.get('red_high','')}{thresholds.get('unit','')}，偿债风险较高，建议关注负债结构和现金流状况。"
        return f"🔴 **{name}** 为 {current_value}{thresholds.get('unit','')}，低于红色预警线 {thresholds.get('red_low','')}{thresholds.get('unit','')}，需重点关注并采取改善措施。"

    if status == "warning":
        if indicator_key == "资产负债率":
            return f"🟡 **{name}** 为 {current_value}{thresholds.get('unit','')}，接近黄色关注线，建议持续监控。"
        return f"🟡 **{name}** 为 {current_value}{thresholds.get('unit','')}，处于关注区间，建议进一步分析原因并制定改善计划。"

    return f"🟢 **{name}** 为 {current_value}{thresholds.get('unit','')}，处于正常区间。"


def generate_drill_suggestions(indicator_key: str, status: str) -> list:
    """根据指标和状态，生成穿透分析建议"""
    drill_map = {
        "存货周转率": [
            {"label": "查看各业务板块存货结构", "target": "pages/1_📊_业财融合看板.py", "context": {"focus": "存货分析"}},
            {"label": "查看预算执行情况", "target": "pages/3_💰_预算偏差分析.py", "context": {"focus": "成本预算偏差"}},
        ],
        "应收周转率": [
            {"label": "查看客户集中度分析", "target": "pages/1_📊_业财融合看板.py", "context": {"focus": "客户集中度"}},
            {"label": "查看收入预算偏差", "target": "pages/3_💰_预算偏差分析.py", "context": {"focus": "收入预算偏差"}},
        ],
        "毛利率": [
            {"label": "查看各业务板块毛利率", "target": "pages/1_📊_业财融合看板.py", "context": {"focus": "毛利率分析"}},
            {"label": "查看成本预算偏差", "target": "pages/3_💰_预算偏差分析.py", "context": {"focus": "成本预算偏差"}},
        ],
        "净利率": [
            {"label": "查看费用预算执行", "target": "pages/3_💰_预算偏差分析.py", "context": {"focus": "费用预算偏差"}},
            {"label": "查看研发投入效率", "target": "pages/1_📊_业财融合看板.py", "context": {"focus": "研发投入"}},
        ],
        "ROE": [
            {"label": "查看杜邦分析拆解", "target": "pages/1_📊_业财融合看板.py", "context": {"focus": "ROE拆解"}},
            {"label": "查看战略目标进度", "target": "pages/4_🎯_战略目标追踪.py", "context": {"focus": "ROE目标"}},
        ],
        "收入增长率": [
            {"label": "查看各业务板块收入趋势", "target": "pages/1_📊_业财融合看板.py", "context": {"focus": "收入增长"}},
            {"label": "查看收入预算偏差", "target": "pages/3_💰_预算偏差分析.py", "context": {"focus": "收入预算偏差"}},
        ],
        "净利增长率": [
            {"label": "查看各业务板块毛利趋势", "target": "pages/1_📊_业财融合看板.py", "context": {"focus": "利润分析"}},
            {"label": "查看战略目标进度", "target": "pages/4_🎯_战略目标追踪.py", "context": {"focus": "利润目标"}},
        ],
    }

    default_suggestions = [
        {"label": "查看业财融合看板", "target": "pages/1_📊_业财融合看板.py", "context": {"focus": indicator_key}},
        {"label": "查看预算偏差分析", "target": "pages/3_💰_预算偏差分析.py", "context": {"focus": indicator_key}},
    ]

    if status == "normal":
        return []

    return drill_map.get(indicator_key, default_suggestions)
