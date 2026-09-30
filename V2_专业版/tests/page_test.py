"""
页面渲染测试：用 Streamlit AppTest 无头运行每个页面，捕获运行时异常
用法： python tests/page_test.py
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from streamlit.testing.v1 import AppTest
from modules import parser

PAGES = [
    ("app.py", "首页驾驶舱"),
    ("pages/0_数据导入.py", "数据导入"),
    ("pages/1_经营诊断.py", "经营诊断"),
    ("pages/2_业财归因.py", "业财归因"),
    ("pages/3_财务风险.py", "财务风险"),
    ("pages/4_预算与战略.py", "预算与战略"),
    ("pages/5_分析报告.py", "分析报告"),
]


def seed(at):
    parsed = parser.parse_folder(os.path.join(ROOT, "data", "立讯精密财务报表"))
    at.session_state.income = parsed["income"]
    at.session_state.balance = parsed["balance"]
    at.session_state.cashflow = parsed["cashflow"]
    at.session_state.years = parsed["years"]
    at.session_state.company_name = parsed["company_name"]
    at.session_state.company_code = parsed["company_code"]
    at.session_state.data_source = "内置示例"
    at.session_state.data_loaded = True
    n = len(parsed["years"])
    rev = float(parsed["income"].iloc[-1]["营业收入"])
    at.session_state.segments = {
        "消费电子": {"收入": [None] * (n - 2) + [rev * 0.80, rev * 0.83],
                     "成本": [None] * (n - 2) + [rev * 0.80 * 0.87, rev * 0.83 * 0.88]},
        "汽车电子": {"收入": [None] * (n - 2) + [rev * 0.09, rev * 0.095],
                     "成本": [None] * (n - 2) + [rev * 0.09 * 0.86, rev * 0.095 * 0.84]},
        "通信互联": {"收入": [None] * (n - 2) + [rev * 0.08, rev * 0.075],
                     "成本": [None] * (n - 2) + [rev * 0.08 * 0.78, rev * 0.075 * 0.775]},
    }
    at.session_state.extra_metrics = {"前五大客户占比": [74.2], "第一大客户占比": [58.5],
                                      "员工人数": [225000], "研发资本化率": [5.0]}


fail = 0
for path, name in PAGES:
    try:
        at = AppTest.from_file(os.path.join(ROOT, path), default_timeout=90)
        seed(at)
        at.run()
        errs = [e for e in at.exception]
        if errs:
            fail += 1
            print(f"❌ {name:12s} 异常 {len(errs)} 处")
            for e in errs[:3]:
                print("   ", type(e).__name__, str(e.value)[:300])
                print("   ", getattr(e, "stack_trace", "")[:600])
        else:
            print(f"✅ {name:12s} 渲染正常 "
                  f"(markdown {len(at.markdown)} / 图表 {len(at.get('vega_lite_chart')) + len(at.get('plotly_chart'))} / 表格 {len(at.dataframe)})")
    except Exception as e:
        fail += 1
        print(f"❌ {name:12s} 运行失败: {type(e).__name__}: {str(e)[:300]}")

print()
print("全部通过 ✅" if fail == 0 else f"存在 {fail} 个页面异常 ❌")
sys.exit(1 if fail else 0)
