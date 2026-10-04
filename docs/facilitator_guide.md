# 讲师指南：Hytech DE 工作坊 (Facilitator guide — Hytech DE workshop) · Zhi Han & Germaine

一位讲师主讲，另一位巡场答疑，每个模块轮换。面对 20 名新学员，巡场讲师直接决定是"多数人完成"还是"多数人卡住"。分工建议见 `docs/workshop_plan.md` §4。

One instructor presents while the other floats; swap per module. With 20 newcomers the floater is the difference between "most finished" and "most stuck". Split proposal in `docs/workshop_plan.md` §4.

## 开课前 (Before the day)

- [ ] Triones 已完成 `docs/setup_guide_triones.md`，包括**在会场完成的连通性测试**
- [ ] 参考答案作业已运行一次 → `hytech_de_workshop.solutions` 已有数据（实验 07 和追进度都依赖它）
- [ ] `llm_endpoint` 已设为 Hytech 所在区域可用的模型（在 SQL 编辑器中测试 `ai_query`）
- [ ] Genie Code 技能在 `/Workspace/.assistant/skills/hytech-de-conventions/` 可见
- [ ] 成本仪表盘 *Hytech DE Workshop - Cost and Health* 已发布（setup 任务 `cost_dashboard`）
- [ ] CI/CD 演示：服务主体 `hytech-ws-cicd`、相关授权，以及一次成功的 `[cicd]` 运行（已于 10 月 3 日在 FEVM 完成）。当天由 `cicd/deploy_as_service_principal.sh` 自动创建并删除临时密钥（`docs/cicd_demo.md`）
- [ ] 幻灯片以 **PDF/PPTX 存在借用的笔记本电脑上**（中国大陆不使用 VPN 时无法访问 Google Workspace）
- [ ] 10 月 12 日（周一）晚上预演，最好使用一个 Hytech 学员账号

- [ ] Triones has completed `docs/setup_guide_triones.md`, including the **connectivity test from the venue**
- [ ] Solution job ran once → `hytech_de_workshop.solutions` is populated (lab 07 and catch-up depend on it)
- [ ] `llm_endpoint` set to a model served in Hytech's region (test `ai_query` in the SQL editor)
- [ ] Genie Code skill visible at `/Workspace/.assistant/skills/hytech-de-conventions/`
- [ ] Cost dashboard *Hytech DE Workshop - Cost and Health* published (setup task `cost_dashboard`)
- [ ] CI/CD demo: service principal `hytech-ws-cicd`, its grants and a green `[cicd]` run (done on FEVM, 3 Oct). On the day, `cicd/deploy_as_service_principal.sh` creates and deletes its own temporary secret (`docs/cicd_demo.md`)
- [ ] Slides as **PDF/PPTX on the loaner laptop** (Google Workspace is blocked in mainland China without VPN)
- [ ] Dry run on Mon 12 Oct evening, ideally with one Hytech participant account

## 讲师控制：作业 `hytech_ws_drip_producer` (Instructor controls: job `hytech_ws_drip_producer`)

| 何时 (When) | 参数 (Parameters) | 效果 (Effect) |
|---|---|---|
| M3 开始（第 1 天，约 10:30）| `duration_minutes=150`, `interval_seconds=30` | M3–M4 期间持续有新的 CDC 文件到达 |
| 第 2 天开始（约 09:30）| `duration_minutes=150` | 为作业实验和文件到达触发器提供实时数据 |
| M5 演示，所有人完成首次运行后 | `new_server=mt5-hk-01`, `duration_minutes=10` | **上线一台新的 MT5 服务器**（全量 + CDC）。下一次管道运行无需改代码即可接入 |
| M5 演示 | `bad_batch_pct=60`, `duration_minutes=2` | 坏批次 → 下一次作业运行时 DQ 门走 **false** 分支 |

同一时间只能有一个滴灌运行（`max_concurrent_runs: 1`）。取消该运行即可提前停止。

| When | Parameters | Effect |
|---|---|---|
| Start of M3 (Day 1, ~10:30) | `duration_minutes=150`, `interval_seconds=30` | New CDC files keep arriving through M3–M4 |
| Start of Day 2 (~09:30) | `duration_minutes=150` | Live data for the Jobs lab and file-arrival triggers |
| M5 demo, after everyone's first run | `new_server=mt5-hk-01`, `duration_minutes=10` | **Onboard a new MT5 server** (full load + CDC). The next pipeline run ingests it with no code change |
| M5 demo | `bad_batch_pct=60`, `duration_minutes=2` | Bad batch → the DQ gate takes the **false** branch on the next job run |

