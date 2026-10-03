# Lab 03 · 交易湖仓管道 (Trade lakehouse pipeline) — Lakeflow Spark Declarative Pipelines

**目标 (Goal):** build bronze → silver → gold for the MT5 data in **your own schema** `u_<name>`.

## 1 · 创建管道 (Create the pipeline) — Lakeflow Pipelines Editor

1. Copy this folder to your home first (`labs/00_Start_Here` → step 4 does it for you):
   `/Users/<you>/hytech_de_lab/03_pipeline/`
2. **New → ETL pipeline** (Lakeflow Pipelines Editor). Choose **Add existing assets** and set:
   | Setting | Value |
   |---|---|
   | Pipeline name | `trade_lakehouse_<your_name>` |
   | Root folder | `/Users/<you>/hytech_de_lab/03_pipeline` |
   | Source code | `/Users/<you>/hytech_de_lab/03_pipeline/transformations` |
   | Default catalog / schema | `hytech_de_workshop` / `u_<your_name>` |
3. **Settings → Configuration** — add two key/value pairs:
   | Key | Value |
   |---|---|
   | `landing_root` | `/Volumes/hytech_de_workshop/raw/landing` |
   | `ref_root` | `/Volumes/hytech_de_workshop/raw/ref` |
4. **Settings → Advanced → Publish event log to metastore**: on, table name `pipeline_event_log`
   (catalog `hytech_de_workshop`, schema `u_<your_name>`). The job in lab 04 reads it.
5. Compute: **Serverless**. Pipeline mode: **Triggered**.

## 2 · 完成 TODO (Fill in the TODOs)

| TODO | File | What |
|---|---|---|
| 1a, 1b | `01_bronze_mt5.py` | Auto Loader format; extract `server_id` from the file path |
| 2 | `03_silver_mt5.sql` | AUTO CDC keys / delete / sequence / SCD2 / tracked columns for users |
| 3a, 3b | `03_silver_mt5.sql` | Two expectations for invalid trades |
| 4 | `03_silver_mt5.sql` | Append-only filter for deals |
| 5 | `05_gold_reporting.sql` | USD notional and client P&L |

Use **Dry run** to validate, then **Run pipeline**. Stuck? The answers are in
`solutions/pipeline/transformations/` — copy the file over yours (catch-up).

## 3 · 观察 (Observe)

- Graph: which tables are streaming tables, which are materialized views? Why?
- Expectations tab of `silver_mt5_deals`: how many rows were dropped, and by which rule?
- Run the pipeline again after the instructor's drip producer has written new files: only the new
  files are processed (incremental). Then open `labs/03b_Explore_Pipeline`.
