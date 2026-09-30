"""
财务报表解析器 — 通用版（V2）
支持三类输入：
  1) CSMAR 标准导出（第0行字段代码 / 第1行中文名 / 第2行单位 / 第3行起数据）
  2) 简版纵向表：首列=年份，其余列=科目
  3) 简版横向表：首列=科目，其余列=年份
输出统一为：{"年份": [...], 标准科目: [...]} 的 DataFrame，单位=亿元
"""
from __future__ import annotations
import re
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from config import ITEM_ALIASES

YI = 1e8

# 各类报表的目标科目
INCOME_KEYS = ["营业收入", "营业成本", "税金及附加", "销售费用", "管理费用", "研发费用",
               "财务费用", "营业利润", "营业外收入", "营业外支出", "利润总额",
               "所得税费用", "净利润", "归母净利润"]
BALANCE_KEYS = ["货币资金", "应收账款净额", "存货净额", "流动资产合计", "固定资产净额",
                "在建工程净额", "无形资产净额", "资产总计", "短期借款",
                "一年内到期非流动负债", "应付账款", "流动负债合计", "长期借款",
                "应付债券", "负债合计", "实收资本", "未分配利润", "归母权益",
                "股东权益合计"]
CASH_KEYS = ["销售商品收到的现金", "经营现金流入", "经营现金流出", "经营现金流量净额",
             "投资现金流量净额", "筹资现金流量净额", "资本开支", "支付给职工的现金"]
INDIRECT_KEYS = ["折旧摊销", "资产减值准备", "财务费用", "净利润"]

# 折旧摊销的多个来源列（间接法）
DA_COLS = ["固定资产折旧、油气资产折耗、生产性生物资产折旧", "投资性房地产折旧及摊销",
           "使用权资产折旧及摊销", "无形资产摊销", "长期待摊费用摊销", "折旧摊销"]

_YEAR_PAT = re.compile(r"(19|20)\d{2}")


# ════════════════════════════════════════════════════════════
# 工具
# ════════════════════════════════════════════════════════════
def _norm(s) -> str:
    return str(s).replace(" ", "").replace("　", "").strip()


def _match_col(columns, aliases) -> Optional[str]:
    """精确匹配 → 去空格匹配 → 包含匹配"""
    norm_map = {_norm(c): c for c in columns}
    for a in aliases:
        na = _norm(a)
        if na in norm_map:
            return norm_map[na]
    for a in aliases:
        na = _norm(a)
        for nc, c in norm_map.items():
            if na and na in nc:
                return c
    return None


def _to_year(v) -> Optional[int]:
    s = str(v)
    m = _YEAR_PAT.search(s)
    return int(m.group(0)) if m else None


def _money_scale(unit_row) -> float:
    """根据单位行判断缩放：元→1/1e8，万元→1/1e4，亿元/百万元"""
    vals = [str(u) for u in unit_row if str(u) != "nan"]
    joined = "".join(vals)
    if "亿元" in joined:
        return 1.0
    if "百万元" in joined:
        return 1e6 / YI
    if "万元" in joined:
        return 1e4 / YI
    return 1.0 / YI  # 默认元


# ════════════════════════════════════════════════════════════
# 读取三种格式
# ════════════════════════════════════════════════════════════
def _read_raw(path) -> pd.DataFrame:
    p = str(path)
    return pd.read_excel(p, header=None) if not p.lower().endswith(".csv") else pd.read_csv(p, header=None)


def looks_like_csmar(raw: pd.DataFrame) -> bool:
    if raw.shape[0] < 4:
        return False
    r1 = raw.iloc[1, :].astype(str).tolist()
    r2 = raw.iloc[2, :].astype(str).tolist()
    has_unit_words = any("单位" in x or x == "元" or "万元" in x for x in r2)
    has_names = sum(1 for x in r1 if len(x) >= 2 and not x.replace(".", "").isdigit()) > 3
    return has_unit_words and has_names


