"""
冒烟测试：不启动 Streamlit，直接跑全部计算引擎，验证数值与鲁棒性
用法： python tests/smoke.py
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import parser, data_loader as dl, finance_core as fc
from modules import business_deep as bd, budget_analysis as ba
from modules import risk_analysis as ra, industry_bench as ib, strategy as stg
from modules import report_engine as re_, quality
from modules.kpi import snapshot, alerts, dim_stats

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "data", "立讯精密财务报表")


def run(with_segments: bool = True, verbose: bool = True):
    print("=" * 70)
    print("解析：", BASE)
    parsed = parser.parse_folder(BASE)
    print("  公司:", parsed["company_name"], parsed["company_code"], "年份:", parsed["years"])
    dl.load(parsed, "内置示例")

    diag = quality.diagnose(parsed["income"], parsed["balance"], parsed["cashflow"], parsed["years"])
    print("  质量评级:", diag["grade"], "| errors:", len(diag["errors"]),
          "| warnings:", len(diag["warnings"]))

    if with_segments:
        inc = parsed["income"]
        n = len(parsed["years"])
        i = n - 1
        rev = float(inc.iloc[i]["营业收入"])
        seg = {
            "消费电子": {"收入": [None] * (n - 2) + [rev * 0.80, rev * 0.83],
                         "成本": [None] * (n - 2) + [rev * 0.80 * 0.845, rev * 0.83 * 0.84]},
            "汽车电子": {"收入": [None] * (n - 2) + [rev * 0.09, rev * 0.095],
                         "成本": [None] * (n - 2) + [rev * 0.09 * 0.86, rev * 0.095 * 0.84]},
            "通信互联": {"收入": [None] * (n - 2) + [rev * 0.08, rev * 0.075],
                         "成本": [None] * (n - 2) + [rev * 0.08 * 0.78, rev * 0.075 * 0.775]},
        }
        dl_st = dl
        import streamlit as st
        st.session_state["segments"] = seg
        dl_st.set_extra({"前五大客户占比": [74.2], "第一大客户占比": [58.5],
                         "员工人数": [225000], "研发资本化率": [5.0]})

    model = fc.build_model(force=True)
    print("  模型年份:", model["years"])
    print("  营业收入:", [None if v is None else round(v, 1) for v in model["revenue"]])
    print("  净利润  :", [None if v is None else round(v, 1) for v in model["net_profit"]])
    print("  ROE     :", [None if v is None else round(v, 2) for v in model["roe"]])
    print("  毛利率  :", [None if v is None else round(v, 2) for v in model["gross_margin"]])
    print("  DSO/DIO/CCC:", round(fc._last(model["dso"]) or 0, 1),
          round(fc._last(model["dio"]) or 0, 1), round(fc._last(model["ccc"]) or 0, 1))
    print("  DA      :", model.get("da"))

    snap = snapshot(model)
    al = alerts(snap)
    print("  预警:", [(a["name"], a["status"], round(a["value"] or 0, 2)) for a in al])

    dp = fc.dupont_decompose(model, 0, model["n"] - 1)
    print("  杜邦分解:", [(n, round(c, 2)) for n, c, _, _, _ in dp])

    mb = fc.margin_bridge(model)
    print("  毛利率桥:", None if not mb else
          {k: (round(v, 3) if isinstance(v, float) else v) for k, v in mb.items() if k != "detail"})

    ol = fc.operating_leverage(model)
    print("  经营杠杆:", {k: (round(v, 2) if isinstance(v, float) else v)
                          for k, v in ol.items() if k not in ("x", "y", "fit")})

    eq = fc.earnings_quality_score(model)
    print("  盈利质量分:", None if eq["score"] is None else round(eq["score"], 1))

    bv = ba.budget_vs_actual(model)
    pb = ba.profit_bridge(model, bv)
    print("  预算收入合计:", bv["收入"].get("合计"))
    print("  利润桥:", None if not pb else
          {k: (round(v, 2) if isinstance(v, float) else v)
           for k, v in pb.items() if k != "steps"})
    gv = ba.gross_profit_variance(model, bv)
    print("  毛利偏差分解行数:", None if gv is None else len(gv))
    rf = ba.rolling_forecast(model, bv, months=6)
    print("  滚动预测收入:", None if rf["fc_revenue"] is None else round(rf["fc_revenue"], 1),
          "提速需求%:", None if rf["speedup"] is None else round(rf["speedup"], 1))

    rs = ra.risk_scorecard(model)
    print("  风险总分:", None if rs["total"] is None else round(rs["total"], 1),
          ra.risk_level(rs["total"])[0])
    print("  各维度:", {k: (None if v["score"] is None else round(v["score"], 1))
                        for k, v in rs["dims"].items()})
    az = ra.altman_detail(model)
    print("  Altman Z:", None if not az else round(az["z"], 2),
          None if not az else az["zone"][0])
    sc = ra.scenario_compare(model)
    print("  情景数:", len(sc))
    if not sc.empty:
        print(sc[["情景", "较基准变动(亿元)", "压力后ROE(%)"]].to_string(index=False))

    lp = ra.liquidity_profile(model)
    print("  现金/短债:", None if lp["cover_short"] is None else round(lp["cover_short"], 2))

    print("  传导链行数:", len(ra.transmission_rows(snap)))

    recs = ib.benchmark_records(snap)
    print("  对标指标数:", len(recs), "| 行业:", ib.industry_summary(snap)["industry"])

    tg = stg.progress(dl.get_strategy(model), 50.0)
    print("  战略目标:", [(t["name"][:16], None if t["progress"] is None else round(t["progress"], 1))
                          for t in tg])
    wi = stg.what_if(model, d_rev=-10, d_gm=-1.5)
    print("  What-if 净利润:", round(wi["模拟"]["净利润"], 2), "基准:", round(wi["基准"]["净利润"], 2))

    rep = re_.build_report(model, "annual")
    md = re_.to_markdown(rep)
    print("  报告章节:", [s["h"] for s in rep["sections"]])
    print("  Markdown 字数:", len(md))
    print("  HTML 长度:", len(re_.to_html(rep)))

    for fn in (bd.segment_overview, bd.cost_structure, bd.expense_efficiency,
               bd.rd_analysis, bd.ar_quality, bd.inventory_quality,
               bd.working_capital, bd.concentration):
        try:
            r = fn(model) if fn is not bd.concentration else fn()
            print(f"  {fn.__name__}: {'OK' if r else 'SKIP(None)'}")
        except Exception as e:
            print(f"  {fn.__name__}: ERROR {type(e).__name__}: {e}")

    print("✅ 冒烟测试通过")
    return model


if __name__ == "__main__":
    run(True)
    print()
    print("#" * 70)
    print("# 无分部数据 / 无补充指标的降级路径")
    print("#" * 70)
    import streamlit as st
    st.session_state.clear()
    run(False)
