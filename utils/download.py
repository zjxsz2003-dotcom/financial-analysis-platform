"""
下载工具函数
"""
import io
import pandas as pd
from fpdf import FPDF
import streamlit as st


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """DataFrame 转 CSV bytes"""
    return df.to_csv(index=False).encode("utf-8-sig")


def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    """DataFrame 转 Excel bytes"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    return output.getvalue()


def fig_to_png_bytes(fig) -> bytes:
    """Plotly Figure 转 PNG bytes"""
    return fig.to_image(format="png", scale=2)


def generate_pdf_report(report_content: dict) -> bytes:
    """
    生成PDF报告
    report_content = {
        "title": "季度经营分析报告",
        "period": "2024年Q3",
        "company": "立讯精密",
        "sections": [
            {"heading": "一、核心指标概览", "body": "文本内容...", "table": pd.DataFrame(...)},
            ...
        ],
        "ai_summary": "AI生成的摘要文本...",
    }
    """
    pdf = FPDF()
    pdf.add_page()

    # 注册中文字体（使用内置支持，或使用系统字体）
    # fpdf2 默认不支持中文，需要在系统中找到中文字体
    import os
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
        "C:/Windows/Fonts/simsun.ttc",    # 宋体
        "C:/Windows/Fonts/simhei.ttf",    # 黑体
    ]
    font_found = False
    for fp in font_paths:
        if os.path.exists(fp):
            pdf.add_font("CJK", "", fp, uni=True)
            pdf.add_font("CJK", "B", fp, uni=True)  # 用同一字体模拟粗体
            font_found = True
            break

    if not font_found:
        # 回退: 尝试常用路径
        import glob
        win_fonts = glob.glob("C:/Windows/Fonts/*.ttf") + glob.glob("C:/Windows/Fonts/*.ttc")
        for fp in win_fonts[:5]:
            try:
                pdf.add_font("CJK", "", fp, uni=True)
                font_found = True
                break
            except:
                continue

    if font_found:
        pdf.set_font("CJK", "", 10)
    else:
        # 最终回退：使用内置字体（不支持中文，但至少不出错）
        pdf.set_font("Helvetica", "", 10)

    # === 封面 ===
    pdf.set_font("CJK", "B", 20) if font_found else pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 15, report_content.get("title", "财务分析报告"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.set_font("CJK", "", 12) if font_found else pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"公司：{report_content.get('company', '')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"期间：{report_content.get('period', '')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # === AI 摘要 ===
    ai_summary = report_content.get("ai_summary", "")
    if ai_summary:
        pdf.set_font("CJK", "B", 13) if font_found else pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "报告摘要", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("CJK", "", 10) if font_found else pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 7, ai_summary)
        pdf.ln(5)

    # === 各章节 ===
    for section in report_content.get("sections", []):
        heading = section.get("heading", "")
        body = section.get("body", "")
        table = section.get("table")

        if heading:
            pdf.set_font("CJK", "B", 12) if font_found else pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, heading, new_x="LMARGIN", new_y="NEXT")

        if body:
            pdf.set_font("CJK", "", 10) if font_found else pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 7, body)

        if table is not None and isinstance(table, pd.DataFrame) and not table.empty:
            pdf.ln(3)
            pdf.set_font("CJK", "", 8) if font_found else pdf.set_font("Helvetica", "", 8)
            col_width = 190 / len(table.columns)
            # 表头
            for col in table.columns:
                pdf.cell(col_width, 8, str(col), border=1, align="C")
            pdf.ln()
            # 数据行
            for _, row in table.iterrows():
                for val in row:
                    pdf.cell(col_width, 7, str(val)[:20], border=1, align="C")
                pdf.ln()

        pdf.ln(3)

    # === 页脚 ===
    pdf.set_y(-20)
    pdf.set_font("CJK", "", 8) if font_found else pdf.set_font("Helvetica", "", 8)
    disclaimer = "本报告由AI辅助生成，数据来源于公开披露信息，仅供学习演示使用"
    pdf.cell(0, 10, disclaimer, align="C")

    return pdf.output()
