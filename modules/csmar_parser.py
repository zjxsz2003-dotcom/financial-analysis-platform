"""
CSMAR 财务报表解析器
支持 CSMAR 标准导出格式：Row 0=字段代码, Row 1=中文名称, Row 2=单位, Row 3+=数据
"""
import pandas as pd
import numpy as np
import re
from pathlib import Path


class CSMARParser:
    """CSMAR 标准格式解析器"""

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path) if base_path else None
        self.yuan_to_yi = 1e8  # 元 → 亿元

    def parse_balance_sheet(self, file_path: str = None) -> pd.DataFrame:
        """解析资产负债表，返回年度数据 DataFrame（亿元）"""
        path = file_path or str(self.base_path / "FS_Combas.xlsx")
        df = pd.read_excel(path, header=None)

        # 用 Row 1 的中文名称作为列索引
        col_names = df.iloc[1, :].tolist()
        data = df.iloc[3:, :].copy()
        data.columns = col_names

        # 筛选年报（12-31）
        annual = data[data["统计截止日期"].astype(str).str.contains("12-31")].copy()

        # 目标科目映射
        target_items = {
            "资产总计": ["资产总计"],
            "流动资产合计": ["流动资产合计"],
            "货币资金": ["货币资金"],
            "应收账款净额": ["应收账款净额"],
            "存货净额": ["存货净额"],
            "固定资产净额": ["固定资产净额"],
            "在建工程净额": ["在建工程净额"],
            "无形资产净额": ["无形资产净额"],
            "负债合计": ["负债合计"],
            "流动负债合计": ["流动负债合计"],
            "短期借款": ["短期借款"],
            "应付账款": ["应付账款"],
            "长期借款": ["长期借款"],
            "股东权益合计": ["所有者权益合计", "股东权益合计"],
            "归属于母公司所有者权益合计": ["归属于母公司所有者权益合计"],
            "实收资本（或股本）": ["实收资本(或股本)", "实收资本（或股本）"],
            "未分配利润": ["未分配利润"],
        }

        result = {"年份": annual["统计截止日期"].apply(lambda x: int(str(x)[:4])).tolist()}

        for key, candidates in target_items.items():
            found = None
            for c in candidates:
                if c in annual.columns:
                    found = c
                    break
            if found:
                result[key] = (annual[found].astype(float) / self.yuan_to_yi).round(2).tolist()
            else:
                result[key] = [0] * len(annual)

        return pd.DataFrame(result)

    def parse_income_statement(self, file_path: str = None) -> pd.DataFrame:
        """解析利润表，返回年度数据 DataFrame（亿元）"""
        path = file_path or str(self.base_path / "FS_Comins.xlsx")
        df = pd.read_excel(path, header=None)

        col_names = df.iloc[1, :].tolist()
        data = df.iloc[3:, :].copy()
        data.columns = col_names

        annual = data[data["统计截止日期"].astype(str).str.contains("12-31")].copy()

        target_items = {
            "营业收入": ["营业收入"],
            "营业成本": ["营业成本"],
            "税金及附加": ["税金及附加"],
            "销售费用": ["销售费用"],
            "管理费用": ["管理费用"],
            "研发费用": ["研发费用"],
            "财务费用": ["财务费用"],
            "营业利润": ["营业利润"],
            "利润总额": ["利润总额"],
            "所得税费用": ["所得税费用"],
            "净利润": ["净利润"],
            "归母净利润": ["归属于母公司所有者的净利润"],
            "基本每股收益": ["基本每股收益"],
        }

        result = {"年份": annual["统计截止日期"].apply(lambda x: int(str(x)[:4])).tolist()}

        for key, candidates in target_items.items():
            found = None
            for c in candidates:
                if c in annual.columns:
                    found = c
                    break
            if found:
                val = annual[found].astype(float)
                # 每股收益保持元，其他转为亿元
                if key == "基本每股收益":
                    result[key] = val.round(2).tolist()
                else:
                    result[key] = (val / self.yuan_to_yi).round(2).tolist()
            else:
                result[key] = [0] * len(annual)

        return pd.DataFrame(result)

    def parse_cashflow(self, file_path: str = None) -> pd.DataFrame:
        """解析现金流量表（直接法），返回年度数据 DataFrame（亿元）"""
        path = file_path or str(self.base_path / "FS_Comscfd.xlsx")
        df = pd.read_excel(path, header=None)

        col_names = df.iloc[1, :].tolist()
        data = df.iloc[3:, :].copy()
        data.columns = col_names

        annual = data[data["统计截止日期"].astype(str).str.contains("12-31")].copy()

        target_items = {
            "经营现金流入": ["经营活动产生的现金流量流入", "经营活动现金流入小计"],
            "经营现金流出": ["经营活动产生的现金流量流出", "经营活动现金流出小计"],
            "经营现金流量净额": ["经营活动产生的现金流量净额"],
            "投资现金流入": ["投资活动产生的现金流量流入", "投资活动现金流入小计"],
            "投资现金流出": ["投资活动产生的现金流量流出", "投资活动现金流出小计"],
            "投资现金流量净额": ["投资活动产生的现金流量净额"],
            "筹资现金流入": ["筹资活动产生的现金流量流入", "筹资活动现金流入小计"],
            "筹资现金流出": ["筹资活动产生的现金流量流出", "筹资活动现金流出小计"],
            "筹资现金流量净额": ["筹资活动产生的现金流量净额"],
        }

        result = {"年份": annual["统计截止日期"].apply(lambda x: int(str(x)[:4])).tolist()}

        for key, candidates in target_items.items():
            found = None
            for c in candidates:
                if c in annual.columns:
                    found = c
                    break
            if found:
                result[key] = (annual[found].astype(float) / self.yuan_to_yi).round(2).tolist()
            else:
                # 尝试从数据中搜索匹配
                matched = [col for col in annual.columns if key.split("净额")[0] in str(col) and "净额" in str(col)]
                if matched:
                    result[key] = (annual[matched[0]].astype(float) / self.yuan_to_yi).round(2).tolist()
                else:
                    result[key] = [0] * len(annual)

        # 计算资本开支（购建固定资产支付现金）
        capex_cols = [c for c in annual.columns if "购建固定" in str(c) or "购建固定资产" in str(c)]
        if capex_cols:
            result["资本开支"] = (annual[capex_cols[0]].astype(float) / self.yuan_to_yi).round(2).tolist()
        else:
            result["资本开支"] = [0] * len(annual)

        return pd.DataFrame(result)

    def parse_all(self, base_path: str = None) -> dict:
        """解析全部报表，返回标准化的 DataFrames"""
        if base_path:
            self.base_path = Path(base_path)

        results = {
            "balance_sheet": self.parse_balance_sheet(),
            "income_statement": self.parse_income_statement(),
            "cashflow": self.parse_cashflow(),
            "company_name": self._get_company_name(),
            "company_code": self._get_company_code(),
        }
        return results

    def _get_company_name(self) -> str:
        """获取公司名称"""
        path = str(self.base_path / "FS_Combas.xlsx") if self.base_path else "FS_Combas.xlsx"
        df = pd.read_excel(path, header=None)
        return str(df.iloc[3, 1])  # Row 3, Col 1 = ShortName

    def _get_company_code(self) -> str:
        """获取股票代码"""
        path = str(self.base_path / "FS_Combas.xlsx") if self.base_path else "FS_Combas.xlsx"
        df = pd.read_excel(path, header=None)
        return str(df.iloc[3, 0])  # Row 3, Col 0 = Stkcd


