# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · 实时数据滴灌 (Drip producer) — instructor only
# MAGIC
# MAGIC Keeps the landing zone "live" during labs: every `interval_seconds` it writes one DMS-style CDC file per
# MAGIC MT5 table per server (new trades, closes, position marks, deposits/withdrawals, client updates) and one
# MAGIC app-events JSON file.
# MAGIC
# MAGIC | Parameter | Use in class |
# MAGIC |---|---|
# MAGIC | `duration_minutes` / `interval_seconds` | Run during M3–M5 (e.g. 60 min, every 30 s) |
# MAGIC | `new_server=mt5-hk-01` | **M5 repair demo**: onboard a new MT5 server (DMS full load, then CDC) |
# MAGIC | `bad_batch_pct=30` | **M5 DQ-gate demo**: 30% of new trade deals are invalid → expectations drop them → job takes the `false` branch |

# COMMAND ----------

dbutils.widgets.text("catalog", "hytech_de_workshop")
dbutils.widgets.text("duration_minutes", "60")
dbutils.widgets.text("interval_seconds", "30")
dbutils.widgets.text("servers", "")
dbutils.widgets.text("new_server", "")
dbutils.widgets.text("bad_batch_pct", "0")
dbutils.widgets.text("deals_per_tick", "24")

# COMMAND ----------

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), "..", "src")))

from hytech_workshop.config import WorkshopConfig  # noqa: E402
from hytech_workshop.drip import run_drip  # noqa: E402

cfg = WorkshopConfig(catalog=dbutils.widgets.get("catalog"))
servers = [s.strip() for s in dbutils.widgets.get("servers").split(",") if s.strip()] or None
result = run_drip(
    cfg,
    duration_minutes=float(dbutils.widgets.get("duration_minutes")),
    interval_seconds=float(dbutils.widgets.get("interval_seconds")),
    servers=servers,
    new_server=dbutils.widgets.get("new_server").strip() or None,
    bad_batch_pct=float(dbutils.widgets.get("bad_batch_pct")) / 100.0,
    deals_per_tick=int(dbutils.widgets.get("deals_per_tick")),
    log=print,
)
print(result)
