# 知识测验：答案与讲解（仅限讲师）(Knowledge check — answer key, instructors only)

用于 `labs/08_Knowledge_Check.md`（M6c，第 2 天 11:30）。约 15 分钟回答，10 分钟讲解答案。在实验 07 后进行加分问题。要将其作为实时投票运行，请将问题粘贴到 Lark（Feishu）表单中，在中国大陆有效；否则对每个选项使用举手表决。

For `labs/08_Knowledge_Check.md` (M6c, Day 2 11:30). About 15 minutes to answer and 10 to go through the answers. Take the bonus question after Lab 07. To run it as a live poll, paste the questions into a Lark (Feishu) form, which works in mainland China; otherwise use a show of hands per option.

**答案 (Answers)：** 1 C · 2 D · 3 A · 4 C · 5 B · 6 D · 7 A · 8 B · 9 C · 10 D · 11 A · 12 C · 13 B · 14 A · 15 B · Bonus D

| # | 答案 (Answer) | 为什么（以及我们在哪里看到它）(Why — and where we saw it) | 考试部分 (Exam section) |
|---|---|---|---|
| 1 | C | Volume 使用与表相同的三级命名空间：`catalog.schema.volume`。元存储位于 catalog 之上，永不在路径中。（实验 00）| 平台 (Platform) |
| 2 | D | `SELECT` 单独不够：组还需要在 catalog 上使用 `USE CATALOG`，在 schema 上使用 `USE SCHEMA`。`ALL PRIVILEGES` 远超所需。（实验 01）| 治理和安全 (Governance and Security) |
| 3 | A | 列掩码按调用者隐藏 `email`；行过滤器按品牌限制行。标签仅分类列：除非 ABAC 策略使用它，否则不强制执行任何内容。每个品牌的副本漂移。（实验 01）| 治理和安全 (Governance and Security) |
| 4 | C | 血缘在 Unity Catalog 计算上的工作负载中自动捕获，在表和列级别。显示在 Catalog Explorer 和 `system.access.table_lineage` 中。（实验 01 演示，实验 06）| 治理和安全 (Governance and Security) |
| 5 | B | 实验 02 中的第二个 `COPY INTO` 加载了 0 行，因为它跳过已加载的文件。Auto Loader 在检查点中保持发现的文件，所以可扩展到数百万文件。（实验 02）| 数据接入和加载 (Data Ingestion and Loading) |
| 6 | D | 使用数据合同（显式 schema），不适配的值转到 `_rescued_data` 而不是丢失；silver 用 `get_json_object` 恢复它们。（实验 02，`silver_app_events`）| 数据接入和加载 (Data Ingestion and Loading) |
| 7 | A | 流式表处理每个新输入一次，适合只追加源。输入会改变的聚合和联接属于物化视图。（实验 03）| 数据转换和建模 (Data Transformation and Modeling) |
| 8 | B | `KEYS` 识别行；`SEQUENCE BY` 为每个键排序更改，所以延迟或乱序事件无法覆盖更新的事件。SCD2 也为 `__START_AT` / `__END_AT` 使用它。（实验 03）| 数据转换和建模 (Data Transformation and Modeling) |
| 9 | C | 三种模式：无 `ON VIOLATION` 保留行并记录它（我们的 `deal_time_not_in_future`），`DROP ROW` 丢弃它，`FAIL UPDATE` 停止更新。隔离表是你自己构建的东西。`dq_gate` 从事件日志读取这些计数。（实验 03、04）| 数据转换和建模 (Data Transformation and Modeling) |
| 10 | D | MERGE 成本随目标大小增长；追加仅随新数据增长。`A` 错误：`APPLY AS DELETE WHEN` 应用删除。在两个表上显示 `DESCRIBE HISTORY`。（实验 03b）| 故障排除、监控和优化 (Troubleshooting, Monitoring, and Optimization) |
| 11 | A | `At least one failed` 用于告警，`All done` 用于审计行。这就是为什么解决方案运行在失败后显示*成功但有失败*。（实验 04）| 使用 Lakeflow 作业 (Working with Lakeflow Jobs) |
| 12 | C | 任务值使用 `dbutils.jobs.taskValues.set` 设置，使用动态值引用读取。`D` 是作业参数，如 `dq_max_drop_pct`。（实验 04）| 使用 Lakeflow 作业 (Working with Lakeflow Jobs) |
| 13 | B | 修复仅重新运行失败的任务及其依赖者，在同一运行内，有修复历史。`D` 错误，如构建实验时发现：循环任务输入必须给出相同数量的迭代，这就是为什么我们清 `fail_server` 而不改变 `servers`。（实验 04）| 使用 Lakeflow 作业 (Working with Lakeflow Jobs) |
| 14 | A | 开发模式使用 `[dev <user>]` 前缀名称，暂停计划和触发器，并标记管道为开发。生产部署使用 `mode: production` 和，在 CI/CD 中，服务主体。（M5 演示）| 实现 CI/CD (Implementing CI/CD) |
| 15 | B | `billing.usage` 按 SKU 保留 DBU，其中 `usage_metadata.dlt_pipeline_id` / `job_id`；`billing.list_prices` 为每个 SKU 和时间窗口给出 USD 每 DBU。实际价格 = 标价 × 合同折扣。（实验 06，成本仪表盘）| 故障排除、监控和优化 (Troubleshooting, Monitoring, and Optimization) |
| 加分 (Bonus) | D | 讲"2,916万"故事：模型将 $29,161 变成"2,916万美元"（约 $29M）。在 SQL 中计算，按原样引用，点检。（实验 07）| — |

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

## 认证备考：考试各部分 vs 工作坊 (Cert prep: exam sections vs the workshop)

Databricks 认证数据工程师副等（Databricks Certified Data Engineer Associate），考试指南 2026 年 5 月：90 分钟内 45 道计分题。
官方页面：<https://www.databricks.com/learn/certification/data-engineer-associate>。

| 考试部分 (Exam section) | 权重 (Weight) | 涵盖在 (Covered in) | 测验问题 (Quiz questions) |
|---|---|---|---|
| Databricks 智能平台 (Databricks Intelligence Platform) | 6% | M1 | 1 |
| 数据接入和加载 (Data Ingestion and Loading) | 21% | M3（实验 02）| 5, 6 |
| 数据转换和建模 (Data Transformation and Modeling) | 22% | M4（实验 03、03b）| 7, 8, 9 |
| 使用 Lakeflow 作业 (Working with Lakeflow Jobs) | 16% | M5（实验 04）| 11, 12, 13 |
| 实现 CI/CD (Implementing CI/CD) | 10% | M5 包演示，`docs/cicd_demo.md` | 14 |
| 故障排除、监控和优化 (Troubleshooting, Monitoring, and Optimization) | 10% | M4 追加 vs MERGE，M6b（实验 06）| 10, 15 |
| 治理和安全 (Governance and Security) | 15% | M2（实验 01）| 2, 3, 4 |

数据接入和数据转换合计占考试的 43%，建议想考认证的学员先重点复习实验 02–03b。推荐其他学习内容之前，请先阅读考试指南中的详细考点。

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

Ingestion and transformation together are 43% of the exam, so point people who want to sit it at Labs 02–03b first. Read the exam guide's detailed objectives before recommending further study.