Only one drip run at a time (`max_concurrent_runs: 1`). Cancel the run to stop it early.

## 第 1 天流程 (Day 1 — run of show)

| 时间 (Time) | 环节 (Segment) | 备注 (Notes) |
|---|---|---|
| 09:30 | **M1** 平台概览（30）| 数据湖仓、Unity Catalog、无服务器、声明式管道、Genie。展示 Hytech 的架构（MySQL → DMS → S3 → Auto Loader → SDP → Power BI/Genie），对照 `docs/workshop_plan.md` §2。**实验 00** 放在最后 10 分钟：每人创建自己的 schema 并复制实验 |
| 10:00 | **M2** Unity Catalog（30）| 实验 01。讲解要点：标签 + 掩码就是 Robin 那套列标签检查框架的 UC 原生版本；受治理标签会强制限定允许的取值。演示：Catalog Explorer 血缘、访问申请 |
| 10:30 | **M3** 数据接入（45）| **启动滴灌程序。** 实验 02。一分钟后重新运行 Auto Loader 单元格，指出它只处理新文件。演示：Lakeflow Connect NetSuite（GA）和 MySQL CDC（预览版），作为不依赖 DMS 的方案 |
| 11:15 | **M4** 声明式管道（60）| 实验 03：按 README 创建管道，填写 5 个 TODO，运行。**要点：追加 vs MERGE**：mt5_deals 约 99.9% 是插入 → 只追加 + 很小的更正表。在 Hytech 的 POC 中，这次重新设计把成本从约 $480/天降到 $40/天以下（数字仅供讲师掌握）。演示：用 Lakeflow Designer 制作 IB 周报 |
| 12:15 | 问答（30）| 追进度：从 `solutions/pipeline/transformations/` 复制文件。已完成的学员做实验 03b |

| Time | Segment | Notes |
|---|---|---|
| 09:30 | **M1** Platform overview (30) | Lakehouse, UC, serverless, Lakeflow, Genie. Show Hytech's architecture (MySQL → DMS → S3 → Auto Loader → SDP → Power BI/Genie) next to `docs/workshop_plan.md` §2. **Lab 00** last 10 min: everyone creates their schema and copies the labs |
| 10:00 | **M2** Unity Catalog (30) | Lab 01. Talk track: tags + masks are the UC-native version of Robin's column-tag check framework; governed tags enforce allowed values. Demo: Catalog Explorer lineage, access requests |
| 10:30 | **M3** Ingestion (45) | **Start the drip producer.** Lab 02. Re-run the Auto Loader cell after a minute and point out the new files only. Demo: Lakeflow Connect NetSuite (GA) and MySQL CDC (preview) as the DMS-free path |
| 11:15 | **M4** Declarative Pipelines (60) | Lab 03: create the pipeline (README), fill 5 TODOs, run. **Lesson: append vs MERGE**: mt5_deals is about 99.9% inserts → append-only + tiny corrections table. In Hytech's POC this redesign cut cost from about $480/day to under $40/day (facilitator-only number). Demo: Lakeflow Designer builds the IB weekly report |
| 12:15 | Q&A (30) | Catch-up: copy files from `solutions/pipeline/transformations/`. Lab 03b for those who are done |

## 第 2 天流程 (Day 2 — run of show)

| 时间 (Time) | 环节 (Segment) | 备注 (Notes) |
|---|---|---|
| 09:30 | **M5** Lakeflow 作业（60）| **启动滴灌。** 实验 04（UI）。第一次运行会按设计在 `mt5-uk-01` 上失败 → 修复运行（清空 `fail_server`，保留 `servers`）。讲解 *Succeeded with failures*（成功但有失败）。演示：上线 `mt5-hk-01`；坏批次 → DQ false 分支；文件到达触发器；**以服务主体身份执行 `bundle deploy -t cicd`**（`docs/cicd_demo.md`，对应 Hytech "禁止直接访问生产环境"的优先事项）。追进度：`04b_Jobs_Catch_Up` |
| 10:30 | **M6a** Genie Code（30）| 实验 05 提示词阶梯。先打开技能（把团队约定写成代码，是 Ray 的优先事项）。适合现场演示：用中文输入 L1 |
| 11:00 | **M6b** 系统表（30）| 打开 *Hytech DE Workshop - Cost and Health* 仪表盘（链接由 setup 任务 `cost_dashboard` 打印），然后通过受治理的 `ops` 视图做实验 06。账单有数小时延迟，所以看第 1 天的运行。呼应 Hytech 每周的成本复盘（成本报表由 Triones 的团队负责）。预告：Genie ZeroOps（私有预览版） |
| 11:30 | **M6c** 回顾 + 认证备考（30）| 把两天内容对应到考试各部分；测验 `labs/08_Knowledge_Check.md`（答案和考试对照：`docs/knowledge_check_answers.md`） |
| 12:00 | **AI 函数**（30）| 实验 07。讲 **"2,916万"的故事**：编写这个实验时，模型把 $29,161 写成了"2,916万美元"（约 $29M）。规则：数字在 SQL 里算好，让模型原样引用，再抽查。`ai_translate` 不支持翻译成中文 → 改用 `ai_query` |
| 12:30 | 问答（30）| 路线图：Lakehouse//RT（测试版）可作为实时 POC 的服务层；填写反馈表 |

