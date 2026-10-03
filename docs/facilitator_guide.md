# Facilitator guide — Hytech DE workshop (Zhi Han & Germaine)

One instructor presents while the other floats; swap per module. With 20 newcomers the floater is the
difference between "most finished" and "most stuck". Split proposal in `docs/workshop_plan.md` §4.

## Before the day

- [ ] Triones has completed `docs/setup_guide_triones.md`, including the **connectivity test from the venue**
- [ ] Solution job ran once → `hytech_de_workshop.solutions` is populated (lab 07 and catch-up depend on it)
- [ ] `llm_endpoint` set to a model served in Hytech's region (test `ai_query` in the SQL editor)
- [ ] Genie Code skill visible at `/Workspace/.assistant/skills/hytech-de-conventions/`
- [ ] Cost dashboard *Hytech DE Workshop - Cost and Health* published (setup task `cost_dashboard`)
- [ ] CI/CD demo: service principal `hytech-ws-cicd`, its grants and a green `[cicd]` run (done on FEVM, 3 Oct). On the day, `cicd/deploy_as_service_principal.sh` creates and deletes its own temporary secret (`docs/cicd_demo.md`)
- [ ] Slides as **PDF/PPTX on the loaner laptop** (Google Workspace is blocked in mainland China without VPN)
- [ ] Dry run on Mon 12 Oct evening, ideally with one Hytech participant account

## Instructor controls (job `hytech_ws_drip_producer`)

| When | Parameters | Effect |
|---|---|---|
| Start of M3 (Day 1, ~10:30) | `duration_minutes=150`, `interval_seconds=30` | New CDC files keep arriving through M3–M4 |
| Start of Day 2 (~09:30) | `duration_minutes=150` | Live data for the Jobs lab and file-arrival triggers |
| M5 demo, after everyone's first run | `new_server=mt5-hk-01`, `duration_minutes=10` | **Onboard a new MT5 server** (full load + CDC). The next pipeline run ingests it with no code change |
| M5 demo | `bad_batch_pct=60`, `duration_minutes=2` | Bad batch → the DQ gate takes the **false** branch on the next job run |

Only one drip run at a time (`max_concurrent_runs: 1`). Cancel the run to stop it early.

## Day 1 — run of show

| Time | Segment | Notes |
|---|---|---|
| 09:30 | **M1** Platform overview (30) | Lakehouse, UC, serverless, Lakeflow, Genie. Show Hytech's architecture (MySQL → DMS → S3 → Auto Loader → SDP → Power BI/Genie) next to `docs/workshop_plan.md` §2. **Lab 00** last 10 min: everyone creates their schema and copies the labs |
| 10:00 | **M2** Unity Catalog (30) | Lab 01. Talk track: tags + masks are the UC-native version of Robin's column-tag check framework; governed tags enforce allowed values. Demo: Catalog Explorer lineage, access requests |
| 10:30 | **M3** Ingestion (45) | **Start the drip producer.** Lab 02. Re-run the Auto Loader cell after a minute and point out the new files only. Demo: Lakeflow Connect NetSuite (GA) and MySQL CDC (preview) as the DMS-free path |
| 11:15 | **M4** Declarative Pipelines (60) | Lab 03: create the pipeline (README), fill 5 TODOs, run. **Lesson: append vs MERGE**: mt5_deals is about 99.9% inserts → append-only + tiny corrections table. In Hytech's POC this redesign cut cost from about $480/day to under $40/day (facilitator-only number). Demo: Lakeflow Designer builds the IB weekly report |
| 12:15 | Q&A (30) | Catch-up: copy files from `solutions/pipeline/transformations/`. Lab 03b for those who are done |

## Day 2 — run of show

| Time | Segment | Notes |
|---|---|---|
| 09:30 | **M5** Lakeflow Jobs (60) | **Start the drip.** Lab 04 (UI). First run fails on `mt5-uk-01` by design → Repair run (clear `fail_server`, keep `servers`). Explain *Succeeded with failures*. Demos: onboard `mt5-hk-01`; bad batch → DQ false branch; file-arrival trigger; **bundle deploy `-t cicd` as a service principal** (`docs/cicd_demo.md`; Hytech's "no direct prod access" priority). Catch-up: `04b_Jobs_Catch_Up` |
| 10:30 | **M6a** Genie Code (30) | Lab 05 ladder. Open the skill first (team conventions as code, Ray's priority). Good live prompt: L1 in Chinese |
| 11:00 | **M6b** System tables (30) | Open the *Hytech DE Workshop - Cost and Health* dashboard (link printed by setup task `cost_dashboard`), then Lab 06 via governed `ops` views. Billing lags by hours, so look at Day-1 runs. Tie back to Hytech's weekly cost review (Triones' team owns cost reporting). Teaser: Genie ZeroOps (private preview) |
| 11:30 | **M6c** Recap + cert prep (30) | Map the two days to the exam sections; quiz `labs/08_Knowledge_Check.md` (answers and exam mapping: `docs/knowledge_check_answers.md`) |
| 12:00 | **AI Functions** (30) | Lab 07. Tell the **"2,916万" story**: while building this lab the model turned $29,161 into "2,916万美元" (about $29M). Rule: compute numbers in SQL, make the model quote them, spot-check. `ai_translate` has no Chinese target → use `ai_query` |
| 12:30 | Q&A (30) | Roadmap: Lakehouse//RT (beta) for the serving layer from the real-time POC; feedback form |

## Wow moments (stage them)

1. A CDC file lands → the next pipeline update processes only that file; SCD2 history appears for a client.
2. `DESCRIBE HISTORY` on the corrections table shows MERGE rewriting files, vs plain appends on deals.
3. New server onboarded live → green on the next run with zero code change.
4. Bad batch → expectations drop rows → the job takes the alert branch on its own.
5. Genie Code writes a gold MV from a Chinese prompt and follows the team skill.
6. Each participant sees the cost of their own Day-1 pipeline, on the cost dashboard and in Lab 06.

## Recovery playbook

See `docs/troubleshooting.md`. Most common:

- **TODO syntax errors** → copy the solution file.
- **Event log not published** → `dq_gate` fails. Fix the pipeline setting and re-run.
- **Repair rejected** → the for-each iteration count changed; keep `servers` the same.
- **Network** → Triones, the IP allow list, or a hotspot.

## Verified on FEVM (`fe-vm-zh-serverless-ws`, 3 Oct 2026)

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
