# Workshop Plan — Hytech "Data Engineering with Databricks" (Shenzhen)

*Option 1: MT5 Trade Lakehouse · 13–14 Oct 2026 · 2 × half-day · Mandarin · ~20 participants*
*Instructors: Zhi Han Tan, Germaine Ong · Hytech admin: Triones*

---

## 1. Goals

**Participants leave able to:**
1. Ingest DMS-style CDC files and JSON with CTAS, COPY INTO and Auto Loader, and explain rescued data.
2. Build a Lakeflow Spark Declarative Pipeline: bronze streaming tables, AUTO CDC (SCD1/SCD2), an append-only fact table, expectations and gold materialized views.
3. Choose the right pattern for cost: **append for immutable facts, AUTO CDC only for mutable entities**.
4. Orchestrate the pipeline as a production job: if/else DQ gate, for-each, Run-if, triggers, retries and repair runs.
5. Govern data with Unity Catalog: grants, ownership, tags, column masks and row filters.
6. Measure what they built with system tables (cost per run/day, run timeline, lineage).
7. Use Genie Code (with a Hytech conventions skill) and AI Functions in their daily work.

**Success criteria**
- At least 80% of participants have a green pipeline update and a green job run in their own schema by the end of Day 2.
- Every participant runs a cost query against their own pipeline.
- Hytech keeps three things afterwards: the repo as a reference template, the Genie Code skill, and the job pattern.

## 2. Storyline

> 你是 Hytech 新入职的数据工程师。4 台 MT5 交易服务器的 MySQL 通过 AWS DMS 把变更数据（CDC）以 Parquet 文件写入云存储。
> 你的任务：搭建交易湖仓（Trade Lakehouse），为每日交易报表、客户盈亏、IB 业绩和风险敞口提供可信数据，并像生产系统一样调度、监控与治理它。

*(English: you are a new Hytech data engineer. Four MT5 trading servers replicate MySQL changes to cloud storage as Parquet files via AWS DMS. Build the trade lakehouse behind the daily trading, client P&L, IB performance and exposure reports, and run, monitor and govern it like production.)*

```
 MT5 servers x4 (synthetic)                          App events (Sensors-style JSON)
 mt5-sg-01 · mt5-sg-02 · mt5-uk-01 · mt5-cy-01
        │ DMS-style CDC Parquet: LOAD00000001.parquet + yyyymmdd-hhmmssfff.parquet (Op = I/U/D, cdc_ts)
        ▼
 /Volumes/hytech_de_workshop/raw/landing/mt5/<server>/<table>/      /landing/app_events/<date>/
        │
        │  Lakeflow Spark Declarative Pipeline (serverless, per participant schema u_<name>)
        ▼
 BRONZE  bronze_mt5_users · bronze_mt5_deals · bronze_mt5_positions · bronze_app_events   (Auto Loader)
 SILVER  silver_mt5_users (AUTO CDC SCD2) · silver_mt5_positions (AUTO CDC SCD1)
         silver_mt5_deals (append-only + expectations) · silver_mt5_deal_corrections (AUTO CDC)
         silver_mt5_deals_current · silver_app_events (dedupe)
 GOLD    gold_daily_symbol_volume · gold_client_daily_pnl · gold_ib_daily_performance
         gold_net_exposure_by_symbol · gold_funding_daily
        │
        ▼
 Lakeflow Job: daily_trading_reporting  →  DQ gate · for-each server reconciliation · AI daily commentary (中文) · alerts · audit
 System tables → cost / runs / lineage of *your* pipeline · Genie Code · AI Functions
```

## 3. Environment