| Time | Segment | Notes |
|---|---|---|
| 09:30 | **M5** Lakeflow Jobs (60) | **Start the drip.** Lab 04 (UI). First run fails on `mt5-uk-01` by design → Repair run (clear `fail_server`, keep `servers`). Explain *Succeeded with failures*. Demos: onboard `mt5-hk-01`; bad batch → DQ false branch; file-arrival trigger; **bundle deploy `-t cicd` as a service principal** (`docs/cicd_demo.md`; Hytech's "no direct prod access" priority). Catch-up: `04b_Jobs_Catch_Up` |
| 10:30 | **M6a** Genie Code (30) | Lab 05 ladder. Open the skill first (team conventions as code, Ray's priority). Good live prompt: L1 in Chinese |
| 11:00 | **M6b** System tables (30) | Open the *Hytech DE Workshop - Cost and Health* dashboard (link printed by setup task `cost_dashboard`), then Lab 06 via governed `ops` views. Billing lags by hours, so look at Day-1 runs. Tie back to Hytech's weekly cost review (Triones' team owns cost reporting). Teaser: Genie ZeroOps (private preview) |
| 11:30 | **M6c** Recap + cert prep (30) | Map the two days to the exam sections; quiz `labs/08_Knowledge_Check.md` (answers and exam mapping: `docs/knowledge_check_answers.md`) |
| 12:00 | **AI Functions** (30) | Lab 07. Tell the **"2,916万" story**: while building this lab the model turned $29,161 into "2,916万美元" (about $29M). Rule: compute numbers in SQL, make the model quote them, spot-check. `ai_translate` has no Chinese target → use `ai_query` |
| 12:30 | Q&A (30) | Roadmap: Lakehouse//RT (beta) for the serving layer from the real-time POC; feedback form |

## 精彩时刻：提前安排 (Wow moments — stage them)

1. 一个 CDC 文件到达 → 下一次管道更新只处理这个文件；某个客户出现 SCD2 历史记录。
2. 更正表上的 `DESCRIBE HISTORY` 显示 MERGE 在重写文件，对比成交表上的纯追加。
3. 现场上线新服务器 → 下一次运行直接成功，无需改代码。
4. 坏批次 → 期望丢弃这些行 → 作业自动走告警分支。
5. Genie Code 根据中文提示词写出 gold 物化视图，并遵守团队技能。
6. 每位学员在成本仪表盘和实验 06 中看到自己第 1 天管道的成本。

**Wow moments (stage them)**

1. A CDC file lands → the next pipeline update processes only that file; SCD2 history appears for a client.
2. `DESCRIBE HISTORY` on the corrections table shows MERGE rewriting files, vs plain appends on deals.
3. New server onboarded live → green on the next run with zero code change.
4. Bad batch → expectations drop rows → the job takes the alert branch on its own.
5. Genie Code writes a gold MV from a Chinese prompt and follows the team skill.
6. Each participant sees the cost of their own Day-1 pipeline, on the cost dashboard and in Lab 06.

## 故障恢复 (Recovery playbook)

详见 `docs/troubleshooting.md`。最常见的情况：

- **TODO 语法错误** → 复制参考答案文件。
- **事件日志未发布** → `dq_gate` 失败。修改管道设置后重新运行。
- **修复运行被拒** → For each 的迭代次数变了；保持 `servers` 不变。
- **网络问题** → 找 Triones 检查 IP 允许列表，或改用热点。

**Recovery playbook**

See `docs/troubleshooting.md`. Most common:

- **TODO syntax errors** → copy the solution file.
- **Event log not published** → `dq_gate` fails. Fix the pipeline setting and re-run.
- **Repair rejected** → the for-each iteration count changed; keep `servers` the same.
- **Network** → Triones, the IP allow list, or a hotspot.

## 在 FEVM 上的验证结果 (Verified on FEVM, `fe-vm-zh-serverless-ws`, 3 Oct 2026)

| 检查 (Check) | 结果 (Result) |
|---|---|
| setup 作业 | ✅ 4 台服务器共约 78.5 万笔成交（每台 1 个 LOAD + 48 个 CDC 文件），14.1 万条 App 事件 |
| 参考答案管道 | ✅ 丢弃 1,238 笔无效成交，标记 299 笔未来日期成交；SCD2 历史正确；应用 151 条更正/删除；去重后 14 万条事件；恢复 1.2 万个救援数据值 |
| 参考答案作业 — 正常路径 | ✅ DQ 门为 true → 中文 AI 日报；For each 4/4 成功；告警任务被跳过；审计已运行 |
| For each 失败 | ✅ 运行条件告警 + 审计都已运行；运行状态 = *Succeeded with failures* |
| 上线 `mt5-hk-01` + 修复运行 | ✅（修复运行必须保持相同的迭代次数） |
| 坏批次 (60%) | ✅ 丢弃 162/3,229 (5%) → false 分支 → DQ 告警；日报被跳过 |
| 学员流程 | ✅ 实验 00 → 自己的管道（用追进度文件）→ 04b 作业 → 模拟失败 → 修复运行 → 成功 |
| 实验笔记本 | ✅ 01、02、03b、06、07 已无界面执行；`ai_mask` 遮蔽了电话和邮箱 |
| 成本仪表盘 | ✅ 由 setup 任务 `cost_dashboard` 发布；两页均正常显示；学员组只读，仅管理员可管理；统计有任务失败的运行 |
| 实验 06 作业时长 | ✅ 用时间段的起止时间计算（无服务器运行的 `run_duration_seconds` 为 0） |
| CI/CD（`cicd` 目标）| ✅ 服务主体 `hytech-ws-cicd` 通过 OAuth M2M 部署并运行：作业和管道归它所有并以它的身份运行，`users` 只读，`solutions_cicd` 中 23 张表归它所有，约 3.5 分钟成功完成，临时密钥已删除 |
| 一键安装 (`00_master_setup`) | ✅ 创建 3 个作业和 1 个管道，依次运行 setup 作业和参考答案作业（约 6 分钟，solutions 中 78.7 万笔成交和中文 AI 日报）；重复运行时原地更新，不重复创建；学员组只读 |

| Check | Result |
|---|---|
| Setup job | ✅ ~785k deals across 4 servers (1 LOAD + 48 CDC files each), 141k app events |
| Solution pipeline | ✅ 1,238 invalid trades dropped, 299 future-dated flagged; SCD2 history; 151 corrections/deletes applied; 140k de-duplicated events; 12k rescued values recovered |
| Solution job — happy path | ✅ DQ gate true → Chinese AI summary; for-each 4/4 OK; alert excluded; audit ran |
| for-each failure | ✅ Run-if alert + audit ran; run = *Succeeded with failures* |
| Onboard `mt5-hk-01` + repair | ✅ (repair must keep the same iteration count) |
| Bad batch (60%) | ✅ 162/3,229 dropped (5%) → false branch → DQ alert; summary excluded |
| Participant flow | ✅ Lab 00 → own pipeline (catch-up files) → 04b job → simulated failure → repair → green |
| Lab notebooks | ✅ 01, 02, 03b, 06, 07 executed headless; `ai_mask` masked phones/emails |
| Cost dashboard | ✅ Published by setup task `cost_dashboard`; both pages render; view-only for the group, only admins manage it; counts runs with failed tasks |
| Lab 06 job durations | ✅ Computed from the period timestamps (`run_duration_seconds` is 0 for serverless runs) |
| CI/CD (`cicd` target) | ✅ Deployed and run by service principal `hytech-ws-cicd` over OAuth M2M: job and pipeline owned by and run as it, `users` CAN VIEW, 23 tables in `solutions_cicd` owned by it, green in ~3.5 min, temporary secret deleted |
| Master setup (`00_master_setup`) | ✅ Created 3 jobs and the pipeline, ran the setup job and the solution job (~6 min; 787k deals and the Chinese AI summary in the solutions schema); a re-run updated everything in place with no duplicates; view-only for the participant group |
