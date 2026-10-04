# 环境准备指南 · Workspace setup guide (for Triones / workshop admin)

*Hytech "Data Engineering with Databricks" workshop · Shenzhen · 13–14 Oct 2026*

**请在 10 月 9 日（周五）前完成**，这样我们可以在 10 月 12 日（周一）做预演。预计需要约 30 分钟，大部分是等待时间。

**Please finish by Fri 9 Oct** so we can do a dry run on Mon 12 Oct. Expect about 30 minutes, most of it waiting.

## 0 · 你需要 (You need)

| 要求 (Requirement) | 原因 (Why) |
|---|---|
| 工作区管理员（或 catalog 所有者 + `CREATE CATALOG`）| 创建 catalog、volume、授权和 Genie Code skill |
| 无服务器计算（notebook、作业、管道）和一个无服务器 SQL 仓库（Small，最多 3 个集群）| 所有实验都使用无服务器 |
| 基础模型 API 端点可用，例如 `databricks-claude-sonnet-4-5`（或其他对话模型）| 在第 04 和 07 个实验中使用 `ai_query`。在 ap-southeast-1 区域可能需要启用*跨地域处理* |
| 启用 Genie Code | 第 05 个实验 |
| **账户级**组 `de_workshop_sz` 包含约 20 位学员（通过 IdP/SCIM）| Unity Catalog 授权只适用于账户级组。在工作区内创建的组**不**工作 |
| 深圳办公室出站 IP 在工作区的 **IP 访问列表**中| 学员必须从会场网络访问工作区 |

## 1 · 导入代码 (Get the code into the workspace)

**选项 A — Git 文件夹（推荐）:** *Workspace → Create → Git folder* → 输入仓库 URL（向 Zhi Han 请求访问权限）→ 克隆到 `/Workspace/Shared/hytech-de-workshop`。

**Option A — Git folder (recommended):** *Workspace → Create → Git folder* → URL of the repo (ask Zhi Han for
access) → clone into `/Workspace/Shared/hytech-de-workshop`.

**选项 B — zip 文件:** *Workspace → Import* 将仓库归档导入 `/Workspace/Shared/hytech-de-workshop`。

**Option B — zip:** *Workspace → Import* the repo archive into `/Workspace/Shared/hytech-de-workshop`.

## 2 · 安装：一键安装笔记本，推荐 (Set up: the master setup notebook, recommended)

打开 `/Workspace/Shared/hytech-de-workshop/setup/00_master_setup` → 右上角选择 **Serverless** → 填写顶部参数 → **Run all**（约 15 分钟）。它会创建下表中的作业和管道，再依次运行 setup 作业（第 3 节）和参考答案作业（第 4 节）。不需要 Databricks CLI，也不需要修改 `databricks.yml`。可以重复运行：同名的作业和管道会原地更新。

Open `/Workspace/Shared/hytech-de-workshop/setup/00_master_setup` → attach **Serverless** → fill in the widgets at the top → **Run all** (about 15 minutes). It creates the jobs and the pipeline below, then runs the setup job (section 3) and the solution job (section 4) in order. No Databricks CLI needed, and no change to `databricks.yml`. Safe to re-run: jobs and the pipeline with the same name are updated in place.

| 参数 (Widget) | 值 (Value) |
|---|---|
| `catalog` | `hytech_de_workshop` |
| `participant_group` | `de_workshop_sz` |
| `participants` | 学员邮箱，逗号分隔<br>Participant emails, comma-separated |
| `instructors` | Zhi Han 和 Germaine 的邮箱：他们会获得作业、管道和成本仪表盘的管理权限<br>Zhi Han's and Germaine's emails: they get CAN MANAGE on the jobs, the pipeline and the cost dashboard |
| `llm_endpoint` | 你的模型端点，例如 `databricks-claude-sonnet-4-5`<br>Your model endpoint, e.g. `databricks-claude-sonnet-4-5` |
| `warehouse_id` | 可选：成本仪表盘使用的 SQL 仓库<br>Optional: SQL warehouse for the cost dashboard |
| 其他 (Others) | 保持默认：`scale=full`、`reset=false`，两个运行选项为 `true`<br>Keep the defaults: `scale=full`, `reset=false`, both run options `true` |

**方式 B：bundle (Option B: the bundle).** 如果更想用 CLI：从 Git 文件夹打开 `databricks.yml` → 点击 **Deploy**（bundle UI），或使用 CLI，然后按第 3、4 节手动运行两个作业：

If you prefer the CLI: from the Git folder, open `databricks.yml` → **Deploy** (bundle UI), or use the CLI, then run the two jobs yourself as in sections 3 and 4:

```bash
databricks bundle deploy -t prod --var="catalog=hytech_de_workshop" --var="llm_endpoint=<your endpoint>"
```

先在 `databricks.yml` 中设置 `workspace.host` 为你的工作区 URL。（`cicd` 目标是讲师的 CI/CD 演示，详见 `docs/cicd_demo.md`；你不需要部署它。）这会创建：

