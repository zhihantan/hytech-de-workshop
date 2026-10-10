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

# COMMAND ----------

def switch_rule(sql_text: str, rule: str, action: str) -> str:
    """把一条期望规则的 ON VIOLATION 动作改为 FAIL 或 DROP（只改这一行）。
    Switch one expectation's ON VIOLATION action to FAIL or DROP (only that line changes)."""
    clause = {"FAIL": "ON VIOLATION FAIL UPDATE", "DROP": "ON VIOLATION DROP ROW"}[action]
    lines, hit = sql_text.splitlines(keepends=True), False
    for i, line in enumerate(lines):
        if re.search(rf"CONSTRAINT\s+{rule}\b", line) and "ON VIOLATION" in line:
            lines[i], hit = re.sub(r"ON VIOLATION (FAIL UPDATE|DROP ROW)", clause, line), True
    if not hit:
        raise ValueError(f"rule {rule} with an ON VIOLATION clause not found")
    return "".join(lines)


def ws_path(p: str) -> str:
    """工作区 API 使用不带 /Workspace 前缀的路径 (the Workspace API takes paths without the /Workspace prefix)."""
    return p[len("/Workspace"):] if p.startswith("/Workspace/") else p


def find_pipeline_id(w, pipeline_name: str) -> str:
    """按名称找到你的管道 (find your pipeline by name)."""
    found = [p for p in w.pipelines.list_pipelines(filter=f"name LIKE '{pipeline_name}'") if p.name == pipeline_name]
    if not found:
        raise ValueError(f"Pipeline '{pipeline_name}' not found: create it in lab 03 first")
    return found[0].pipeline_id


def transformations_dir(w, pipeline_id: str, lab_root: str) -> str:
    """你的管道读取的 transformations 文件夹 (the transformations folder your pipeline reads)."""
    spec = w.api_client.do("GET", f"/api/2.0/pipelines/{pipeline_id}")["spec"]
    for lib in spec.get("libraries") or []:
        include = (lib.get("glob") or {}).get("include", "")
        folder = (include[:-3] if include.endswith("/**") else include).rstrip("/")
        if folder.endswith("/transformations"):
            return ws_path(folder)
    return f"{lab_root}/03_pipeline/transformations"


def wire_staging_lane(w, catalog: str, user_name: str, no_retries: bool = False) -> str:
    """代你完成 03c 第 2 步：添加管道配置 staging_root，并把 06_staging_mt5_hk01.sql 放进 transformations。
    no_retries=True 时还关闭自动重试（通过 API 启动的更新默认会重试，04c 会讲）。
    Does lab 03c step 2 for you: adds the pipeline setting staging_root and puts 06_staging_mt5_hk01.sql in
    transformations. With no_retries=True it also turns off automatic retries (API-started updates retry by
    default; lab 04c explains)."""
    from databricks.sdk.service.workspace import ImportFormat

    n = my_names(user_name)
    pipeline_id = find_pipeline_id(w, n["pipeline"])
    spec = w.api_client.do("GET", f"/api/2.0/pipelines/{pipeline_id}")["spec"]
    conf = dict(spec.get("configuration") or {})
    wanted = {"staging_root": staging_root(catalog, n["schema"])}
    if no_retries:
        wanted.update({"pipelines.numUpdateRetryAttempts": "0", "pipelines.maxFlowRetryAttempts": "0"})
    if any(conf.get(k) != v for k, v in wanted.items()):
        conf.update(wanted)
        w.api_client.do("PUT", f"/api/2.0/pipelines/{pipeline_id}",
                        body={**spec, "configuration": conf, "id": pipeline_id})
        print("✅ pipeline settings:", wanted)
    target = f"{transformations_dir(w, pipeline_id, n['lab_root'])}/{STAGING_FILE}"
    try:
        w.workspace.get_status(target)
        print("✅ already in your pipeline:", target)
    except Exception:  # noqa: BLE001 - not there yet: copy it from 03_pipeline/staging
        source = f"{n['lab_root']}/03_pipeline/staging/{STAGING_FILE}"
        w.workspace.upload(target, w.workspace.download(source).read(), format=ImportFormat.AUTO)
        print("✅ copied", source, "->", target)
    return pipeline_id


