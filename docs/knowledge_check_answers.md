# Knowledge check — answer key (instructors only)

For `labs/08_Knowledge_Check.md` (M6c, Day 2 11:30). About 15 minutes to answer and 10 to go through the
answers. Take the bonus question after Lab 07. To run it as a live poll, paste the questions into a Lark (Feishu)
form, which works in mainland China; otherwise use a show of hands per option.

**Answers:** 1 C · 2 D · 3 A · 4 C · 5 B · 6 D · 7 A · 8 B · 9 C · 10 D · 11 A · 12 C · 13 B · 14 A · 15 B · Bonus D

| # | Answer | Why (and where we saw it) | Exam section |
|---|---|---|---|
| 1 | C | Volumes use the same three-level namespace as tables: `catalog.schema.volume`. The metastore sits above catalogs and is never in the path. (Lab 00) | Platform |
| 2 | D | `SELECT` alone is not enough: the group also needs `USE CATALOG` on the catalog and `USE SCHEMA` on the schema. `ALL PRIVILEGES` is far more than needed. (Lab 01) | Governance and Security |
| 3 | A | A column mask hides `email` per caller; a row filter limits rows by brand. A tag only classifies a column: it enforces nothing unless an ABAC policy uses it. Copies per brand drift. (Lab 01) | Governance and Security |
| 4 | C | Lineage is captured automatically, at table and column level, for workloads on Unity Catalog compute. Shown in Catalog Explorer and `system.access.table_lineage`. (Lab 01 demo, Lab 06) | Governance and Security |
| 5 | B | The second `COPY INTO` in Lab 02 loaded 0 rows because it skips files it already loaded. Auto Loader keeps discovered files in its checkpoint, so it scales to millions of files. (Lab 02) | Data Ingestion and Loading |
| 6 | D | With a data contract (explicit schema), values that don't fit go to `_rescued_data` instead of being lost; silver recovers them with `get_json_object`. (Lab 02, `silver_app_events`) | Data Ingestion and Loading |
| 7 | A | Streaming tables process each new input once, which suits append-only sources. Aggregates and joins whose inputs can change belong in materialized views. (Lab 03) | Data Transformation and Modeling |
| 8 | B | `KEYS` identifies the row; `SEQUENCE BY` orders the changes for each key, so a late or out-of-order event cannot overwrite a newer one. SCD2 also uses it for `__START_AT` / `__END_AT`. (Lab 03) | Data Transformation and Modeling |
| 9 | C | Three modes: no `ON VIOLATION` keeps the row and records it (our `deal_time_not_in_future`), `DROP ROW` drops it, `FAIL UPDATE` stops the update. A quarantine table is something you build yourself. `dq_gate` read these counts from the event log. (Labs 03, 04) | Data Transformation and Modeling |
| 10 | D | MERGE cost grows with the size of the target; an append grows only with new data. `A` is false: `APPLY AS DELETE WHEN` applies deletes. Show `DESCRIBE HISTORY` on both tables. (Lab 03b) | Troubleshooting, Monitoring, and Optimization |
| 11 | A | `At least one failed` for the alert, `All done` for the audit row. That is why the solution run shows *Succeeded with failures* after a failure. (Lab 04) | Working with Lakeflow Jobs |
| 12 | C | Task values are set with `dbutils.jobs.taskValues.set` and read with a dynamic value reference. `D` is a job parameter, such as `dq_max_drop_pct`. (Lab 04) | Working with Lakeflow Jobs |
| 13 | B | A repair re-runs only the unsuccessful tasks and their dependants, inside the same run, with a repair history. `D` is false, as found while building the lab: the for-each inputs must give the same number of iterations, which is why we clear `fail_server` instead of changing `servers`. (Lab 04) | Working with Lakeflow Jobs |
| 14 | A | Development mode prefixes names with `[dev <user>]`, pauses schedules and triggers, and marks pipelines as development. Production deploys use `mode: production` and, in CI/CD, a service principal. (M5 demo) | Implementing CI/CD |
| 15 | B | `billing.usage` holds DBUs per SKU with `usage_metadata.dlt_pipeline_id` / `job_id`; `billing.list_prices` gives USD per DBU for each SKU and time window. Real price = list × contract discount. (Lab 06, cost dashboard) | Troubleshooting, Monitoring, and Optimization |
| Bonus | D | Tell the "2,916万" story: the model turned $29,161 into "2,916万美元" (about $29M). Compute in SQL, quote as-is, spot-check. (Lab 07) | — |

## Cert prep: exam sections vs the workshop

Databricks Certified Data Engineer Associate, exam guide May 2026: 45 scored questions in 90 minutes.
Official page: <https://www.databricks.com/learn/certification/data-engineer-associate>.

| Exam section | Weight | Covered in | Quiz questions |
|---|---|---|---|
| Databricks Intelligence Platform | 6% | M1 | 1 |
| Data Ingestion and Loading | 21% | M3 (Lab 02) | 5, 6 |
| Data Transformation and Modeling | 22% | M4 (Labs 03, 03b) | 7, 8, 9 |
| Working with Lakeflow Jobs | 16% | M5 (Lab 04) | 11, 12, 13 |
| Implementing CI/CD | 10% | M5 bundle demo, `docs/cicd_demo.md` | 14 |
| Troubleshooting, Monitoring, and Optimization | 10% | M4 append vs MERGE, M6b (Lab 06) | 10, 15 |
| Governance and Security | 15% | M2 (Lab 01) | 2, 3, 4 |

Ingestion and transformation together are 43% of the exam, so point people who want to sit it at Labs 02–03b
first. Read the exam guide's detailed objectives before recommending further study.
