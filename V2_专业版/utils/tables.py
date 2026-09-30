"""
专业财务报表渲染器 — 企业蓝白版
用 HTML 表格替代 st.dataframe，实现：右对齐数字、等宽数字、小计/合计层级、
负数红色、斑马纹、悬停高亮、缩进层级 —— 达到事务所/投行底稿的观感
"""
from __future__ import annotations
from typing import Sequence, Optional
import html
import re
import pandas as pd
import streamlit as st

from config import C

DASH = "—"

# ════════════════════════════════════════════════════════════
# 数值格式化
# ════════════════════════════════════════════════════════════
def _is_num(v) -> bool:
    try:
        if v is None:
            return False
        f = float(v)
        return f == f  # not NaN
    except (TypeError, ValueError):
        return False


def num(v, dec: int = 1, dash: str = DASH) -> str:
    """千分位数值。None/NaN → —"""
    if not _is_num(v):
        return dash
    f = float(v)
    if abs(f) < 10 ** (-dec - 1):
        f = 0.0
    return f"{f:,.{dec}f}"


def pct(v, dec: int = 1, dash: str = DASH) -> str:
    if not _is_num(v):
        return dash
    return f"{float(v):.{dec}f}%"


def delta(v, dec: int = 1, unit: str = "", arrow: bool = True) -> str:
    """变化量文本：+12.3 / -4.5"""
    if not _is_num(v):
        return DASH
    f = float(v)
    s = f"{f:+,.{dec}f}{unit}"
    if arrow:
        s = ("▲ " if f > 0 else ("▼ " if f < 0 else "— ")) + s.lstrip("+-")
    return s


def signed(v, dec: int = 1) -> str:
    return num(v, dec) if not _is_num(v) or float(v) >= 0 else f"({num(abs(float(v)), dec)})"


def cell_cls(v) -> str:
    """根据数值返回单元格 class：neg / pos / ''"""
    if not _is_num(v):
        return ""
    f = float(v)
    if f < 0:
        return "neg"
    return ""


def cell_cls_text(s: str) -> str:
    """对已格式化字符串判断正负"""
    t = s.replace(",", "").replace("%", "").strip()
    if t.startswith("(") or t.startswith("-") or t.startswith("▼"):
        return "neg"
    return ""


# ════════════════════════════════════════════════════════════
# 核心：HTML 财务表
# ════════════════════════════════════════════════════════════
def fin_table(
    headers: Sequence[str],
    rows: Sequence[dict],
    caption: str = "",
    sub_headers: Optional[Sequence[str]] = None,
    max_height: Optional[int] = None,
) -> str:
    """
    headers: 列标题（首列左对齐，其余右对齐）
    rows:    [{"c": [...单元格文本...], "t": "normal|grp|sub|tot", "i": 0|1|2}, ...]
    """
    th = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    head = f"<thead><tr>{th}</tr>"
    if sub_headers:
        sh = "".join(f"<th>{html.escape(str(h))}</th>" for h in sub_headers)
        head += f'<tr class="sub">{sh}</tr>'
    head += "</thead>"

    body = []
    for r in rows:
        t = r.get("t", "normal")
        ind = r.get("i", 0)
        tds = []
        for j, c in enumerate(r.get("c", [])):
            if isinstance(c, tuple):
                txt, cls = c
            else:
                txt, cls = c, ""
            if j == 0:
                extra = f" lbl ind{ind}" if ind else " lbl"
                tds.append(f'<td class="{cls}{extra}">{html.escape(str(txt))}</td>')
            else:
                c2 = cls or cell_cls_text(str(txt))
                tds.append(f'<td class="{c2}">{str(txt)}</td>')
        body.append(f'<tr class="{t}">' + "".join(tds) + "</tr>")

    style = f' style="max-height:{max_height}px;overflow-y:auto;"' if max_height else ""
    cap = f'<div class="tbl-cap">{caption}</div>' if caption else ""
    return (
        f'<div class="fintable-wrap"{style}><table class="fintable">'
        f"{head}<tbody>{''.join(body)}</tbody></table></div>{cap}"
    )


def show_table(headers, rows, caption: str = "", sub_headers=None,
               download_df: Optional[pd.DataFrame] = None,
               download_name: str = "table.csv", key: str = None):
    """渲染表格，可选附带 CSV 下载"""
    st.markdown(fin_table(headers, rows, caption, sub_headers), unsafe_allow_html=True)
    if download_df is not None and not download_df.empty:
        st.download_button(
            "⇩ 导出 CSV",
            data=download_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=download_name, mime="text/csv", key=key or f"dl_{abs(hash(caption))%9999}",
        )