| Item | Value (defaults, all configurable) |
|---|---|
| Build/test workspace | `fe-vm-zh-serverless-ws` (AWS us-west-2, serverless) |
| Hytech workspace | TBC with Triones (AWS us-east-1 or ap-southeast-1) |
| Catalog | `hytech_de_workshop` |
| Schemas | `raw` (volumes `landing`, `ref`, `producer`) · `solutions` (instructor solution) · `ops` (governed views over system tables) · `u_<name>` (one per participant, owned by them) |
| Compute | Serverless notebooks, jobs and pipelines; one serverless SQL warehouse (Small, scaling to 3 clusters) |
| LLM endpoint | `databricks-claude-sonnet-4-5` (configurable) for `ai_query` |
| Participant group | `de_workshop_sz` |

**Dataset** (synthetic, seeded, about 90 days of history, under 1 GB):

| Table / files | Grain | Size | Built-in "lessons" |
|---|---|---|---|
| `mt5_users` | client account per server | about 6k | SCD2 changes (leverage, group, IB, status, KYC), rare deletes |
| `mt5_deals` | MT5 deal (trade in/out, deposit/withdrawal balance deals) | about 1M | About 99.9% inserts, about 0.1% corrections; about 0.2% invalid rows for expectations; Chinese/English funding comments |
| `mt5_positions` | open position | about 3k open | Update-heavy CDC, deletes on close |
| `app_events` | Sensors-style JSON event | about 200k | Nested JSON; a new field mid-week; type mismatches → `_rescued_data`; about 1% duplicates; zh/en feedback text |
| `ref/symbols.csv` | symbol | 40 | Asset class and contract size (COPY INTO) |
| `ref/ib_hierarchy.csv` | IB | about 60 | IB tree and rebate plan |
| `ref/fx_rates_daily.csv` | day × ccy | about 900 | Quote-currency → USD (CTAS) |
| Drip producer job | — | live | New CDC files every 30 s; can onboard a new server (`mt5-hk-01`) and inject a bad batch |

## 4. Run of show

One instructor presents while the other circulates; swap per module. With 20 newcomers, the floater is essential. Proposed lead per module is marked; confirm with Germaine.

### Day 1 — Tue 13 Oct (09:30–13:00)

| Time | Module | Concept (10–15 min) | Demo | Hands-on lab | Output |
|---|---|---|---|---|---|
| 09:30 | **M1 Platform overview** (30) | Lakehouse, Unity Catalog, serverless, Lakeflow (Connect, Pipelines, Jobs), Genie. Hytech's real architecture next to the lab | Workspace tour | `labs/00_Start_Here`: create/verify own schema, browse the landing volume | Schema `u_<name>` ready |
| 10:00 | **M2 Unity Catalog** (30) | 3-level namespace, ownership, privileges, volumes, tags, masks, row filters, lineage | ABAC with governed tags (instructor), access requests | `labs/01_Unity_Catalog`: grants, tags, column mask on email/phone, row filter by brand | Masked `users_snapshot` table |
| 10:30 | **M3 Ingestion** (45) | Batch vs incremental vs streaming; CTAS / COPY INTO / Auto Loader; metadata columns; rescued data; enterprise connectors | Lakeflow Connect NetSuite (GA), MySQL CDC (preview) | `labs/02_Ingestion`: CTAS FX rates, COPY INTO symbols (×2 for idempotency), Auto Loader DMS Parquet, JSON with rescued data | 4 bronze tables |
| 11:15 | **M4 Spark Declarative Pipelines** (60) | Streaming tables vs MVs, AUTO CDC SCD1/2, expectations, event log; **append vs MERGE cost lesson** | Lakeflow Pipelines Editor; Lakeflow Designer (IB weekly report) | `labs/03_pipeline`: fill the TODOs in silver/gold, create and run the pipeline; then `labs/03b_Explore_Pipeline` | Green pipeline update; gold marts |
| 12:15 | **Q&A Day 1** (30) | — | Drip producer running: watch new CDC land on the next update | Catch-up: copy solution files | Everyone has a pipeline |

### Day 2 — Wed 14 Oct (09:30–13:00)

