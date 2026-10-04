# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · 实时数据滴灌 (Drip producer) — instructor only
# MAGIC
# MAGIC 在实验期间保持数据接入区"活跃"：每 `interval_seconds`，为每个 MT5 服务器的每个表写入一个 DMS 风格的变更数据 (CDC) 文件（新成交、平仓、头寸标记、入金/出金、客户更新）和一个应用事件 JSON 文件。
# MAGIC
# MAGIC Keeps the landing zone "live" during labs: every `interval_seconds` it writes one DMS-style CDC file per
# MAGIC MT5 table per server (new trades, closes, position marks, deposits/withdrawals, client updates) and one
# MAGIC app-events JSON file.
# MAGIC
# MAGIC | 参数 (Parameter) | 在课堂中的使用 (Use in class) |
# MAGIC |---|---|
# MAGIC | `duration_minutes` / `interval_seconds` | 在 M3–M5 期间运行（例如 60 分钟，每 30 秒） |
# MAGIC | `new_server=mt5-hk-01` | **M5 修复演示**：载入新的 MT5 服务器（DMS 全量，然后 CDC） |
# MAGIC | `bad_batch_pct=30` | **M5 数据质量闸门演示**：30% 的新成交交易无效 → 期望将其删除 → 作业采用 `false` 分支 |

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
