# Lab 05 · Genie Code — 让 AI 助手按 Hytech 规范写代码 (an AI pair-engineer that follows Hytech conventions)

**准备 (Before you start)**

- The **`hytech-de-conventions`** skill is installed workspace-wide (`/Workspace/.assistant/skills/`).
  It teaches Genie Code Hytech's naming, MT5 field semantics, the *append vs MERGE* rule, the expectation
  patterns and the governance rules. Open it and skim it (2 min) — this is how a team shares conventions.
- Open the Genie Code panel and switch to **Agent mode**. You can write prompts in Chinese.
- Use `@` to give context (e.g. `@silver_mt5_deals_current`, `@ref_symbols`).

Work through the ladder. Each step has an **expected outcome** — check it before moving on.

---

### L1 · 新的 gold 物化视图 (a new gold MV) — *Lakeflow Pipelines Editor, your `03_pipeline`*

> 在 transformations 里新增一个 gold 物化视图 `gold_country_asset_class_daily`：按 deal_date、country、asset_class
> 统计交易笔数、手数、美元名义金额和客户盈亏，只统计 BUY/SELL 成交，客户属性取当前版本。遵循 hytech-de-conventions。

✅ **Expected:** a new `CREATE OR REFRESH MATERIALIZED VIEW` that
- reads `silver_mt5_deals_current`, joins **current** users (`__END_AT IS NULL`) on `(server_id, login)` and `ref_symbols`
- computes `notional_usd = lots × contract_size × price × rate_profit`
- has a `COMMENT` and `quality = gold`

Run the pipeline and query the new table.

### L2 · 数据质量期望 (expectations)

> 给 `silver_mt5_positions` 增加数据质量期望：lots > 0、price_open > 0，违反时丢弃该行；并解释 AUTO CDC 表上的期望应该放在哪里。

✅ **Expected:** constraints added to the streaming-table definition, plus a note that expectations apply to
the rows *flowing into* the target (the CDC source query).

### L3 · 解释 (explain) — `/explain`

> /explain 为什么 `silver_mt5_users` 用 `TRACK HISTORY ON` 只跟踪部分列？如果跟踪全部列，会有什么后果？

✅ **Expected:** `LastAccess` changes on every login, so tracking all columns would create a new SCD2 version per
login: table bloat, misleading history, higher cost.

### L4 · 诊断失败 (diagnose a failed task) — *Jobs run page, the failed `reconcile_server` iteration*

> 这个任务为什么失败？我应该如何只重跑失败的部分？

✅ **Expected:** it identifies the simulated failure (`fail_server`) and recommends **Repair run** with
`fail_server` cleared, keeping `servers` unchanged (same number of for-each iterations).

### L5 · 成本查询 (cost query) — *SQL editor*

> 用 `hytech_de_workshop.ops.billing_usage` 和 `ops.list_prices` 计算我的管道过去 7 天每天的 DBU 和标价成本（美元），
> 管道名以 trade_lakehouse 开头、由我创建（`ops.pipelines`）。

✅ **Expected:** a join on `sku_name` with the price validity window, `usage_quantity × pricing.default`,
and a filter on `usage_metadata.dlt_pipeline_id`.

### L6 · 挑战 (stretch) — dashboard

> 基于 L5 的查询和 `gold_daily_symbol_volume`，创建一个 AI/BI 仪表盘：第 1 页“交易概览”（名义金额趋势、Top 品种、客户盈亏），
> 第 2 页“管道健康与成本”（每日成本、运行时长、数据质量丢弃行数）。

---

**讨论 (Discuss):** where did Genie Code apply the skill (naming, comments, the append rule)? Where did you have to
correct it? Which other conventions should Hytech's skill contain, e.g. their real catalogs, the GitLab
workflow, the column-tag framework?
