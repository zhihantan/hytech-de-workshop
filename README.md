# Hytech · Data Engineering with Databricks — MT5 Trade Lakehouse Workshop (Hytech · Databricks 数据工程 — MT5 交易湖仓工作坊)

一份完整的、实践性强的 **2 × 半天工作坊（普通话授课）**，面向 Hytech 深圳数据工程团队。学员将按照 Hytech 生产系统的架构模式，搭建一个**交易湖仓**。

A self-contained, hands-on **2 × half-day workshop (Mandarin)** for Hytech's Shenzhen data-engineering team.
Participants build a production-style **trade lakehouse** on the same pattern Hytech runs in production:

> MT5 MySQL → AWS DMS (full load + CDC Parquet) → **Auto Loader** → **Lakeflow Spark Declarative Pipelines**
> (bronze → silver with AUTO CDC + expectations → gold marts) → **Lakeflow Jobs** (DQ gate, for-each, Run-if,
> repair) — governed by **Unity Catalog**, observed with **system tables**, assisted by **Genie Code** and
> **AI Functions**.

所有数据都是**合成数据**（预设种子，无真实客户）。全部无服务器架构、幂等且端到端验证（见下文 *Verified* 部分）。

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

## 快速开始：讲师与 Hytech 管理员 (Quick start: instructors / Hytech admin)

1. 把代码库放进工作区（Git 文件夹），然后二选一：<br>
   Put the repo in the workspace (Git folder), then choose one:

   **方式 A（推荐）：一键安装笔记本。** 打开 `setup/00_master_setup` → 选择 **Serverless** → 填写顶部参数 → **Run all**（约 15 分钟）。它会创建全部作业和管道，再依次运行 setup 作业和参考答案作业。不需要 CLI，也不需要修改 `databricks.yml`。

   **Option A (recommended): the master setup notebook.** Open `setup/00_master_setup` → attach **Serverless** → fill in the widgets at the top → **Run all** (about 15 minutes). It creates every job and the pipeline, then runs the setup job and the solution job in order. No CLI needed, and no change to `databricks.yml`.

   **方式 B：bundle（讲师开发和 CI/CD 演示用）。** 在本地电脑上部署：

   **Option B: the bundle (for instructor development and the CI/CD demo).** Deploy from your laptop:

   ```bash
   databricks bundle deploy -t dev            # or -t prod for the shared deployment
   databricks bundle run hytech_ws_setup      # catalog, synthetic data, ops views, cost dashboard, Genie Code skill (~10 min)
   databricks bundle run hytech_daily_trading_reporting_solution   # fills the solutions schema (~4 min)
   ```

   设置 `databricks.yml` 中的 `workspace.host` 和变量 `catalog`、`llm_endpoint`、`participant_group`。

   Set `workspace.host` in `databricks.yml` and the variables `catalog`, `llm_endpoint`, `participant_group`.

2. 在课堂期间，用作业 **`hytech_ws_drip_producer`** 驱动实时数据（见讲师指南）。

   During class, drive the live data with job **`hytech_ws_drip_producer`** (see the facilitator guide).

3. 学员从 **`labs/00_Start_Here`** 开始。

   Participants start at **`labs/00_Start_Here`**.

Hytech 管理员的完整检查清单：[`docs/setup_guide_triones.md`](docs/setup_guide_triones.md)。

Full checklist for Hytech's admin: [`docs/setup_guide_triones.md`](docs/setup_guide_triones.md).

## 文档 (Documents)

| 文档 (Doc) | 用途 (For) |
|---|---|
| [`docs/workshop_plan.md`](docs/workshop_plan.md) | 目标、故事线、议程、构建计划、风险<br>Goals, storyline, agenda, build plan, risks |
| [`docs/facilitator_guide.md`](docs/facilitator_guide.md) | 现场表演流程、讲师控制、精彩时刻、验证证据<br>Run of show, instructor controls, wow moments, verification evidence |
| [`docs/setup_guide_triones.md`](docs/setup_guide_triones.md) | Hytech 管理员的工作区设置<br>Workspace setup by the Hytech admin |
| [`docs/participant_guide_zh.md`](docs/participant_guide_zh.md) | 学员快速开始（中文）<br>Participant quick start (Chinese) |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | 已知问题和解决方案<br>Known errors and fixes |
| [`docs/cicd_demo.md`](docs/cicd_demo.md) | CI/CD 演示：作为服务主体部署、GitLab 模板<br>CI/CD demo: deploy as a service principal, GitLab template |
| [`docs/knowledge_check_answers.md`](docs/knowledge_check_answers.md) | 测验答案和考试部分映射（讲师用）<br>Quiz answers and exam-section mapping (instructors) |

