# Databricks notebook source
# MAGIC %md
# MAGIC # Job task · `reconcile_server` — 按服务器对账 (per-server completeness check, runs inside **for-each**)
# MAGIC
# MAGIC For one MT5 server (`{{input}}` from the for-each task):
# MAGIC 1. the DMS landing folder must exist (fails for a server whose DMS task has not started yet), and
# MAGIC 2. every **valid** inserted deal in bronze must be in silver (expectations dropped only the invalid ones).
# MAGIC
# MAGIC Results are appended to `ops_reconciliation`. Lab helper: job parameter `fail_server` makes one iteration fail
# MAGIC on purpose so you can practise **Repair run**.

# COMMAND ----------

dbutils.widgets.text("catalog", "hytech_de_workshop")
dbutils.widgets.text("schema", "")
dbutils.widgets.text("server_id", "mt5-sg-01")
dbutils.widgets.text("fail_server", "", "Lab: make this server fail on purpose")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
server = dbutils.widgets.get("server_id").strip()
cs = f"{catalog}.{schema}"
landing = f"/Volumes/{catalog}/raw/landing/mt5/{server}/mt5_deals"

# COMMAND ----------

if server == dbutils.widgets.get("fail_server").strip():
    raise RuntimeError(f"[{server}] simulated failure (job parameter fail_server={server}) — clear it and use Repair run")

try:
    files = [f for f in dbutils.fs.ls(landing) if f.name.endswith(".parquet")]
except Exception:  # noqa: BLE001 - folder does not exist yet
    files = []
if not files:
    raise RuntimeError(f"[{server}] no DMS files in {landing} — has the DMS task for this server started?")

counts = spark.sql(f"""
  SELECT
    (SELECT count(*) FROM {cs}.bronze_mt5_deals
      WHERE server_id = '{server}' AND Op = 'I' AND Login IS NOT NULL
        AND (Action = 2 OR (Volume > 0 AND nullif(Symbol, '') IS NOT NULL AND Price > 0))) AS bronze_valid_inserts,
    (SELECT count(*) FROM {cs}.silver_mt5_deals WHERE server_id = '{server}')            AS silver_rows
""").first()
bronze_valid, silver = counts["bronze_valid_inserts"], counts["silver_rows"]
status = "OK" if bronze_valid == silver else "MISMATCH"
if bronze_valid == 0:
    print(f"[{server}] note: {len(files)} landing files but nothing ingested yet — new server? "
          "The next pipeline update picks it up automatically (the bronze path glob is mt5/*/<table>/).")
print(f"[{server}] landing_files={len(files)} bronze_valid_inserts={bronze_valid:,} silver_rows={silver:,} -> {status}")

spark.sql(f"""
  CREATE TABLE IF NOT EXISTS {cs}.ops_reconciliation (
    checked_at TIMESTAMP, server_id STRING, landing_files INT, bronze_valid_inserts BIGINT, silver_rows BIGINT, status STRING)
""")
spark.sql(f"""INSERT INTO {cs}.ops_reconciliation VALUES
  (current_timestamp(), '{server}', {len(files)}, {bronze_valid}, {silver}, '{status}')""")

if status != "OK":
    raise RuntimeError(f"[{server}] silver is missing {bronze_valid - silver:,} valid deals")
