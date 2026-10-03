# Lab 04 · Lakeflow Jobs — 像生产一样调度 (orchestrate like production)

**目标 (Goal):** 在 UI 中搭建作业 `daily_trading_reporting_<your_name>`：运行你的管道 → 数据质量闸门（if/else）→
AI 每日简报或告警；按服务器 for-each 对账；失败告警（Run if）；审计（Run if）；然后制造一次失败并用 **Repair run** 修复。

```
run_pipeline ─┬─► dq_gate ─► dq_ok (if/else) ─┬─ true  ─► publish_daily_summary
              │                               └─ false ─► notify_dq_owner
              └─► reconcile_servers (for each server) ─► reconcile_server
alert_on_failure  Run if: At least one failed     (deps: run_pipeline, dq_gate, reconcile_servers, publish_daily_summary)
write_audit_row   Run if: All done                (deps: alert_on_failure, notify_dq_owner, publish_daily_summary, reconcile_servers)
```

> 任务用到的 notebook 已经在 `/Users/<you>/hytech_de_lab/jobs/`（Lab 00 复制过来的）。
> 落后了？运行 `04b_Jobs_Catch_Up` 自动创建同样的作业 (catch-up creates the same job for you).

## 1 · 创建作业与参数 (Create the job and its parameters)

**Jobs & Pipelines → Create → Job**, name `daily_trading_reporting_<your_name>`. Then add **Job parameters**:

| Key | Value |
|---|---|
| `catalog` | `hytech_de_workshop` |
| `schema` | `u_<your_name>` |
| `dq_max_drop_pct` | `1.0` |
| `servers` | `["mt5-sg-01","mt5-sg-02","mt5-uk-01","mt5-cy-01"]` |
| `llm_endpoint` | `databricks-claude-sonnet-4-5` (or the endpoint the instructor gives you) |
| `fail_server` | `mt5-uk-01` ← 故意制造失败 (to practise repair) |

Job parameters are passed automatically to every notebook task (as widgets).

## 2 · 添加任务 (Add the tasks)

| # | Task name | Type | Settings |
|---|---|---|---|
| 1 | `run_pipeline` | **Pipeline** | your pipeline `trade_lakehouse_<your_name>`; *Retries*: 1 |
| 2 | `dq_gate` | Notebook | `.../hytech_de_lab/jobs/dq_gate`; depends on `run_pipeline` |
| 3 | `dq_ok` | **If/else condition** | `{{tasks.dq_gate.values.dq_drop_pct}}` **<** `{{job.parameters.dq_max_drop_pct}}`; depends on `dq_gate` |
| 4 | `publish_daily_summary` | Notebook | `.../jobs/publish_daily_summary`; depends on `dq_ok` = **true** |
| 5 | `notify_dq_owner` | Notebook | `.../jobs/notify`; depends on `dq_ok` = **false**; parameters `reason` = `dq_gate_failed`, `detail` = `{{tasks.dq_gate.values.dq_drop_pct}}`, `job_id` = `{{job.id}}`, `run_id` = `{{job.run_id}}` |
| 6 | `reconcile_servers` | **For each** | Inputs `{{job.parameters.servers}}`, concurrency 4; nested task: Notebook `.../jobs/reconcile_server` with parameter `server_id` = `{{input}}`; depends on `run_pipeline` |
| 7 | `alert_on_failure` | Notebook | `.../jobs/notify`; depends on 1, 2, 6, 4; **Run if: At least one failed**; parameters `reason` = `job_task_failed`, `job_id` = `{{job.id}}`, `run_id` = `{{job.run_id}}` |
| 8 | `write_audit_row` | Notebook | `.../jobs/audit`; depends on 7, 5, 4, 6; **Run if: All done**; parameters `job_id` = `{{job.id}}`, `run_id` = `{{job.run_id}}` |

Compute: **Serverless** for every task.

## 3 · 运行、失败、修复 (Run → fail → repair)

1. **Run now.** Watch the graph: `reconcile_servers` → the `mt5-uk-01` iteration fails (simulated);
   `alert_on_failure` runs (*At least one failed*); `write_audit_row` still runs (*All done*).
   Note the run status **Succeeded with failures**: the leaf tasks succeeded, but a task in the middle failed.
2. Open the failed iteration → read the error. (Genie Code: ask *“为什么失败？如何只重跑失败的任务？”*)
3. **Repair run** → edit the job parameter `fail_server` to empty → repair.
   Only the failed tasks and their dependants re-run; the pipeline is **not** re-run.
   ⚠️ A repair must resolve the for-each to the **same number of iterations** as the original run:
   keep the `servers` list unchanged.
4. Check the output tables in your schema: `ops_dq_results`, `ops_reconciliation`, `ops_alerts`,
   `ops_job_audit`, `gold_daily_commentary`.

## 4 · 触发器与通知 (Triggers and notifications)

- **Add trigger → File arrival** on `/Volumes/hytech_de_workshop/raw/landing/mt5/` (minimum 60 s between
  triggers). The instructor's drip producer writes new files → your job starts by itself.
  **Pause** the trigger again after the demo, so 20 jobs don't keep firing.
- Alternatives: **Scheduled** (e.g. hourly), **Table update** (start when an upstream table changes:
  useful for dependencies between teams' pipelines), **Continuous**.
- **Job notifications → On failure → your email.**

## 5 · 代码即作业 (Jobs as code → CI/CD)

Open your job → **⋮ → View as code (YAML)** and compare with `resources/solution.job.yml` in the repo.
That YAML is deployed with **Declarative Automation Bundles** (`databricks bundle deploy -t prod`),
from GitLab CI, running as a service principal. This is how Hytech can **remove direct access to
production**: changes go through review and CI/CD, and nobody edits prod by hand.

## 6 · 讲师演示 (Instructor demos)

- **Onboard a new server live:** the drip producer with `new_server=mt5-hk-01` (DMS full load + CDC). The
  bronze glob `mt5/*/<table>/` picks it up on the next pipeline run, with no code change.
- **Bad batch:** the drip producer with `bad_batch_pct=60`. Expectations drop the bad rows, `dq_drop_pct`
  goes above 1%, the condition takes the **false** branch, and `notify_dq_owner` raises the alert.
