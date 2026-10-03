# Hytech · Data Engineering with Databricks — MT5 Trade Lakehouse Workshop

A self-contained, hands-on **2 × half-day workshop (Mandarin)** for Hytech's Shenzhen data-engineering team.
Participants build a production-style **trade lakehouse** on the same pattern Hytech runs in production:

> MT5 MySQL → AWS DMS (full load + CDC Parquet) → **Auto Loader** → **Lakeflow Spark Declarative Pipelines**
> (bronze → silver with AUTO CDC + expectations → gold marts) → **Lakeflow Jobs** (DQ gate, for-each, Run-if,
> repair) — governed by **Unity Catalog**, observed with **system tables**, assisted by **Genie Code** and
> **AI Functions**.

All data is **synthetic** (seeded, no real clients). Everything is serverless, idempotent and verified end to
end (see *Verified* below).

```
 mt5-sg-01 · mt5-sg-02 · mt5-uk-01 · mt5-cy-01 (+ mt5-hk-01 onboarded live)      app events (JSON)
        │  DMS-style CDC Parquet  (LOAD00000001.parquet + yyyymmdd-hhmmssfff.parquet, Op = I/U/D)
        ▼
 /Volumes/hytech_de_workshop/raw/landing/mt5/<server>/<table>/
        ▼  Spark Declarative Pipeline (per participant schema u_<name>)
 bronze_mt5_{users,deals,positions} · bronze_app_events
 silver_mt5_users (SCD2) · silver_mt5_positions (SCD1) · silver_mt5_deals (append + expectations)
 silver_mt5_deal_corrections (AUTO CDC) · silver_mt5_deals_current · silver_app_events
 gold_daily_symbol_volume · gold_client_daily_pnl · gold_ib_daily_performance · gold_net_exposure_by_symbol · gold_funding_daily
        ▼  Lakeflow Job
 run_pipeline → dq_gate → if/else → AI daily summary (中文) | DQ alert · for-each server reconciliation · Run-if alert/audit
```

## Quick start (instructors / Hytech admin)

1. Put the repo in the workspace (Git folder) or deploy from your laptop:
   ```bash
   databricks bundle deploy -t dev            # or -t prod for the shared deployment
   databricks bundle run hytech_ws_setup      # catalog, synthetic data, ops views, Genie Code skill (~10 min)
   databricks bundle run hytech_daily_trading_reporting_solution   # fills the solutions schema (~4 min)
   ```
   Set `workspace.host` in `databricks.yml` and the variables `catalog`, `llm_endpoint`, `participant_group`.
2. During class, drive the live data with job **`hytech_ws_drip_producer`** (see the facilitator guide).
3. Participants start at **`labs/00_Start_Here`**.

Full checklist for Hytech's admin: [`docs/setup_guide_triones.md`](docs/setup_guide_triones.md).

## Documents

| Doc | For |
|---|---|
| [`docs/workshop_plan.md`](docs/workshop_plan.md) | Goals, storyline, agenda, build plan, risks |
| [`docs/facilitator_guide.md`](docs/facilitator_guide.md) | Run of show, instructor controls, wow moments, verification evidence |
| [`docs/setup_guide_triones.md`](docs/setup_guide_triones.md) | Workspace setup by the Hytech admin |
| [`docs/participant_guide_zh.md`](docs/participant_guide_zh.md) | Participant quick start (Chinese) |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Known errors and fixes |

## Labs

| Module | Lab (`labs/`) | Solution |
|---|---|---|
| M1 | `00_Start_Here` — own schema, explore DMS files, copy labs | — |
| M2 Unity Catalog | `01_Unity_Catalog` — grants, views, tags, column mask, row filter | `solutions/01_Unity_Catalog` |
| M3 Ingestion | `02_Ingestion` — CTAS, COPY INTO, Auto Loader, JSON + rescued data | `solutions/02_Ingestion` |
| M4 Pipelines | `03_pipeline/` (5 TODOs) + `03b_Explore_Pipeline` | `solutions/pipeline/` |
| M5 Jobs | `04_Lakeflow_Jobs.md` (UI) + `04b_Jobs_Catch_Up` | `resources/solution.job.yml` |
| M6 Genie Code | `05_Genie_Code.md` prompt ladder + skill `genie_code/.assistant/skills/hytech-de-conventions` | — |
| M6 System tables | `06_System_Tables` (via governed `ops` views) | `solutions/06_System_Tables` |
| AI Functions | `07_AI_Functions` — `ai_query` (中文), `ai_classify`, `ai_mask`, sentiment | `solutions/07_AI_Functions` |

## Repository layout

| Path | What |
|---|---|
| `databricks.yml`, `resources/` | Declarative Automation Bundle: setup job, drip producer, solution pipeline and job (dev/prod targets) |
| `setup/` | `01`–`06` setup notebooks, `03_drip_producer`, `99_teardown` |
| `src/hytech_workshop/` | Synthetic data generator: MT5 users/deals/positions as DMS CDC, app events, reference data, drip producer |
| `solutions/pipeline/transformations/` | Reference pipeline (Python Auto Loader bronze + SQL silver/gold) |
| `jobs/` | Job task notebooks: `dq_gate`, `reconcile_server`, `publish_daily_summary`, `notify`, `audit` |
| `labs/` | Participant notebooks with TODOs |
| `genie_code/` | Genie Code skill + prompt ladder |
| `tests/` | Local generator tests (`pytest tests/`) |

## Design choices worth knowing

- **Append vs MERGE.** Deals (~99.9% inserts) are an append-only streaming table. The rare corrections and
  deletes go to a small AUTO CDC table, combined in an MV. This mirrors the redesign from Hytech's real-time POC.
- **Data contract + rescued data.** App events use an explicit schema. Drifted fields and type mismatches land
  in `_rescued_data` and are recovered in silver.
- **Governed observability.** Participants query system tables only through `ops.*` views: this workspace only,
  no SQL text, other users' identities masked.
- **LLM numbers.** The AI summary pre-computes every figure in SQL; the model only words it (lesson in lab 07).

## Verified on `fe-vm-zh-serverless-ws` (AWS us-west-2), 3 Oct 2026

- **Setup:** ~785k deals across 4 servers, 141k app events.
- **Solution pipeline:** green. Expectations dropped 1,238 invalid trades; SCD2 history, corrections and rescued
  data all verified.
- **Solution job:**
  - happy path → Chinese AI summary
  - for-each failure → Run-if alert and audit
  - onboard `mt5-hk-01` → repair run
  - bad batch → DQ alert branch
- **Participant flow:** Lab 00 → own pipeline → catch-up job → simulated failure → repair → green.
- **Notebooks:** labs 01, 02, 03b, 06 and 07 executed headless.

Details: [`docs/facilitator_guide.md`](docs/facilitator_guide.md#verified-on-fevm-fe-vm-zh-serverless-ws-3-oct-2026).
