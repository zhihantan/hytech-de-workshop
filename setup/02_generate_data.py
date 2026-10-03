# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · 生成模拟数据 (Generate the synthetic landing zone)
# MAGIC
# MAGIC Writes **synthetic** (fake) data only — no real client data:
# MAGIC * `landing/mt5/<server>/<table>/` — AWS DMS layout: `LOAD00000001.parquet` (full load) + hourly CDC files
# MAGIC   `yyyymmdd-hhmmssfff.parquet` with `Op` (I/U/D) and `cdc_ts`, for `mt5_users`, `mt5_deals`, `mt5_positions`
# MAGIC * `landing/app_events/<date>/events-*.json` — Sensors-style JSON with schema drift and ~1% duplicates
# MAGIC * `ref/{symbols,ib_hierarchy,servers,fx_rates}/*.csv`
# MAGIC * `producer/` — state for the drip producer (`03_drip_producer`)
# MAGIC
# MAGIC ⚠️ If the landing zone already has data, nothing happens unless `reset=true`, which deletes it first.
# MAGIC Only reset **before** participants start their pipelines (their streaming checkpoints point at these files).

# COMMAND ----------

dbutils.widgets.text("catalog", "hytech_de_workshop")
dbutils.widgets.dropdown("scale", "full", ["full", "demo"])
dbutils.widgets.dropdown("reset", "false", ["true", "false"])

catalog = dbutils.widgets.get("catalog")
scale = dbutils.widgets.get("scale")
reset = dbutils.widgets.get("reset") == "true"

# COMMAND ----------

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), "..", "src")))

from hytech_workshop.config import WorkshopConfig  # noqa: E402
from hytech_workshop.history import build_all  # noqa: E402

if scale == "full":
    cfg = WorkshopConfig(catalog=catalog)
else:  # quick dry-run size
    cfg = WorkshopConfig(catalog=catalog, users_per_server=400, positions_per_server_per_day=300,
                         history_days=30, events_per_day=5000, event_days=3)
print(cfg)

# COMMAND ----------

existing = [f for f in dbutils.fs.ls(cfg.landing_root)]
if existing and not reset:
    dbutils.notebook.exit(
        f"Landing zone already populated ({len(existing)} entries) — nothing generated. "
        "Set reset=true to wipe and regenerate (only BEFORE participants start their pipelines)."
    )
if reset:
    for root in (cfg.landing_root, cfg.ref_root, cfg.producer_root):
        for item in dbutils.fs.ls(root):
            dbutils.fs.rm(item.path, True)
            print("deleted", item.path)

manifest = build_all(cfg, log=print)
with open(f"{cfg.producer_root}/manifest.json", "w") as fh:
    json.dump(manifest, fh, indent=2, default=str)

# COMMAND ----------

# MAGIC %md ### 校验 (Verify): files and rows per server and table

# COMMAND ----------

rows = []
for server, info in manifest["servers"].items():
    for table, st in info["stats"].items():
        rows.append((server, table, st["load_files"], st["load_rows"], st["cdc_files"], st["cdc_rows"]))
summary = spark.createDataFrame(rows, "server string, table string, load_files int, load_rows long, cdc_files int, cdc_rows long")
display(summary.orderBy("table", "server"))

check = spark.read.parquet(f"{cfg.landing_root}/mt5/*/mt5_deals/").groupBy("Op").count()
display(check)
print("app events:", manifest["app_events"], "| seconds:", manifest["seconds"])
