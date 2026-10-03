# Databricks notebook source
# MAGIC %md
# MAGIC # Job task · `dq_gate` — 数据质量闸门 (data-quality gate)
# MAGIC
# MAGIC Reads the pipeline **event log** for the latest update, computes how many `silver_mt5_deals` rows the
# MAGIC expectations dropped, stores per-expectation results in `ops_dq_results`, and publishes **task values**
# MAGIC for the downstream `if/else` condition task:
# MAGIC
# MAGIC * `{{tasks.dq_gate.values.dq_drop_pct}}` — % of deal rows dropped in this update
# MAGIC * `{{tasks.dq_gate.values.dq_dropped_rows}}`

# COMMAND ----------

dbutils.widgets.text("catalog", "hytech_de_workshop")
dbutils.widgets.text("schema", "")
dbutils.widgets.text("event_log_table", "pipeline_event_log")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
cs = f"{catalog}.{schema}"
ev = f"{cs}.{dbutils.widgets.get('event_log_table')}"

# COMMAND ----------

latest = spark.sql(f"""
  SELECT origin.update_id AS update_id, timestamp
  FROM {ev}
  WHERE event_type = 'create_update'
  ORDER BY timestamp DESC
  LIMIT 1
""").first()
if latest is None:
    raise ValueError(f"No pipeline updates found in {ev}. Did you publish the event log to this table?")
update_id = latest["update_id"]

flows = spark.sql(f"""
  SELECT origin.flow_name                                                   AS flow_name,
         sum(CAST(details:flow_progress.metrics.num_output_rows AS BIGINT))   AS output_rows,
         sum(CAST(details:flow_progress.data_quality.dropped_records AS BIGINT)) AS dropped_rows
  FROM {ev}
  WHERE event_type = 'flow_progress' AND origin.update_id = '{update_id}'
  GROUP BY ALL
""")
display(flows)

deals = flows.where("flow_name LIKE '%silver_mt5_deals'").first()
output_rows = int((deals and deals["output_rows"]) or 0)
dropped = int((deals and deals["dropped_rows"]) or 0)
drop_pct = round(100.0 * dropped / (output_rows + dropped), 4) if (output_rows + dropped) else 0.0
print(f"update {update_id}: silver_mt5_deals output={output_rows:,} dropped={dropped:,} -> {drop_pct}%")

# COMMAND ----------

expectations = spark.sql(f"""
  SELECT current_timestamp() AS checked_at, '{update_id}' AS update_id,
         e.dataset, e.name AS expectation,
         sum(e.passed_records) AS passed_records, sum(e.failed_records) AS failed_records
  FROM (
    SELECT explode(from_json(details:flow_progress.data_quality.expectations,
                   'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) AS e
    FROM {ev}
    WHERE event_type = 'flow_progress' AND origin.update_id = '{update_id}'
      AND details:flow_progress.data_quality.expectations IS NOT NULL
  )
  GROUP BY ALL
""")
expectations.write.mode("append").option("mergeSchema", "true").saveAsTable(f"{cs}.ops_dq_results")
display(expectations)

dbutils.jobs.taskValues.set(key="dq_update_id", value=update_id)
dbutils.jobs.taskValues.set(key="dq_dropped_rows", value=dropped)
dbutils.jobs.taskValues.set(key="dq_drop_pct", value=drop_pct)