def parse_csmar(raw: pd.DataFrame) -> pd.DataFrame:
    """CSMAR：返回以中文列名为列的年度数据（原始单位→亿元）"""
    cols = raw.iloc[1, :].tolist()
    data = raw.iloc[3:, :].copy()
    data.columns = [_norm(c) for c in cols]

    date_col = _match_col(data.columns, ["统计截止日期", "会计期间", "报告期", "日期"])
    if date_col is None:
        # 退化：取第一列为期间
        date_col = data.columns[0]
    date_col = _norm(date_col)

    scale = _money_scale(raw.iloc[2, :].tolist())

    data["_year"] = data[date_col].map(_to_year)
    # 年度口径：保留 12-31 的行；若没有则按年份去重取最大日期
    dcol_str = data[date_col].astype(str)
    annual = data[dcol_str.str.contains("12-31", na=False)].copy()
    if annual.empty:
        annual = data.dropna(subset=["_year"]).copy()
    annual = annual[annual["_year"].notna()]
    annual["_year"] = annual["_year"].astype(int)
    # 同年多报表类型 → 取最后一条（通常为更正后/合并口径）
    annual = annual.drop_duplicates(subset=["_year"], keep="last").sort_values("_year")

    out = pd.DataFrame({"年份": annual["_year"].tolist()})
    for c in annual.columns:
        if c in ("_year", date_col):
            continue
        vals = pd.to_numeric(annual[c], errors="coerce")
        out[_norm(c)] = (vals * scale).round(4).tolist()
    return out.reset_index(drop=True)


def parse_simple(raw: pd.DataFrame) -> pd.DataFrame:
    """
    简版：
      A) 首列=年份 → 行=年份、列=科目（转置为 科目×年份）
      B) 首列=科目 → 行=科目、列=年份
    返回 DataFrame(年份, 科目...)
    """
    df = raw.copy()
    # 去掉全空行列
    df = df.dropna(how="all").dropna(how="all", axis=1)
    if df.empty:
        return pd.DataFrame()

    first = df.iloc[:, 0]
    first_str = first.astype(str).map(_norm)

    # A) 首列是年份
    year_hits = first_str.map(lambda s: bool(re.fullmatch(r"(19|20)\d{2}(\D.*)?", s))).sum()
    if year_hits >= max(2, len(df) * 0.5):
        years = first.map(_to_year)
        items = {}
        for j in range(1, df.shape[1]):
            col = df.iloc[:, j]
            name = _norm(df.iloc[:, j].name) if df.iloc[:, j].name is not None else ""
            if not name or name.startswith("Unnamed"):
                name = _norm(col.iloc[0]) if len(col) else f"col{j}"
            vals = pd.to_numeric(col, errors="coerce")
            items[name] = vals.tolist()
        out = pd.DataFrame({"年份": years.tolist()})
        for k, v in items.items():
            out[k] = v
        return out.dropna(subset=["年份"]).sort_values("年份").reset_index(drop=True)

    # B) 首列是科目，其余列是年份
    header_row = None
    for i in range(min(3, len(df))):
        row = df.iloc[i, 1:].astype(str).tolist()
        if sum(1 for x in row if _YEAR_PAT.search(x)) >= max(1, len(row) * 0.5):
            header_row = i
            break
    if header_row is not None:
        years = [_to_year(x) for x in df.iloc[header_row, 1:].tolist()]
        body = df.iloc[header_row + 1:, :]
        items = {}
        for _, r in body.iterrows():
            key = _norm(r.iloc[0])
            if not key:
                continue
            items[key] = pd.to_numeric(pd.Series(r.iloc[1:].tolist()), errors="coerce").tolist()
        out = pd.DataFrame({"年份": years})
        for k, v in items.items():
            out[k] = v
        out = out[out["年份"].notna()].copy()
        out["年份"] = out["年份"].astype(int)
        return out.sort_values("年份").reset_index(drop=True)

    return pd.DataFrame()


def read_statement(path) -> pd.DataFrame:
    raw = _read_raw(path)
    if looks_like_csmar(raw):
        return parse_csmar(raw)
    return parse_simple(raw)


