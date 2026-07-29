"""
战略目标追踪模块
KPI分解树 + 进度追踪 + What-if情景模拟
"""
import plotly.graph_objects as go
from modules.data_loader import get_strategy_targets
from config import COLORS, ALERT_COLORS


def get_strategy_progress_data() -> list:
    """获取战略目标进度数据"""
    targets = get_strategy_targets()
    result = []
    for t in targets:
        current = t["current_value"]
        target = t["target_value"]
        progress = min(round(current / target * 100, 1), 100) if target else 0

        # 判断状态
        # 假设当前为年中（6/12），时间进度50%
        time_progress = 50
        if progress >= time_progress + 10:
            status = "normal"
        elif progress >= time_progress - 10:
            status = "warning"
        else:
            status = "danger"

        result.append({
            "name": t["name"],
            "target_value": t["target_value"],
            "current_value": current,
            "unit": t["unit"],
            "progress": progress,
            "status": status,
            "kpi_tree": t.get("kpi_tree", {}),
        })
    return result


def get_strategy_progress_chart() -> go.Figure:
    """战略目标进度仪表盘图"""
    data = get_strategy_progress_data()

    fig = go.Figure()
    names = [d["name"][:12] + "..." if len(d["name"]) > 12 else d["name"] for d in data]
    progress = [d["progress"] for d in data]
    colors = [ALERT_COLORS[d["status"]] for d in data]

    fig.add_trace(go.Bar(
        y=names,
        x=progress,
        orientation="h",
        marker_color=colors,
        text=[f"{p}%" for p in progress],
        textposition="outside",
    ))

    # 时间进度参考线
    fig.add_vline(x=50, line_dash="dash", line_color=COLORS["slate"],
                  annotation_text="时间进度50%")

    fig.update_layout(
        title=dict(text="年度战略目标完成进度", font=dict(size=14, color=COLORS["ink"])),
        xaxis=dict(title="完成率(%)", range=[0, 110]),
        height=250,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def get_kpi_tree_figure(target_name: str, kpi_data: dict) -> go.Figure:
    """生成KPI分解树形图"""
    labels = [target_name]
    parents = [""]
    values = [100]

    for kpi_name, kpi_info in kpi_data.items():
        labels.append(kpi_name)
        parents.append(target_name)
        values.append(kpi_info["weight"] * 100)

        # 子指标的具体值
        sub_label = f"{kpi_name}\n(当前:{kpi_info['current']}/目标:{kpi_info['target']})"
        labels.append(sub_label)
        parents.append(kpi_name)
        values.append(kpi_info["weight"] * 50)

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        textinfo="label",
        marker=dict(colors=[COLORS["ember"]] * len(labels)),
    ))
    fig.update_layout(
        height=250,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def what_if_simulation(adjusted_margin: float = None, adjusted_rev_growth: float = None) -> dict:
    """
    What-if 情景模拟
    调整毛利率或收入增速，看对ROE和净利润的影响
    """
    from modules.data_loader import get_income, get_balance, get_years

    income = get_income()
    balance = get_balance()
    latest = get_years()[-1]

    inc_row = income[income["年份"] == latest].iloc[0]
    bal_row = balance[balance["年份"] == latest].iloc[0]
    base_revenue = float(inc_row["营业收入"])
    base_cogs = float(inc_row["营业成本"])
    base_np = float(inc_row["净利润"])
    base_equity = float(bal_row["股东权益合计"])
    base_roe = round(base_np / base_equity * 100, 1) if base_equity else 0
    base_margin = round((base_revenue - base_cogs) / base_revenue * 100, 1)

    scenarios = []

    # 情景1：毛利率变化
    if adjusted_margin:
        new_cogs = base_revenue * (1 - adjusted_margin / 100)
        gross_impact = base_cogs - new_cogs  # 成本节约
        # 简化假设：其他不变，增量直接到净利润
        new_np = base_np + gross_impact
        new_roe = round(new_np / base_equity * 100, 1) if base_equity else 0
        scenarios.append({
            "name": f"毛利率调整至{adjusted_margin}%",
            "base_margin": base_margin,
            "new_margin": adjusted_margin,
            "base_roe": base_roe,
            "new_roe": new_roe,
            "np_change": round(new_np - base_np, 1),
        })

    # 情景2：收入增速变化
    if adjusted_rev_growth:
        new_revenue = base_revenue * (1 + adjusted_rev_growth / 100)
        # 假设毛利率不变
        new_cogs = new_revenue * (1 - base_margin / 100)
        gross_change = (new_revenue - new_cogs) - (base_revenue - base_cogs)
        new_np = base_np + gross_change
        new_roe = round(new_np / base_equity * 100, 1) if base_equity else 0
        scenarios.append({
            "name": f"收入增速调整至{adjusted_rev_growth}%",
            "base_rev_growth": 0,
            "new_rev_growth": adjusted_rev_growth,
            "base_roe": base_roe,
            "new_roe": new_roe,
            "np_change": round(new_np - base_np, 1),
        })

    return {"scenarios": scenarios, "base_roe": base_roe, "base_np": base_np}
