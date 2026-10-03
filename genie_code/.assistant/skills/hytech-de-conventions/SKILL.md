---
name: hytech-de-conventions
description: >-
  Use when writing, reviewing or debugging data-engineering code for the Hytech MT5 trade lakehouse
  (catalog hytech_de_workshop or Hytech's production catalogs): Lakeflow Spark Declarative Pipelines
  (bronze/silver/gold streaming tables and materialized views), AUTO CDC, expectations, Auto Loader,
  Lakeflow Jobs, Unity Catalog grants/tags/masks, and system-table cost queries. Encodes Hytech naming,
  MT5 data semantics (deals, positions, users, DMS CDC), cost-aware patterns and governance rules.
  Triggers: pipeline, streaming table, materialized view, AUTO CDC, expectation, Auto Loader, job, MT5,
  deals, positions, users, DMS, CDC, 管道, 流表, 物化视图, 数据质量, 作业.
---

# Hytech data-engineering conventions — MT5 trade lakehouse

Follow these rules whenever you generate or change code for the Hytech trade lakehouse. If the user's
request conflicts with a rule, say so and propose the compliant alternative.

## 1. Where things live

- Landing zone (read-only): `/Volumes/hytech_de_workshop/raw/landing/`
  - `mt5/<server_id>/<table>/` — AWS DMS Parquet: `LOAD0000000N.parquet` (full load) and
    `yyyymmdd-hhmmssfff.parquet` (CDC). Every row has `Op` (`I`/`U`/`D`) and `cdc_ts` (commit time).
    Tables: `mt5_users`, `mt5_deals`, `mt5_positions`. Servers: `mt5-sg-01`, `mt5-sg-02`, `mt5-uk-01`,
    `mt5-cy-01` (+ new ones over time — never hard-code the list in ingestion).
  - `app_events/<yyyy-mm-dd>/events-*.json` — Sensors-style JSON lines (nested `properties`).
- Reference CSVs: `/Volumes/hytech_de_workshop/raw/ref/{symbols,ib_hierarchy,servers,fx_rates}/`.
- Each engineer builds in their **own schema** `u_<name>`. Never write to `raw`, `solutions` or `ops`.
- Pipeline configuration keys: `landing_root`, `ref_root` — use `${landing_root}` (SQL) or
  `spark.conf.get("landing_root")` (Python) instead of literal paths.

## 2. Naming and layering

| Layer | Name pattern | Contents |
|---|---|---|
| Bronze | `bronze_<source>_<entity>` e.g. `bronze_mt5_deals` | Source columns as-is (MT5 PascalCase) + `server_id` (from path), `source_file`, `ingested_at` |
| Silver | `silver_<source>_<entity>` | snake_case, typed, keys enforced, expectations |
| Gold | `gold_<subject>_<grain>` e.g. `gold_daily_symbol_volume` | Business marts for BI / Genie |
| Reference | `ref_<name>` | Materialized views over the reference CSVs |
| Ops | `ops_<name>` | Job outputs: DQ results, reconciliation, alerts, audit |

- Units in column names: `_usd`, `lots`, `_at` (timestamp), `_date`, `_pct`.
- Every table / MV has a `COMMENT` and `TBLPROPERTIES ('quality' = 'bronze' | 'silver' | 'gold')`.

## 3. MT5 semantics (get these exactly right)

- `Volume` is in 1/10000 lot → `lots = Volume / 10000.0`.
- `Action`: 0 = BUY, 1 = SELL, 2 = BALANCE (deposit if `Profit > 0`, withdrawal if `Profit < 0`).
- `Entry`: 0 = IN (opens a position), 1 = OUT (closes it). Realised P&L (`Profit`, USD) is on OUT deals only.
- Costs: `Commission` (charged per side), `Storage` = swap. `Profit`, `Commission`, `Storage` are in USD.
- USD notional = `lots * ContractSize * Price * RateProfit` (`RateProfit` converts quote currency → USD).
- Users: `Group` = `real\<Brand>\<TYPE>-USD` → `brand = split_part(Group, '\\', 2)`,
  `account_type = split_part(split_part(Group, '\\', 3), '-', 1)`. `Agent` = IB login, 0 = no IB.
- Logins, deal ids and position ids are unique **per server** only: keys are always
  `(server_id, login)`, `(server_id, deal_id)`, `(server_id, position_id)`.
- Retail clients usually lose: a positive total `client_pnl_usd` is unusual and worth flagging.

## 4. Cost-aware patterns (lesson from Hytech's real-time POC)

- **Immutable facts (deals, ~99.9% inserts) → append-only** streaming table from bronze `WHERE Op = 'I'`.
  Route the rare `U`/`D` rows to a small AUTO CDC table (`silver_mt5_deal_corrections`) and combine
  them in a materialized view (`silver_mt5_deals_current`). **Do not** AUTO CDC / MERGE the entire deals
  table: a MERGE rescans the target, so cost grows with data *stored*, not data *changed*.
- **Mutable entities → AUTO CDC**: users as SCD Type 2 with `TRACK HISTORY ON` business columns only
  (group, account_type, leverage, ib_login, status — not `LastAccess`); positions as SCD Type 1 with
  `APPLY AS DELETE WHEN _op = 'D'`. Always `SEQUENCE BY cdc_ts`.
- Triggered pipelines by default; continuous mode only if an SLA requires it. Serverless compute.
  No all-purpose clusters for scheduled work.

## 5. Data quality

- Expectations on silver:
  - `ON VIOLATION DROP ROW` for invalid trades: `login IS NOT NULL`, and unless `deal_type = 'BALANCE'`:
    `volume_raw > 0`, `symbol IS NOT NULL`, `price > 0`.
  - Warn only (no `ON VIOLATION`) for soft rules, e.g. `deal_time <= current_timestamp() + INTERVAL 1 HOUR`.
  - `ON VIOLATION FAIL UPDATE` only for contract breaks that must stop the pipeline.
- DQ metrics come from the pipeline event log: `details:flow_progress.data_quality.dropped_records` and
  `details:flow_progress.data_quality.expectations`.
- App events: keep a contract schema in bronze with `rescuedDataColumn => '_rescued_data'`;
  de-duplicate on `event_id` in silver.

## 6. Governance (Unity Catalog)

- PII columns (`email`, `phone`, `first_name`, `last_name`) get the tag `pii_category` (value = the PII
  type) and a column mask. In production use the **governed tag** keys and values defined by Hytech's data
  governance team — governed tags reject values outside their allowed list (`UC_TAG_POLICY_VALUE_NOT_ALLOWED`).
  Mask and row-filter functions use `is_account_group_member('<group>')`.
- Grant to **groups**, never to individual users. Least privilege: `USE CATALOG`, `USE SCHEMA`, `SELECT`.
- No secrets or tokens in code. Webhook URLs come from job parameters or a secret scope.

## 7. Lakeflow Jobs pattern

`run_pipeline` (pipeline task, 1 retry) → `dq_gate` (sets task values) → `if/else` on
`{{tasks.dq_gate.values.dq_drop_pct}}` → `publish_daily_summary` | `notify_dq_owner`;
`for each` server → `reconcile_server`; `alert_on_failure` with *Run if: At least one failed*;
`write_audit_row` with *Run if: All done*. Production deployments use Declarative Automation Bundles
through CI/CD, run as a service principal — no manual edits in prod.

## 8. Answer style

- Reply in the user's language (中文提问就用中文回答); keep SQL/Python identifiers in English.
- Show the code first, then explain in 1–3 short lines. Point out which rule above you applied.
