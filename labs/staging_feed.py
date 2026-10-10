# Databricks notebook source
# MAGIC %md
# MAGIC # staging_feed · 预发布通道辅助函数 (staging-lane helpers)
# MAGIC
# MAGIC 实验 03c 和 04c 用 `%run ./staging_feed` 加载本笔记本。它为新服务器 `mt5-hk-01` 在**你自己 schema** 的 volume 中写入 DMS 风格的 CDC 文件，并提供连接、运行和修改你自己管道的函数。不需要讲师：所有数据都在你自己的 schema 里。
# MAGIC
# MAGIC Labs 03c and 04c load this notebook with `%run ./staging_feed`. It writes DMS-style CDC files for the new server `mt5-hk-01` into a volume in **your own schema**, and has functions to wire up, run and change your own pipeline. No instructor needed: all the data lives in your own schema.

# COMMAND ----------

import os
import re
import shutil
import tempfile
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

STAGING_SERVER = "mt5-hk-01"
STAGING_DEAL_BASE = 1_500_000_000      # 与 SERVER_META["mt5-hk-01"] 相同 (same as SERVER_META["mt5-hk-01"])
STAGING_POSITION_BASE = 2_500_000_000
STAGING_LOGIN_BASE = 85_000_000
BATCH_ROWS = 200
SCENARIOS = ("clean", "junk", "bad_prices")
STAGING_FILE = "06_staging_mt5_hk01.sql"
STAGING_TABLES = ("bronze_staging_mt5_deals", "silver_staging_mt5_deals", "silver_staging_mt5_deals_quarantine",
                  "gold_staging_daily_volume")
DMS_COLUMNS = [
    "Op", "cdc_ts", "Deal", "Login", "Order", "Time", "TimeMsc", "Symbol", "Action", "Entry", "Reason", "Volume",
    "Price", "ContractSize", "RateProfit", "Profit", "Storage", "Commission", "Fee", "PositionID", "Dealer", "Comment",
]
# 模板 = 你自己 bronze 中 mt5-sg-01 最近的有效成交 (template = recent valid mt5-sg-01 deals in your own bronze)
TEMPLATE_SQL = """
SELECT {cols} FROM {cs}.bronze_mt5_deals
WHERE server_id = 'mt5-sg-01' AND Op = 'I' AND Login IS NOT NULL AND `Time` <= current_timestamp()
  AND (Action = 2 OR (Volume > 0 AND nullif(Symbol, '') IS NOT NULL AND Price > 0))
ORDER BY cdc_ts DESC
LIMIT {n}
"""


def my_names(user_name: str) -> dict:
    """由邮箱得出你的 schema、管道、作业和实验文件夹（与实验 00 和 04b 的规则相同）。
    Your schema, pipeline, job and lab folder from your email (the same rule as labs 00 and 04b)."""
    name = "".join(ch if ch.isalnum() else "_" for ch in user_name.split("@")[0].lower()).strip("_")
    return {
        "name": name,
        "schema": f"u_{name}",
        "pipeline": f"trade_lakehouse_{name}",
        "job": f"daily_trading_reporting_{name}",
        "lab_root": f"/Users/{user_name}/hytech_de_lab",
    }


def staging_root(catalog: str, schema: str) -> str:
    """你的预发布 volume，也就是管道配置 staging_root 的值。
    Your staging volume: the value of the pipeline setting staging_root."""
    return f"/Volumes/{catalog}/{schema}/staging"


def staging_dir(catalog: str, schema: str) -> str:
    """DMS 为 mt5-hk-01 写入成交文件的文件夹 (the folder DMS writes mt5-hk-01 deal files to)."""
    return f"{staging_root(catalog, schema)}/mt5/{STAGING_SERVER}/mt5_deals"


def dms_file_name(ts: datetime) -> str:
    """AWS DMS 的 CDC 文件名：yyyymmdd-hhmmssfff.parquet (AWS DMS CDC file name)."""
    return ts.strftime("%Y%m%d-%H%M%S") + f"{ts.microsecond // 1000:03d}.parquet"


def make_batch(template: pd.DataFrame, scenario: str, batch_key: int, now: datetime) -> pd.DataFrame:
    """把模板成交改写成 mt5-hk-01 的一个 CDC 批次，再按场景注入问题行。
    Re-key the template deals as one mt5-hk-01 CDC batch, then inject the scenario's problem rows.

    * clean      — 没有问题行 (no problem rows)
    * junk       — 3 笔 Volume = 0 和 2 笔缺少品种 → DROP；1 笔未来日期 → WARN
                   (3 zero-volume and 2 symbol-less trades → DROP; 1 future-dated trade → WARN)
    * bad_prices — 5 笔负价格 → FAIL (5 negative-price trades → FAIL)
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"scenario must be one of {SCENARIOS}, got {scenario!r}")
    df = template[DMS_COLUMNS].head(BATCH_ROWS).copy().reset_index(drop=True)
    trades = df.index[df["Action"] != 2]
    if len(trades) < 6:
        raise ValueError("the template needs at least 6 trades (Action 0 or 1)")
    now = pd.Timestamp(now)
    now = now.tz_convert("UTC") if now.tzinfo else now.tz_localize("UTC")
    seq = np.arange(len(df), dtype=np.int64)
    key = int(batch_key) * BATCH_ROWS
    df["Op"] = "I"
    df["Deal"] = STAGING_DEAL_BASE + key + seq
    df["Order"] = np.where(df["Action"] == 2, 0, df["Deal"] + 100_000_000).astype(np.int64)
    df["Login"] = STAGING_LOGIN_BASE + df["Login"].astype(np.int64) % 1000
    df["PositionID"] = np.where(df["PositionID"].fillna(0).astype(np.int64) > 0, STAGING_POSITION_BASE + key + seq, 0)
    # 成交时间分布在过去几分钟内，DMS 在两秒后提交 (deals spread over the last few minutes; DMS commits 2 s later)
    df["Time"] = now - pd.to_timedelta((len(df) - seq) * 2, unit="s")
    df["cdc_ts"] = df["Time"] + pd.Timedelta(seconds=2)
    if scenario == "junk":
        df.loc[trades[0:3], "Volume"] = 0
        df.loc[trades[3:5], "Symbol"] = None
        df.loc[trades[5], "Time"] = now + pd.Timedelta(days=3)
    elif scenario == "bad_prices":
        df.loc[trades[0:5], "Price"] = -df.loc[trades[0:5], "Price"].abs()
    df["TimeMsc"] = (df["Time"] - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(milliseconds=1)
    return df