| Time | Module | Concept | Demo | Hands-on lab | Output |
|---|---|---|---|---|---|
| 09:30 | **M5 Lakeflow Jobs** (60) | Tasks, DAGs, parameters, task values, if/else, for-each, Run-if, triggers, retries, repair, notifications; CI/CD with Declarative Automation Bundles | `databricks bundle deploy -t cicd` as a service principal (`docs/cicd_demo.md`) | `labs/04_Lakeflow_Jobs`: build `daily_trading_reporting` in the UI. Run → the for-each fails on new server `mt5-hk-01` → instructor onboards it → **repair run** | Green job run plus a repaired run |
| 10:30 | **M6a Genie Code** (30) | Agent mode, `@` context, skills, `/fix` | Install the `hytech-de-conventions` skill | `labs/05_Genie_Code` prompt ladder: new gold MV from a Chinese prompt, add expectations, fix a failed task | New MV in own pipeline |
| 11:00 | **M6b System tables** (30) | billing.usage × list_prices, lakeflow timelines, lineage, query history; governed views | Cost & health dashboard (published by setup) | `labs/06_System_Tables`: your pipeline's $/day, task durations, lineage graph | Cost and health queries |
| 11:30 | **M6c Recap + knowledge check + cert prep** (30) | Data Engineer Associate topic map | — | `labs/08_Knowledge_Check` (15 questions + bonus) | — |
| 12:00 | **AI Functions** (30) | Batch LLM in SQL; governance; cost | — | `labs/07_AI_Functions`: `ai_query` Chinese daily summary, `ai_classify` funding methods (regex vs AI), `ai_mask` on feedback text | Commentary table |
| 12:30 | **Q&A Day 2** (30) | Roadmap: Genie ZeroOps (private preview), Lakehouse//RT (beta) | — | Feedback form | — |

### Key "wow" moments

- **M3/M4:** the drip producer writes a MySQL change and it appears in silver on the next pipeline update, with SCD2 history visible.
- **M4:** `DESCRIBE HISTORY` on the append-only deals table next to the MERGE-based corrections table, plus the POC cost numbers: cost scales with *data changed, not data stored*.
- **M5:** onboard a new MT5 server live. The job fails, then the repair run goes green with no pipeline change, because the bronze glob is metadata-driven.
- **M6:** Genie Code writes a mart from a Chinese prompt, and the Day-1 pipeline cost shows up to the cent.

## 5. Lab design rules

- Every lab has **TODO blocks with hints** in `labs/` and a complete version in `solutions/`.
- Every module has a **catch-up path**: copy the solution file, or run the helper cell, so nobody blocks the next module.
- Markdown is in Chinese first with English in brackets; code, identifiers and column names are in English.
- Labs are timed for newcomers: concept ≤ 15 min, lab 20–30 min.
- No third-party Python packages, because Hytech's serverless egress may be restricted. Synthetic data uses only numpy/pandas/pyarrow.
- Everything is idempotent and safe to re-run. Per-participant isolation comes from each person's own schema and pipeline.

## 6. Build plan (repo `zhihantan/hytech-de-workshop`)