# ════════════════════════════════════════════════════════════
# 标准化：抽取标准科目
# ════════════════════════════════════════════════════════════
def standardize(df: pd.DataFrame, keys) -> pd.DataFrame:
    if df is None or df.empty or "年份" not in df.columns:
        return pd.DataFrame(columns=["年份"] + list(keys))
    cols = [_norm(c) for c in df.columns]
    df2 = df.copy()
    df2.columns = cols
    out = pd.DataFrame({"年份": df2["年份"].tolist()})
    for k in keys:
        aliases = ITEM_ALIASES.get(k, [k])
        col = _match_col(cols, aliases)
        if col:
            out[k] = pd.to_numeric(df2[col], errors="coerce").round(4).tolist()
        else:
            out[k] = [np.nan] * len(df2)
    return out


def extract_da(cf_direct: pd.DataFrame, cf_indirect: Optional[pd.DataFrame]) -> list:
    """折旧摊销：优先间接法明细加总，其次 '折旧摊销' 列"""
    if cf_indirect is not None and not cf_indirect.empty:
        cols = [_norm(c) for c in cf_indirect.columns]
        total = None
        for c in DA_COLS:
            nc = _norm(c)
            if nc in cols:
                v = pd.to_numeric(cf_indirect[cf_indirect.columns[cols.index(nc)]], errors="coerce").fillna(0).to_numpy()
                total = v if total is None else total + v
        if total is not None and np.nansum(np.abs(total)) > 0:
            return np.round(total, 4).tolist()
    if cf_direct is not None and "折旧摊销" in cf_direct.columns:
        return pd.to_numeric(cf_direct["折旧摊销"], errors="coerce").tolist()
    return []


# ════════════════════════════════════════════════════════════
# 主入口
# ════════════════════════════════════════════════════════════
def parse_folder(base: str) -> dict:
    """解析 CSMAR 导出的三张（或四张）表"""
    p = Path(base)
    res = {"company_name": "", "company_code": "", "years": []}

    def find(*pats):
        for pat in pats:
            for f in p.glob(pat):
                return f
        return None

    f_bs = find("FS_Combas*.xlsx", "*资产负债*.xlsx", "*bas*.xlsx", "*资产*.xlsx")
    f_is = find("FS_Comins*.xlsx", "*利润*.xlsx", "*ins*.xlsx")
    f_cf = find("FS_Comscfd*.xlsx", "FS_Comscf*.xlsx", "*现金流*.xlsx", "*scfd*.xlsx")
    f_ci = find("FS_Comscfi*.xlsx", "*间接*.xlsx")

    raw_bs = read_statement(f_bs) if f_bs else pd.DataFrame()
    raw_is = read_statement(f_is) if f_is else pd.DataFrame()
    raw_cf = read_statement(f_cf) if f_cf else pd.DataFrame()
    raw_ci = read_statement(f_ci) if f_ci else pd.DataFrame()

    # 公司名 / 代码
    try:
        r = _read_raw(f_bs)
        cols = [_norm(c) for c in r.iloc[1, :].tolist()]
        d = r.iloc[3:, :]
        d.columns = cols
        res["company_name"] = str(d.iloc[0][_match_col(cols, ["证券简称", "公司名称", "简称"]) or cols[1]])
        res["company_code"] = str(d.iloc[0][_match_col(cols, ["证券代码", "股票代码", "代码"]) or cols[0]]).zfill(6)
    except Exception:
        pass

    bs = standardize(raw_bs, BALANCE_KEYS)
    inc = standardize(raw_is, INCOME_KEYS)
    cf = standardize(raw_cf, CASH_KEYS)

    # 折旧摊销
    da = extract_da(raw_cf, raw_ci if not raw_ci.empty else None)
    if da and len(da) == len(cf):
        cf["折旧摊销"] = da

    # 统一年份（取三表年份交集或并集的最大覆盖）
    years = None
    for d in (bs, inc, cf):
        if not d.empty:
            ys = set(int(y) for y in d["年份"].tolist())
            years = ys if years is None else (years & ys if len(years & ys) >= 2 else years | ys)
    years = sorted(years) if years else []

    def align(d: pd.DataFrame):
        if d.empty:
            return d
        return d[d["年份"].isin(years)].sort_values("年份").reset_index(drop=True)

    res["balance"] = align(bs)
    res["income"] = align(inc)
    res["cashflow"] = align(cf)
    res["years"] = years
    res["raw"] = {"bs": raw_bs, "is": raw_is, "cf": raw_cf, "ci": raw_ci}
    return res