# ════════════════════════════════════════════════════════════
# 便捷构造：指标 × 年度 矩阵表
# ════════════════════════════════════════════════════════════
def year_matrix(
    label: str,
    items: Sequence[tuple],
    years: Sequence[int],
    values: dict,
    dec: int = 1,
    suffix: str = "",
) -> dict:
    """
    items: [(行标签, 行类型, 缩进, 数据key)]  行类型: normal/grp/sub/tot
    values: {key: [每年数值]}
    """
    cells = [label]
    for y in years:
        cells.append("")
    return {"c": cells, "t": "grp", "i": 0}


def build_year_table(
    items: Sequence[tuple],
    years: Sequence[int],
    values: dict,
    first_header: str = "项目",
    dec: int = 1,
    suffix: str = "",
    show_yoy: bool = False,
) -> tuple:
    """
    items: [(标签, 行类型, 缩进, key)]
    返回 (headers, rows, DataFrame)
    """
    headers = [first_header] + [f"{y}年" for y in years]
    if show_yoy:
        headers.append("同比")
    rows, raw = [], []
    for label, rtype, indent, key in items:
        vals = values.get(key)
        if rtype == "grp" or vals is None:
            rows.append({"c": [label] + [""] * (len(years) + (1 if show_yoy else 0)),
                         "t": rtype, "i": indent})
            continue
        cells = [label]
        for v in vals:
            cells.append(num(v, dec) + suffix if _is_num(v) else DASH)
        if show_yoy:
            if len(vals) >= 2 and _is_num(vals[-1]) and _is_num(vals[-2]) and vals[-2]:
                cells.append(delta(float(vals[-1]) - float(vals[-2]), dec, suffix))
            else:
                cells.append(DASH)
        rows.append({"c": cells, "t": rtype, "i": indent})
        raw.append({first_header: label, **{f"{y}": (vals[i] if i < len(vals) else None)
                                            for i, y in enumerate(years)}})
    return headers, rows, pd.DataFrame(raw)


# ════════════════════════════════════════════════════════════
# 指标对标表
# ════════════════════════════════════════════════════════════
def benchmark_table(records: Sequence[dict], caption: str = "") -> str:
    """
    records: [{"dim","name","unit","cur","bench","diff","pct","better","status"}]
    """
    headers = ["维度", "指标", "本公司", "行业基准", "差异", "相对基准", "评价"]
    body = []
    last_dim = None
    for r in records:
        d = r.get("dim", "")
        if d != last_dim:
            body.append({"c": [d] + [""] * 6, "t": "grp", "i": 0})
            last_dim = d
        diff = r.get("diff")
        better = r.get("better")
        rel = r.get("pct")
        rel_txt = DASH
        if _is_num(rel):
            rel_txt = f"{float(rel):+.1f}%"
        cls = "" if _is_num(diff) and float(diff) >= 0 else "neg"
        tag = "优于基准" if better is True else ("低于基准" if better is False else "持平")
        body.append({
            "c": [r.get("name", ""), "", num(r.get("cur"), 2) + r.get("unit", ""),
                  num(r.get("bench"), 2) + r.get("unit", ""),
                  (delta(diff, 2, r.get("unit", "")) if _is_num(diff) else DASH),
                  (rel_txt, cls), (tag, "pos" if better else ("neg" if better is False else ""))],
            "t": "normal", "i": 1,
        })
        # 指标名放第二列：修正首列为空
        body[-1]["c"][0] = ""
        body[-1]["c"][1] = r.get("name", "")
    return fin_table(headers, body, caption)


# ════════════════════════════════════════════════════════════
# 通用「标签 + 状态」清单表
# ════════════════════════════════════════════════════════════
def kv_table(headers: Sequence[str], rows: Sequence[Sequence], caption: str = "") -> str:
    body = [{"c": list(r), "t": "normal", "i": 0} for r in rows]
    return fin_table(headers, body, caption)


def badge_html(text: str, status: str = "i") -> str:
    m = {"normal": "bdg-n", "warning": "bdg-w", "danger": "bdg-d",
         "info": "bdg-i", "na": "bdg-0"}
    return f'<span class="bdg {m.get(status, "bdg-i")}">{html.escape(str(text))}</span>'


def status_badge(status: str, text: str = "") -> str:
    """返回状态徽章 HTML"""
    from config import STATUS_LABEL
    return badge_html(text or STATUS_LABEL.get(status, status), status)