## 实验 (Labs)

| 模块 (Module) | 实验 (`labs/`) | 参考答案 (Solution) |
|---|---|---|
| M1 | `00_Start_Here` — 自己的 schema、浏览 DMS 文件、复制实验<br>`00_Start_Here` — own schema, explore DMS files, copy labs | — |
| M2 Unity Catalog | `01_Unity_Catalog` — 授权、视图、标签、列掩码、行过滤器<br>`01_Unity_Catalog` — grants, views, tags, column mask, row filter | `solutions/01_Unity_Catalog` |
| M3 数据接入 (Ingestion) | `02_Ingestion` — CTAS、COPY INTO、Auto Loader、JSON + 救援数据<br>`02_Ingestion` — CTAS, COPY INTO, Auto Loader, JSON + rescued data | `solutions/02_Ingestion` |
| M4 管道 (Pipelines) | `03_pipeline/` + `03b_Explore_Pipeline` | `solutions/pipeline/` |
| M5 作业 (Jobs) | `04_Lakeflow_Jobs.md` (UI) + `04b_Jobs_Catch_Up` | `resources/solution.job.yml` |
| M6 Genie Code | `05_Genie_Code.md` 提示词梯度 + 技能 `genie_code/.assistant/skills/hytech-de-conventions`<br>`05_Genie_Code.md` prompt ladder + skill `genie_code/.assistant/skills/hytech-de-conventions` | — |
| M6 系统表 (System tables) | `06_System_Tables`（通过受治理的 `ops` 视图）<br>`06_System_Tables` (via governed `ops` views) | `solutions/06_System_Tables` |
| AI 函数 (AI Functions) | `07_AI_Functions` — `ai_query` (中文), `ai_classify`, `ai_mask`, 情感分析<br>`07_AI_Functions` — `ai_query` (中文), `ai_classify`, `ai_mask`, sentiment | `solutions/07_AI_Functions` |
| M6c 总结 (Recap) | `08_Knowledge_Check` — 15 道题 + 加分题，映射到考试指南<br>`08_Knowledge_Check` — 15 questions + bonus, mapped to the exam guide | `docs/knowledge_check_answers.md` |

## 代码库布局 (Repository layout)

| 路径 (Path) | 说明 (What) |
|---|---|
| `databricks.yml`, `resources/` | 声明式自动化包：设置作业、滴灌程序、参考答案管道和作业（`dev`、`prod` 和 `cicd` 目标）<br>Declarative Automation Bundle: setup job, drip producer, solution pipeline and job (`dev`, `prod` and `cicd` targets) |
| `setup/` | `00_master_setup`（一键创建并运行全部作业）、`01`–`07` 设置笔记本（`07` 发布成本仪表盘）、`03_drip_producer`、`99_teardown`<br>`00_master_setup` (creates and runs every job in one go), `01`–`07` setup notebooks (`07` publishes the cost dashboard), `03_drip_producer`, `99_teardown` |
| `dashboards/` | AI/BI 成本和健康仪表盘（JSON 格式），基于 `ops` 视图<br>AI/BI cost & health dashboard (JSON) over the `ops` views |
| `cicd/` | GitLab CI 模板（在合并请求时验证、作为服务主体部署）和 `deploy_as_service_principal.sh` 实时演示脚本<br>GitLab CI template (validate on merge requests, deploy as a service principal) and `deploy_as_service_principal.sh` for the live demo |
| `src/hytech_workshop/` | 合成数据生成器：MT5 用户/成交/持仓（作为 DMS CDC）、应用事件、参考数据、滴灌程序<br>Synthetic data generator: MT5 users/deals/positions as DMS CDC, app events, reference data, drip producer |
| `solutions/pipeline/transformations/` | 参考管道（Python Auto Loader bronze + SQL silver/gold）<br>Reference pipeline (Python Auto Loader bronze + SQL silver/gold) |
| `jobs/` | 作业任务笔记本：`dq_gate`、`reconcile_server`、`publish_daily_summary`、`notify`、`audit`<br>Job task notebooks: `dq_gate`, `reconcile_server`, `publish_daily_summary`, `notify`, `audit` |
| `labs/` | 学员笔记本：完整代码，关键步骤有「要点」注释<br>Participant notebooks: complete code, with "Key point" comments on the key steps |
| `genie_code/` | Genie Code 技能 + 提示词梯度<br>Genie Code skill + prompt ladder |
| `tests/` | 本地生成器测试（`pytest tests/`）<br>Local generator tests (`pytest tests/`) |