def parse_uploaded(files: dict) -> dict:
    """
    files: {"balance": path_or_file, "income": ..., "cashflow": ..., "indirect": ...}
    """
    out = {"company_name": "", "company_code": "", "years": [], "balance": pd.DataFrame(),
           "income": pd.DataFrame(), "cashflow": pd.DataFrame()}
    raws = {}
    for key, keys in (("balance", BALANCE_KEYS), ("income", INCOME_KEYS), ("cashflow", CASH_KEYS)):
        f = files.get(key)
        if f is None:
            continue
        raw = read_statement(f)
        raws[key] = raw
        out[key] = standardize(raw, keys)
    if files.get("indirect"):
        raws["indirect"] = read_statement(files["indirect"])
    da = extract_da(raws.get("cashflow"), raws.get("indirect"))
    if da and not out["cashflow"].empty and len(da) == len(out["cashflow"]):
        out["cashflow"]["折旧摊销"] = da

    years = None
    for k in ("balance", "income", "cashflow"):
        d = out[k]
        if not d.empty:
            ys = set(int(y) for y in d["年份"].tolist())
            years = ys if years is None else (years & ys if len(years & ys) >= 2 else years | ys)
    years = sorted(years) if years else []
    for k in ("balance", "income", "cashflow"):
        if not out[k].empty:
            out[k] = out[k][out[k]["年份"].isin(years)].sort_values("年份").reset_index(drop=True)
    out["years"] = years
    out["raw"] = raws
    return out


# ════════════════════════════════════════════════════════════
# 分部数据（可选）
# ════════════════════════════════════════════════════════════
def parse_segments(path) -> dict:
    """
    分部/业务板块数据。支持两种布局：
      A) 列：年份 | 板块 | 收入 | 成本   → 长表
      B) 列：项目 | <板块1> | <板块2> ...，行含 收入/成本 → 宽表
    返回 {板块名: {"收入":[...], "成本":[...]}}  与 years 对齐
    """
    raw = _read_raw(path)
    df = raw.dropna(how="all").dropna(how="all", axis=1)
    if df.empty:
        return {}
    # 尝试把第一行当表头
    head = [_norm(x) for x in df.iloc[0, :].tolist()]
    body = df.iloc[1:, :].copy()
    body.columns = head

    col_year = _match_col(head, ["年份", "年度", "期间", "年"])
    col_seg = _match_col(head, ["板块", "业务板块", "分部", "业务", "产品线", "segment"])
    col_rev = _match_col(head, ["收入", "营业收入", "营收", "revenue"])
    col_cost = _match_col(head, ["成本", "营业成本", "cost"])

    if col_year and col_seg and col_rev:
        years = sorted({int(y) for y in body[col_year].map(_to_year).dropna()})
        segs = {}
        for seg, grp in body.groupby(body[col_seg].astype(str)):
            rev = [np.nan] * len(years)
            cost = [np.nan] * len(years)
            for _, r in grp.iterrows():
                y = _to_year(r[col_year])
                if y in years:
                    i = years.index(y)
                    rev[i] = pd.to_numeric(r[col_rev], errors="coerce")
                    if col_cost:
                        cost[i] = pd.to_numeric(r[col_cost], errors="coerce")
            segs[str(seg)] = {"收入": rev, "成本": cost}
        return {"years": years, "segments": segs}

    # 宽表：首列为项目名
    keycol = head[0]
    items = {_norm(r[keycol]): [pd.to_numeric(x, errors="coerce") for x in r.iloc[1:].tolist()]
             for _, r in body.iterrows()}
    seg_names = [h for h in head[1:] if h and not _YEAR_PAT.search(h)]
    years = [_to_year(h) for h in head[1:]]
    rev_row = _match_col(list(items.keys()), ["收入", "营业收入", "营收"])
    cost_row = _match_col(list(items.keys()), ["成本", "营业成本"])
    segs = {}
    for j, s in enumerate(seg_names):
        if not s:
            continue
        rev = items[rev_row][j] if rev_row else np.nan
        cost = items[cost_row][j] if cost_row else np.nan
        segs[s] = {"收入": [rev], "成本": [cost]}
    return {"years": years, "segments": segs} if segs else {}
