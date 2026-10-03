# 环境准备指南 · Workspace setup guide (for Triones / workshop admin)

*Hytech "Data Engineering with Databricks" workshop · Shenzhen · 13–14 Oct 2026*

**Please finish by Fri 9 Oct** so we can do a dry run on Mon 12 Oct. Expect about 30 minutes, most of it waiting.

## 0 · 你需要 (You need)

| Requirement | Why |
|---|---|
| Workspace admin (or catalog owner + `CREATE CATALOG`) in the training workspace | Create the catalog, volumes, grants and Genie Code skill |
| Serverless compute (notebooks, jobs, pipelines) and one serverless SQL warehouse (Small, max 3 clusters) | All labs are serverless |
| Foundation Model API endpoint available, e.g. `databricks-claude-sonnet-4-5` (or another chat model) | `ai_query` in labs 04 and 07. In ap-southeast-1 you may need *cross-geography processing* enabled |
| Genie Code enabled | Lab 05 |
| **Account-level** group `de_workshop_sz` containing the ~20 participants (via your IdP/SCIM) | Unity Catalog grants only work with account-level groups. A group created inside the workspace does **not** work |
| Shenzhen office egress IPs on the workspace **IP access list** | Participants must reach the workspace from the venue |

## 1 · 导入代码 (Get the code into the workspace)

**Option A — Git folder (recommended):** *Workspace → Create → Git folder* → URL of the repo (ask Zhi Han for
access) → clone into `/Workspace/Shared/hytech-de-workshop`.

**Option B — zip:** *Workspace → Import* the repo archive into `/Workspace/Shared/hytech-de-workshop`.

## 2 · 部署 (Deploy) — Declarative Automation Bundle

From the Git folder: open `databricks.yml` → **Deploy** (bundle UI), or with the CLI:

```bash
databricks bundle deploy -t prod --var="catalog=hytech_de_workshop" --var="llm_endpoint=<your endpoint>"
```

Set `workspace.host` in `databricks.yml` to your workspace URL first. (The `cicd` target is the instructors'
CI/CD demo, see `docs/cicd_demo.md`; you don't need to deploy it.) This creates:

| Resource | Purpose |
|---|---|
| Job `hytech_ws_setup` | Catalog, schemas, volumes, grants, synthetic data, participant schemas, ops views, cost dashboard, Genie Code skill |
| Job `hytech_ws_drip_producer` | Instructor-only: keeps new CDC files arriving during the labs |
| Pipeline `hytech_trade_lakehouse_solution` | Instructor solution (catch-up, AI lab data) |
| Job `hytech_daily_trading_reporting_solution` | Instructor solution for lab 04 |

## 3 · 运行环境搭建作业 (Run the setup job)

Run **`hytech_ws_setup`** with these job parameters:

| Parameter | Value |
|---|---|
| `catalog` | `hytech_de_workshop` (or a name of your choice: then use it everywhere) |
| `participant_group` | `de_workshop_sz` |
| `participants` | the participants' emails, comma-separated (creates and hands over `u_<name>` schemas) |
| `scale` | `full` |
| `reset` | `false` (first run generates the data. Use `true` only to regenerate **before** the workshop) |
| `warehouse_id` | Optional: SQL warehouse for the cost dashboard (empty = a serverless warehouse is picked) |

Takes about 10 minutes. Check that every task is green. The `cost_dashboard` task prints the dashboard link: it is
in your home folder (`/Workspace/Users/<you>/hytech_de_workshop`) and shared read-only with `de_workshop_sz`.
Please also share it with Zhi Han and Germaine (*Share* → Can Manage). In `generate_data`, the summary should show 4 servers ×
3 tables, each with 1 LOAD file + 48 CDC files.

## 4 · 运行讲师解决方案 (Run the solution once)

Run job **`hytech_daily_trading_reporting_solution`** (about 4 minutes). It runs the solution pipeline and fills
`hytech_de_workshop.solutions` — participants use this schema in lab 07 and to catch up.

## 5 · 连通性测试 (Connectivity test from the Shenzhen office) — important

From a laptop **on the venue network**:

1. Open the workspace URL → log in.
2. Open `/Workspace/Shared/hytech-de-workshop/labs/00_Start_Here` → attach **Serverless** → run all.
   All cells should succeed.
3. Open the SQL editor → `SELECT ai_query('<endpoint>', '用一句话介绍 Databricks')` → you should get an answer.

If any step fails, send Zhi Han and Germaine a screenshot (Lark/WeChat).

## 6 · 培训期间 (During the workshop)

- Be available as workshop admin for permissions and network issues.
- Participants never need access to `raw` beyond read, and never to system tables directly (they use `ops.*` views).

## 7 · 培训之后 (After the workshop)

Keep the catalog for about 2 weeks so people can practise. Then run `setup/99_teardown` (type the catalog name
to confirm) and `databricks bundle destroy -t prod`.
