"""
数据完整性校验器
确保上传的财务数据满足分析所需的最小字段集合
"""
import pandas as pd


REQUIRED_BS_FIELDS = [
    "资产总计", "流动资产合计", "货币资金", "应收账款净额", "存货净额",
    "固定资产净额", "负债合计", "流动负债合计", "短期借款",
    "应付账款", "长期借款", "股东权益合计",
]

REQUIRED_IS_FIELDS = [
    "营业收入", "营业成本", "销售费用", "管理费用",
    "研发费用", "财务费用", "营业利润", "利润总额", "净利润",
]

REQUIRED_CF_FIELDS = [
    "经营现金流量净额",
]


def validate_balance_sheet(df: pd.DataFrame) -> dict:
    """校验资产负债表"""
    missing = [f for f in REQUIRED_BS_FIELDS if f not in df.columns]
    warnings = []

    # 勾稽关系校验
    if "流动资产合计" in df.columns and "资产总计" in df.columns:
        ratio = df["流动资产合计"] / df["资产总计"]
        if ratio.max() > 1.0:
            warnings.append("流动资产合计 > 资产总计，数据可能异常")

    return {
        "valid": len(missing) == 0,
        "missing_fields": missing,
        "warnings": warnings,
        "row_count": len(df),
        "year_range": f"{df['年份'].min()}-{df['年份'].max()}" if "年份" in df.columns else "N/A",
    }


def validate_income_statement(df: pd.DataFrame) -> dict:
    """校验利润表"""
    missing = [f for f in REQUIRED_IS_FIELDS if f not in df.columns]
    warnings = []

    # 勾稽关系：收入-成本-费用 ≈ 营业利润
    if all(f in df.columns for f in ["营业收入", "营业成本", "营业利润"]):
        gross = df["营业收入"] - df["营业成本"]
        profit_ratio = abs(df["营业利润"] / gross).replace([float("inf"), -float("inf")], 0)
        if profit_ratio.max() > 5:
            warnings.append("营业利润与毛利差距较大，请检查费用科目是否完整")

    return {
        "valid": len(missing) == 0,
        "missing_fields": missing,
        "warnings": warnings,
        "row_count": len(df),
        "year_range": f"{df['年份'].min()}-{df['年份'].max()}" if "年份" in df.columns else "N/A",
    }


def validate_cashflow(df: pd.DataFrame) -> dict:
    """校验现金流量表"""
    missing = [f for f in REQUIRED_CF_FIELDS if f not in df.columns]
    return {
        "valid": len(missing) == 0,
        "missing_fields": missing,
        "warnings": [],
        "row_count": len(df),
        "year_range": f"{df['年份'].min()}-{df['年份'].max()}" if "年份" in df.columns else "N/A",
    }


def validate_all(balance_sheet: pd.DataFrame, income_statement: pd.DataFrame,
                 cashflow: pd.DataFrame) -> dict:
    """校验全部报表"""
    bs_result = validate_balance_sheet(balance_sheet)
    is_result = validate_income_statement(income_statement)
    cf_result = validate_cashflow(cashflow)

    # 跨表校验：年份一致性
    cross_warnings = []
    if "年份" in balance_sheet.columns and "年份" in income_statement.columns:
        bs_years = set(balance_sheet["年份"])
        is_years = set(income_statement["年份"])
        if bs_years != is_years:
            cross_warnings.append(f"资产负债表和利润表年份不一致: BS {bs_years}, IS {is_years}")

    # 跨表校验：净利润一致性
    if "净利润" in income_statement.columns and "未分配利润" in balance_sheet.columns:
        pass  # 此处可扩展更复杂的勾稽校验

    all_valid = bs_result["valid"] and is_result["valid"] and cf_result["valid"]
    all_missing = (bs_result["missing_fields"] + is_result["missing_fields"] +
                   cf_result["missing_fields"])
    all_warnings = (bs_result["warnings"] + is_result["warnings"] +
                    cf_result["warnings"] + cross_warnings)

    return {
        "all_valid": all_valid,
        "balance_sheet": bs_result,
        "income_statement": is_result,
        "cashflow": cf_result,
        "all_missing_fields": all_missing,
        "all_warnings": all_warnings,
        "cross_table_warnings": cross_warnings,
    }