Set `workspace.host` in `databricks.yml` to your workspace URL first. (The `cicd` target is the instructors'
CI/CD demo, see `docs/cicd_demo.md`; you don't need to deploy it.) This creates:

| 资源 (Resource) | 用途 (Purpose) |
|---|---|
| Job `hytech_ws_setup` | Catalog、schema、volume、授权、综合数据、学员 schema、ops 视图、成本仪表盘、Genie Code skill |
| Job `hytech_ws_drip_producer` | 讲师专用：在实验期间持续生成新 CDC 文件 |
| Pipeline `hytech_trade_lakehouse_solution` | 讲师参考答案（追进度、AI 实验数据）|
| Job `hytech_daily_trading_reporting_solution` | 第 04 个实验的讲师参考答案 |

## 3 · 运行环境搭建作业 (Run the setup job)

一键安装会自动运行这一步；下面的参数用于方式 B 或以后重新运行。<br>
The master setup runs this step for you; the parameters below are for option B or later re-runs.

使用以下作业参数运行 **`hytech_ws_setup`**：

Run **`hytech_ws_setup`** with these job parameters:

| 参数 (Parameter) | 值 (Value) |
|---|---|
| `catalog` | `hytech_de_workshop`（或选择你喜欢的名称：然后在所有地方使用它）|
| `participant_group` | `de_workshop_sz` |
| `participants` | 学员的邮箱地址，用逗号分隔（创建并转移 `u_<name>` schema）|
| `scale` | `full` |
| `reset` | `false`（首次运行生成数据。仅在工作坊**前**重新生成时使用 `true`）|
| `warehouse_id` | 可选：用于成本仪表盘的 SQL 仓库（留空 = 选择无服务器仓库）|

耗时约 10 分钟。检查所有任务是否都是绿色的。`cost_dashboard` 任务会打印仪表盘链接：它位于你的主文件夹（`/Workspace/Users/<你>/hytech_de_workshop`），并与 `de_workshop_sz` 只读共享。请也将其与 Zhi Han 和 Germaine 共享（*Share* → Can Manage）；使用一键安装并填写 `instructors` 时会自动共享。在 `generate_data` 中，摘要应显示 4 台服务器 × 3 张表，每张表有 1 个 LOAD 文件 + 48 个 CDC 文件。

Takes about 10 minutes. Check that every task is green. The `cost_dashboard` task prints the dashboard link: it is
in your home folder (`/Workspace/Users/<you>/hytech_de_workshop`) and shared read-only with `de_workshop_sz`.
Please also share it with Zhi Han and Germaine (*Share* → Can Manage); the master setup does this for you when `instructors` is filled in. In `generate_data`, the summary should show 4 servers ×
3 tables, each with 1 LOAD file + 48 CDC files.

## 4 · 运行参考答案作业 (Run the solution once)

一键安装同样会自动运行这一步。<br>
The master setup runs this step for you too.

运行作业 **`hytech_daily_trading_reporting_solution`**（约 4 分钟）。它运行参考答案管道并填充 `hytech_de_workshop.solutions` — 学员在第 07 个实验和追进度时使用此 schema。

Run job **`hytech_daily_trading_reporting_solution`** (about 4 minutes). It runs the solution pipeline and fills
`hytech_de_workshop.solutions` — participants use this schema in lab 07 and to catch up.

## 5 · 连通性测试 (Connectivity test from the Shenzhen office) — important

从**会场网络**中的笔记本电脑进行测试：

1. 打开工作区 URL → 登录。
2. 打开 `/Workspace/Shared/hytech-de-workshop/labs/00_Start_Here` → 选择 **Serverless** → 运行全部单元格。所有单元格应该都成功。
3. 打开 SQL 编辑器 → `SELECT ai_query('<endpoint>', '用一句话介绍 Databricks')` → 你应该会得到一个答案。

如果任何步骤失败，请向 Zhi Han 和 Germaine 发送截图（Lark/微信）。

From a laptop **on the venue network**:

1. Open the workspace URL → log in.
2. Open `/Workspace/Shared/hytech-de-workshop/labs/00_Start_Here` → attach **Serverless** → run all.
   All cells should succeed.
3. Open the SQL editor → `SELECT ai_query('<endpoint>', '用一句话介绍 Databricks')` → you should get an answer.

If any step fails, send Zhi Han and Germaine a screenshot (Lark/WeChat).

## 6 · 培训期间 (During the workshop)

- 作为工作坊管理员，需要处理权限和网络问题。
- 学员只需要对 `raw` 的读权限，绝不需要直接访问系统表（他们使用 `ops.*` 视图）。

- Be available as workshop admin for permissions and network issues.
- Participants never need access to `raw` beyond read, and never to system tables directly (they use `ops.*` views).

## 7 · 培训之后 (After the workshop)

将 catalog 保留约 2 周，以便学员继续练习。然后运行 `setup/99_teardown`（输入 catalog 名称确认），它也会删除一键安装创建的作业和管道。如果用的是方式 B（bundle），再运行 `databricks bundle destroy -t prod`。

Keep the catalog for about 2 weeks so people can practise. Then run `setup/99_teardown` (type the catalog name
to confirm); it also deletes the jobs and the pipeline the master setup created. If you used option B (the bundle),
also run `databricks bundle destroy -t prod`.