def auto_detect_and_parse(uploaded_files: dict) -> dict:
    """
    自动检测上传文件类型并解析
    uploaded_files: {"文件名": file_bytes_or_path, ...}
    返回标准化的解析结果
    """
    file_mapping = {
        "balance_sheet": [],
        "income_statement": [],
        "cashflow": [],
    }

    # 文件名关键词匹配
    for fname in uploaded_files.keys():
        fname_lower = fname.lower()
        if any(kw in fname_lower for kw in ["bas", "balance", "资产负债", "combas"]):
            file_mapping["balance_sheet"].append(fname)
        elif any(kw in fname_lower for kw in ["ins", "income", "利润", "comins"]):
            file_mapping["income_statement"].append(fname)
        elif any(kw in fname_lower for kw in ["scfd", "scfi", "cash", "现金", "comscf"]):
            file_mapping["cashflow"].append(fname)

    # 解析
    parser = CSMARParser()
    result = {}

    for fname, file_path in uploaded_files.items():
        if fname in file_mapping["balance_sheet"]:
            result["balance_sheet"] = parser.parse_balance_sheet(file_path)
        elif fname in file_mapping["income_statement"]:
            result["income_statement"] = parser.parse_income_statement(file_path)
        elif fname in file_mapping["cashflow"]:
            result["cashflow"] = parser.parse_cashflow(file_path)

    return result
