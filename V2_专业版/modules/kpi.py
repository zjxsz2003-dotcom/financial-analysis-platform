"""
KPI 指标层 — 状态判定、行业对标、预警汇总
"""
from __future__ import annotations
from typing import Optional
from config import KPI_DIMENSIONS, KPI_META, DEFAULT_THRESHOLDS, STATUS_LABEL
from modules.data_loader import get_industry_benchmarks

# 指标 → 模型序列名
SERIES_MAP = {
    "ROE": "roe", "ROA": "roa", "毛利率": "gross_margin", "净利率": "net_margin",
    "EBIT利润率": "ebit_margin",
    "流动比率": "current_ratio", "速动比率": "quick_ratio", "现金短债比": "cash_to_short_debt",
    "资产负债率": "debt_ratio", "利息保障倍数": "interest_cover",
    "总资产周转率": "asset_turnover", "应收周转率": "ar_turnover",
    "存货周转率": "inv_turnover", "现金转换周期": "ccc",
    "收入增长率": "rev_growth", "净利增长率": "np_growth", "归母净利增长率": "npp_growth",
    "经营现金流/净利润": "ocf_to_ni", "自由现金流": "fcf",
    "收现比": "cash_recovery", "资本开支强度": "capex_intensity",
}


def _status(key: str, v) -> str:
    if v is None or v != v:
        return "na"
    meta = KPI_META.get(key)
    th = DEFAULT_THRESHOLDS.get(key, {})
    direction = th.get("dir", meta[2] if meta else 1)
    yellow, red = th.get("yellow"), th.get("red")
    if yellow is None or red is None:
        return "normal"
    if direction > 0:
        if v <= red:
            return "danger"
        if v <= yellow:
            return "warning"
    else:
        if v >= red:
            return "danger"
        if v >= yellow:
            return "warning"
    return "normal"


def snapshot(model: dict, thresholds: dict = None) -> dict:
    """
    返回 {维度: {指标: {values, current, prev, yoy, unit, status, bench, diff, better, dec}}}
    thresholds: 用户自定义阈值覆盖
    """
    if not model:
        return {}
    bench_all = get_industry_benchmarks()
    if thresholds:
        DEFAULT_THRESHOLDS.update(thresholds)
    out = {}
    for dim, keys in KPI_DIMENSIONS.items():
        out[dim] = {}
        for key in keys:
            sname = SERIES_MAP.get(key)
            vals = model.get(sname, []) if sname else []
            vals = [None if v is None else float(v) for v in vals]
            cur = next((v for v in reversed(vals) if v is not None), None)
            prev = None
            seen = [v for v in vals if v is not None]
            prev = seen[-2] if len(seen) >= 2 else None
            meta = KPI_META.get(key, (key, "", 1, 1))
            b = bench_all.get(key)
            diff = None if (cur is None or b is None) else cur - b
            better = None
            if diff is not None and abs(diff) > 1e-9:
                direction = DEFAULT_THRESHOLDS.get(key, {}).get("dir", meta[2])
                better = diff > 0 if direction > 0 else diff < 0
            out[dim][key] = {
                "values": vals, "current": cur, "prev": prev,
                "yoy": None if (cur is None or prev is None) else cur - prev,
                "unit": meta[1], "dec": meta[3], "direction": meta[2],
                "status": _status(key, cur), "bench": b, "diff": diff, "better": better,
                "name": meta[0],
            }
    return out


def flat(snap: dict) -> list:
    rows = []
    for dim, items in snap.items():
        for key, d in items.items():
            r = dict(d)
            r["dim"] = dim
            r["key"] = key
            rows.append(r)
    return rows


def alerts(snap: dict) -> list:
    res = []
    for dim, items in snap.items():
        for key, d in items.items():
            if d["status"] in ("warning", "danger"):
                res.append({"dim": dim, "key": key, "name": d["name"],
                            "status": d["status"], "value": d["current"],
                            "unit": d["unit"], "dec": d["dec"], "yoy": d["yoy"]})
    order = {"danger": 0, "warning": 1}
    res.sort(key=lambda x: order.get(x["status"], 2))
    return res


def dim_stats(snap: dict) -> list:
    out = []
    for dim, items in snap.items():
        n = w = d = na = 0
        for key, v in items.items():
            if v["status"] == "normal":
                n += 1
            elif v["status"] == "warning":
                w += 1
            elif v["status"] == "danger":
                d += 1
            else:
                na += 1
        out.append({"name": dim, "normal": n, "warning": w, "danger": d, "na": na,
                    "total": n + w + d + na})
    return out


def status_counts(snap: dict) -> dict:
    c = {"normal": 0, "warning": 0, "danger": 0, "na": 0}
    for dim, items in snap.items():
        for key, d in items.items():
            c[d["status"]] = c.get(d["status"], 0) + 1
    return c