| # | Component | Path | Status |
|---|---|---|---|
| 1 | Plan (this doc), README | `docs/`, `README.md` | ✅ |
| 2 | Config + synthetic generators (MT5 CDC, app events, refs) | `src/hytech_workshop/` | ✅ |
| 3 | Setup notebooks (catalog, data, participants, ops views, skill install) + teardown | `setup/` | ✅ |
| 4 | Drip producer job | `setup/03_drip_producer.py` | ✅ |
| 5 | Solution pipeline (SQL + Python) | `solutions/pipeline/` | ✅ |
| 6 | Job task notebooks (DQ gate, reconcile, AI summary, notify, audit) | `jobs/` | ✅ |
| 7 | Declarative Automation Bundle (setup, producer, solution pipeline and job; dev/prod) | `databricks.yml`, `resources/` | ✅ |
| 8 | Participant labs 00–07 + solutions | `labs/`, `solutions/` | ✅ |
| 9 | Genie Code skill + prompt ladder | `genie_code/` | ✅ |
| 10 | Facilitator guide, participant guide (zh), Triones setup guide, troubleshooting | `docs/` | ✅ |
| 11 | End-to-end test on `fe-vm-zh-serverless-ws` (setup → pipeline → job → repair → system tables → AI) | evidence in `docs/` | ✅ |
| 12 | Knowledge check (15 questions + bonus) and answer key mapped to the exam guide | `labs/08_Knowledge_Check.md`, `docs/knowledge_check_answers.md` | ✅ |
| 13 | Cost & health dashboard (AI/BI), published by the setup job | `dashboards/`, `setup/07_cost_dashboard.py` | ✅ |
| 14 | CI/CD demo: `cicd` target (service principal), GitLab CI template, demo script | `databricks.yml`, `cicd/`, `docs/cicd_demo.md` | ✅ |

**Test plan on FEVM**
1. Deploy the bundle (dev) and run the setup job; check file counts and row counts.
2. Run the solution pipeline. Check expectations, SCD2 history and gold row counts.
3. Run the solution job. Check the DQ gate true path, the for-each across 4 servers, Run-if and audit.
4. Start the producer with `new_server=mt5-hk-01` and a bad batch. Check the false path, the failure → repair, and incremental pickup.
5. Run the system-tables and AI-functions labs against the solution.
6. Do a participant dry run with a fresh `u_` schema and the lab files (UI flow).

## 7. Timeline to delivery

| Date | Milestone |
|---|---|
| Sat 3 – Sun 4 Oct | Repo, data generator, setup, solution pipeline, job (core path green on FEVM) |
| Mon 5 Oct | Germaine confirms with Triones: domain, workspace/region, system-table access, participant list |
| Tue 6 – Wed 7 Oct | Participant labs, Genie Code skill, guides (zh); Germaine drafts slides |
| Thu 8 – Fri 9 Oct | Joint review and module split; hand Triones the setup guide; Triones runs setup and tests access from the Shenzhen office |
| Mon 12 Oct | Travel; evening dry run in Hytech's workspace |
| Tue 13 – Wed 14 Oct | Workshop |

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Hytech workspace IP-ACL blocks the Shenzhen office | Triones tests from the venue Wi-Fi by 9 Oct; ask for a fallback hotspot/VPN |
| Google Docs/Slides blocked in mainland China | Slides as PDF/PPTX on the loaner laptop; lab text lives in notebooks |
| FMAPI model not served in Hytech's region | `llm_endpoint` is a parameter; check cross-geo routing; fallback to any available chat model |
| Participants can't read system tables | Governed views in `ops` (definer's rights), filtered to the training workspace |
| Newcomers fall behind in M3–M4 | Catch-up cells and solution files; the floater instructor |
| 20 pipelines with file-arrival triggers | Participants run manually or on schedule; the instructor demos the trigger |
| Account-level groups / governed tags need account admin | Setup degrades gracefully: grants are skipped with a warning; ABAC is instructor-demo only |
| Billing data lags by hours | Run the cost lab on Day 2 against Day-1 runs |

## 9. Open questions (for Triones, Mon 5 Oct)

1. Which workspace and region? Are serverless, FMAPI (which models), Genie Code and Genie enabled? Is the Shenzhen office on the IP allow list?
2. Is it OK to mirror MT5/DMS table shapes with synthetic data? Any names to avoid?
3. Participant list and usernames. Will there be an account-level group (`de_workshop_sz`)?
4. Can the `ops` schema expose system tables via filtered views? Who approves (Ray/Robin)?
5. Do they want the CI/CD demo aligned to their GitLab setup (invite Robin to M5)? A GitLab template is ready: `cicd/gitlab-ci.yml`.
6. What came back from Triones' poll of team questions?