## 值得了解的设计选择 (Design choices worth knowing)

- **追加 vs MERGE。** 成交（约 99.9% 是插入）是一个只追加的流式表。少数修正和删除进入一个小的 AUTO CDC 表，在物化视图中合并。这反映了 Hytech 实时 POC 的重新设计。

  **Append vs MERGE.** Deals (~99.9% inserts) are an append-only streaming table. The rare corrections and
  deletes go to a small AUTO CDC table, combined in an MV. This mirrors the redesign from Hytech's real-time POC.

- **数据契约 + 救援数据。** 应用事件使用显式 schema。漂移字段和类型不匹配进入 `_rescued_data` 并在 silver 层恢复。

  **Data contract + rescued data.** App events use an explicit schema. Drifted fields and type mismatches land
  in `_rescued_data` and are recovered in silver.

- **受治理的可观测性。** 学员只能通过 `ops.*` 视图查询系统表：仅限该工作区、无 SQL 文本、其他用户身份已掩盖。

  **Governed observability.** Participants query system tables only through `ops.*` views: this workspace only,
  no SQL text, other users' identities masked.

- **大语言模型数据。** AI 总结在 SQL 中预先计算每个数字；模型只对其进行措辞（第 07 个实验中的课程）。

  **LLM numbers.** The AI summary pre-computes every figure in SQL; the model only words it (lesson in lab 07).

## 在 `fe-vm-zh-serverless-ws` (AWS us-west-2) 上验证，2026 年 10 月 3 日 (Verified on `fe-vm-zh-serverless-ws` (AWS us-west-2), 3 Oct 2026)

- **设置 (Setup):** 跨 4 台服务器约 78.5 万笔成交，14.1 万条应用事件。

  **Setup:** ~785k deals across 4 servers, 141k app events.

- **参考答案管道 (Solution pipeline):** 绿色。期望过滤了 1,238 笔无效交易；SCD2 历史、修正和救援数据均已验证。

  **Solution pipeline:** green. Expectations dropped 1,238 invalid trades; SCD2 history, corrections and rescued
  data all verified.

- **参考答案作业 (Solution job):**
  - 正常路径 → 中文 AI 总结 (happy path → Chinese AI summary)
  - 循环任务失败 → 运行条件和审计 (for-each failure → Run-if alert and audit)
  - 上线 `mt5-hk-01` → 修复运行 (onboard `mt5-hk-01` → repair run)
  - 坏批次 → DQ 告警分支 (bad batch → DQ alert branch)

- **学员流程 (Participant flow):** 实验 00 → 自己的管道 → 追进度作业 → 模拟失败 → 修复 → 绿色。

  Lab 00 → own pipeline → catch-up job → simulated failure → repair → green.

- **笔记本 (Notebooks):** 实验 01、02、03b、06 和 07 无头执行。

  Labs 01, 02, 03b, 06 and 07 executed headless.

- **成本仪表盘 (Cost dashboard):** 由设置作业发布；在浏览器中检查了两个页面。

  Published by the setup job; both pages checked in the browser.

- **CI/CD:** `cicd` 目标由服务主体通过 OAuth M2M 部署和运行，如 `cicd/gitlab-ci.yml` 所做的那样。

  The `cicd` target deployed and run by a service principal over OAuth M2M, as `cicd/gitlab-ci.yml` does.

- **一键安装 (Master setup):** `setup/00_master_setup` 不用 CLI 创建并运行了全部作业和管道；重复运行时原地更新。

  `setup/00_master_setup` created and ran every job and the pipeline without the CLI; a re-run updated them in place.

详情：[`docs/facilitator_guide.md`](docs/facilitator_guide.md#在-fevm-上的验证结果-verified-on-fevm-fe-vm-zh-serverless-ws-3-oct-2026)。

Details: [`docs/facilitator_guide.md`](docs/facilitator_guide.md#在-fevm-上的验证结果-verified-on-fevm-fe-vm-zh-serverless-ws-3-oct-2026).
