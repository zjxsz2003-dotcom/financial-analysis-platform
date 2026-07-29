# 项目备忘录

## 当前状态（2026-07-26 22:00）
✅ **v3.0 稳定运行** — http://localhost:8501
✅ **全部Bug已修复** — 0错误
✅ **财务报表按会企标准格式展示** — 资产负债表(账户式)、利润表(多步式)、现金流量表(三大活动)
✅ **外部技能库** — reference_skills/ (anthropics-skills, superpowers, web-access)

## 最近修复（本轮对话）
1. `bi_drill_bar` 等6个函数缺失 → ui_helpers.py补全
2. `_budget_settings`/`_settings_ui`/`_render_balance_sheet`函数定义顺序 → 移到调用前
3. `compact_chart` 导入错误 → 各页面本地定义
4. `bi_drill_bar([` 语法错误(未闭合) → 补上 `])`
5. 财务报表CSMAR格式 → 会企01-03表标准格式(深蓝标题+账户式+多步式)

## 核心文件
- `pages/0_📥_数据导入.py` — 数据导入(含标准财务报表渲染)
- `pages/1~6` — 6个分析模块
- `modules/` — 计算引擎
- `utils/ui_helpers.py` — UI组件库
- `reference_skills/` — 外部设计参考
