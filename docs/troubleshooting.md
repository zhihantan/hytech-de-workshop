# Troubleshooting · 常见问题

| Symptom | Cause | Fix |
|---|---|---|
| `PRINCIPAL_DOES_NOT_EXIST: de_workshop_sz` on GRANT | The group is workspace-local or missing. Unity Catalog needs an **account-level** group | Create the group at account level (IdP/SCIM). In a test workspace, grant to `account users` instead |
| `UC_TAG_POLICY_VALUE_NOT_ALLOWED` when setting a tag | The tag key is a **governed tag** with a list of allowed values (account-level tag policy) | Use an allowed value or a different key. Good discussion point: this is how a company-wide tag standard is enforced |
| Lab 00: cannot create schema | Participant lacks `CREATE SCHEMA` on the catalog | Re-run `setup/04_participant_schemas` with their email, or grant `CREATE SCHEMA` to the group |
| Pipeline: `____` / syntax error | TODO not filled in | Fill the TODO, or copy the file from `solutions/pipeline/transformations/` (catch-up) |
| Pipeline: `landing_root` not found | Configuration keys missing | Pipeline settings → Configuration: `landing_root`, `ref_root` (see `labs/03_pipeline/README.md`) |
| `dq_gate`: "No pipeline updates found in …pipeline_event_log" | Event log not published | Pipeline settings → Advanced → Publish event log → `pipeline_event_log` in your schema; run the pipeline again |
| Repair fails: "Inputs of a For each task repair must resolve to the same total iterations" | The repair resolved `servers` to a different list than the original run | Repair with the **same** `servers` value as the original run (only change `fail_server`) |
| Repair API: "latest repair ID needs to be provided" | A previous repair exists | UI handles this; with the API pass `latest_repair_id` |
| Run shows **Succeeded with failures** | A middle task failed but the leaf tasks (Run-if alert/audit) succeeded | Expected. Inspect the failed task; consider which tasks should decide the run status |
| `ai_query` error: endpoint not found / not available in region | FMAPI model not served in this region | Use an available endpoint (`llm_endpoint` job parameter); enable cross-geography processing |
| AI commentary has wrong numbers (e.g. 29,161 → "2,916万") | LLMs are unreliable at arithmetic and unit conversion | Pre-compute numbers in SQL; tell the model to quote numbers as-is; spot-check |
| `ai_translate` does not translate to Chinese | Chinese is not a supported target language | Use `ai_query` with a translation prompt |
| `_rescued_data` is always NULL | Schema was inferred (it widened types) instead of using the contract schema | Use the explicit schema + `rescuedDataColumn` as in lab 02 / `02_bronze_app_events.sql` |
| No new rows after re-running Auto Loader | No new files arrived | Ask the instructor to start the drip producer |
| System-table queries return nothing for today | Billing data lags by hours | Look at yesterday / Day 1; job and pipeline timelines arrive sooner |
| Gold shows future dates | `deal_time_not_in_future` is warn-only | Intended discussion point: decide drop vs warn vs fail |
| Workspace unreachable from the venue | IP access list / network | Use the admin-approved network; Triones checks the IP allow list |
| Google Docs / Slides do not open | Blocked in mainland China without VPN | Use the PDF copies on the instructor laptop; labs are inside the workspace |

## Reset a participant

```sql
DROP SCHEMA hytech_de_workshop.u_<name> CASCADE;   -- then re-run labs/00_Start_Here
```

Delete their pipeline and job in the UI first (or the pipeline keeps the old checkpoints).

## Regenerate the data (instructors only, before the workshop)

Run job `hytech_ws_setup` with `reset=true`. This wipes and recreates the landing zone, so every pipeline must
then be **fully refreshed**.