def run_pipeline(w, pipeline_id: str, full_refresh_selection=None, timeout_minutes: int = 30) -> str:
    """启动一次管道更新并等待结束，返回 COMPLETED / FAILED / CANCELED。
    Start a pipeline update, wait for it, and return COMPLETED / FAILED / CANCELED."""
    body = {"full_refresh_selection": list(full_refresh_selection)} if full_refresh_selection else {}
    try:
        update_id = w.api_client.do("POST", f"/api/2.0/pipelines/{pipeline_id}/updates", body=body)["update_id"]
    except Exception as e:  # noqa: BLE001 - usually an update is already running
        raise RuntimeError(f"could not start an update ({str(e).splitlines()[0][:160]}): "
                           "wait for the running update to finish, then run this cell again") from e
    deadline = time.time() + timeout_minutes * 60
    while True:
        state = w.api_client.do("GET", f"/api/2.0/pipelines/{pipeline_id}/updates/{update_id}")["update"]["state"]
        if state in ("COMPLETED", "FAILED", "CANCELED"):
            print(f"pipeline update {update_id}: {state}")
            return state
        if time.time() > deadline:
            raise TimeoutError(f"update {update_id} is still {state} after {timeout_minutes} min")
        time.sleep(15)


def set_price_rule(w, user_name: str, action: str) -> None:
    """代你修改预发布 silver 的 valid_trade_price：FAIL（停止更新）或 DROP（丢弃并隔离）。
    Edits the staging silver rule valid_trade_price for you: FAIL (stop the update) or DROP (drop + quarantine)."""
    from databricks.sdk.service.workspace import ImportFormat

    n = my_names(user_name)
    path = f"{transformations_dir(w, find_pipeline_id(w, n['pipeline']), n['lab_root'])}/{STAGING_FILE}"
    text = w.workspace.download(path).read().decode("utf-8")
    new = switch_rule(text, "valid_trade_price", action)
    if new != text:
        w.workspace.upload(path, new.encode("utf-8"), format=ImportFormat.AUTO, overwrite=True)
    print(f"✅ valid_trade_price -> {action} ({path})")


def write_batch(spark, catalog: str, schema: str, scenario: str) -> str:
    """生成一个批次文件，写入你的预发布 volume，并返回文件路径。
    Build one batch file, write it into your staging volume and return its path."""
    cols = ", ".join(f"`{c}`" for c in DMS_COLUMNS)
    template = spark.sql(TEMPLATE_SQL.format(cols=cols, cs=f"{catalog}.{schema}", n=BATCH_ROWS)).toPandas()
    if len(template) < 20:
        raise RuntimeError(f"{catalog}.{schema}.bronze_mt5_deals has too few mt5-sg-01 deals: run your lab 03 pipeline first")
    now = datetime.now(timezone.utc)
    df = make_batch(template, scenario, batch_key=int(now.timestamp() * 1000) % 1_000_000_000, now=now)
    target = staging_dir(catalog, schema)
    os.makedirs(target, exist_ok=True)
    path = f"{target}/{dms_file_name(now)}"
    with tempfile.TemporaryDirectory() as tmp:
        local = os.path.join(tmp, "batch.parquet")
        # 先写到本地再复制：volume 上只会出现完整的文件 (write locally, then copy: the volume only ever sees whole files)
        pq.write_table(pa.Table.from_pandas(df, preserve_index=False), local,
                       compression="snappy", coerce_timestamps="us", allow_truncated_timestamps=True)
        shutil.copyfile(local, path)
    print(f"✅ {scenario}: {len(df)} rows -> {path}")
    return path


def batch_counts(spark, cs: str, path: str) -> dict:
    """一个批次文件的行数：文件本身、bronze、silver 和隔离表。
    Rows of one batch file: in the file itself, in bronze, in silver and in the quarantine table."""
    like = "%" + os.path.basename(path)
    counts = {"file": spark.read.parquet(path).count()}
    for label, table in (("bronze", "bronze_staging_mt5_deals"), ("silver", "silver_staging_mt5_deals"),
                         ("quarantine", "silver_staging_mt5_deals_quarantine")):
        counts[label] = spark.sql(f"SELECT count(*) AS n FROM {cs}.{table} WHERE source_file LIKE :f",
                                  args={"f": like}).first()["n"]
    return counts


def latest_update_flows(spark, cs: str) -> dict:
    """最近一次管道更新中每张表的最终状态，来自事件日志。
    The final status of every table in the latest pipeline update, from the event log."""
    rows = spark.sql(f"""
      WITH latest AS (
        SELECT origin.update_id AS update_id FROM {cs}.pipeline_event_log
        WHERE event_type = 'create_update' ORDER BY timestamp DESC LIMIT 1)
      SELECT origin.flow_name AS flow,
             -- 最后还有一条只含执行指标、没有状态的事件，所以只看有状态的事件
             -- (each flow ends with a metrics-only event that has no status, so only read events that have one)
             max_by(details:flow_progress.status, timestamp) FILTER (WHERE details:flow_progress.status IS NOT NULL) AS status
      FROM {cs}.pipeline_event_log JOIN latest ON origin.update_id = latest.update_id
      WHERE event_type = 'flow_progress'
      GROUP BY ALL""").collect()
    return {r["flow"].replace("`", "").split(".")[-1]: r["status"] for r in rows}
