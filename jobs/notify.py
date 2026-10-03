# Databricks notebook source
# MAGIC %md
# MAGIC # Job task · `notify` — 告警 (alert)
# MAGIC
# MAGIC Used twice in the job: on the DQ gate's `false` branch, and with **Run if = At least one failed**.
# MAGIC Appends to `ops_alerts`. If `webhook_url` is set (e.g. a Lark/Feishu custom-bot webhook) it also posts
# MAGIC a text message — Lakeflow Jobs also has built-in email/Slack/Teams/webhook notifications.

# COMMAND ----------

dbutils.widgets.text("catalog", "hytech_de_workshop")
dbutils.widgets.text("schema", "")
dbutils.widgets.text("reason", "job_task_failed")
dbutils.widgets.text("job_id", "")
dbutils.widgets.text("run_id", "")
dbutils.widgets.text("webhook_url", "")
dbutils.widgets.text("detail", "")

catalog, schema = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
reason, job_id, run_id = dbutils.widgets.get("reason"), dbutils.widgets.get("job_id"), dbutils.widgets.get("run_id")
cs = f"{catalog}.{schema}"

# COMMAND ----------

# `detail` is filled by a dynamic value reference in the job, e.g. "{{tasks.dq_gate.values.dq_drop_pct}}"
detail = dbutils.widgets.get("detail")
message = f"[Hytech trade lakehouse] {reason} · job {job_id} run {run_id} · schema {cs} {detail}".strip()
print(message)

spark.sql(f"""
  CREATE TABLE IF NOT EXISTS {cs}.ops_alerts (
    alert_at TIMESTAMP, reason STRING, job_id STRING, run_id STRING, message STRING)
""")
spark.sql(f"INSERT INTO {cs}.ops_alerts VALUES (current_timestamp(), :r, :j, :ru, :m)",
          args={"r": reason, "j": job_id, "ru": run_id, "m": message})

webhook = dbutils.widgets.get("webhook_url").strip()
if webhook:
    import requests

    resp = requests.post(webhook, json={"msg_type": "text", "content": {"text": message}}, timeout=10)
    print("webhook:", resp.status_code, resp.text[:200])
