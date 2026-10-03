# 学员指南 · Hytech「Data Engineering with Databricks」工作坊

**时间:** 10 月 13–14 日 09:30–13:00 · **地点:** 深圳南山区后海联想中心（Hytech 办公室）· **语言:** 中文

## 课前准备 (Before the workshop)

1. 用公司账号登录 Databricks 工作区（Triones 会发链接）。在**办公室网络**下确认能打开。
2. 推荐预习（自学，中文）：[Databricks Fundamentals (Mandarin Chinese)](https://www.databricks.com/training/catalog/databricks-fundamentals-mandarin-chinese-5940)
3. 基础要求：SQL、中级 Python、Spark DataFrame 基础。

## 第一步 (Step 1)

打开 `/Workspace/Shared/hytech-de-workshop/labs/00_Start_Here` → 右上角选择 **Serverless** → 逐个运行单元格。它会：

- 创建你的 schema：`hytech_de_workshop.u_<你的名字>`
- 把所有实验复制到 `/Users/<你>/hytech_de_lab/`。之后**只在你自己的副本里操作**。

## 实验地图 (Lab map)

| 模块 | 实验 | 要点 |
|---|---|---|
| M2 | `01_Unity_Catalog` | 授权给组、视图、标签、列掩码、行过滤、血缘 |
| M3 | `02_Ingestion` | CTAS / COPY INTO / Auto Loader / JSON + `_rescued_data` |
| M4 | `03_pipeline/`（先读 README）+ `03b_Explore_Pipeline` | 声明式管道：bronze → silver（AUTO CDC、期望）→ gold |
| M5 | `04_Lakeflow_Jobs.md` | 作业：if/else、for-each、Run if、修复运行、触发器 |
| M6 | `05_Genie_Code.md` · `06_System_Tables` | Genie Code 提示词阶梯；成本 / 运行 / 血缘 |
| M6c | `08_Knowledge_Check.md` | 知识测验：15 道单选题 + 加分题，对应认证考试大纲 |
| AI | `07_AI_Functions` | `ai_query`（中文简报）、`ai_classify`、`ai_mask` |

每个实验都有 `TODO`，答案在 `solutions/`。**跟不上没关系**：复制答案文件，继续下一步。

## 数据是什么 (What is the data?)

**模拟数据**（不是真实客户数据），按 Hytech 的真实架构设计：

- 4 台 MT5 交易服务器（`mt5-sg-01`、`mt5-sg-02`、`mt5-uk-01`、`mt5-cy-01`）
- AWS DMS 格式的 Parquet 文件：全量 `LOAD00000001.parquet` + 增量 CDC 文件，带 `Op`（I/U/D）和 `cdc_ts`
- 表：`mt5_users`（客户账户）、`mt5_deals`（成交与出入金）、`mt5_positions`（持仓）、App 埋点事件 JSON
- 讲师的“滴灌”程序在课堂上持续写入新文件，模拟实时数据

## 小贴士 (Tips)

- Genie Code 可以用中文提问，选择 **Agent mode**，用 `@表名` 提供上下文。
- 管道报错时，先看错误信息里的文件和行号，再对照 `TODO`。
- 不要修改 `raw`、`solutions`、`ops` 下的任何东西（你也没有权限）。
- 课后两周内环境保留，可以继续练习。
