# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · 从这里开始 (Start here) — Hytech 交易湖仓工作坊
# MAGIC
# MAGIC **场景 (Scenario).** 你是 Hytech 新入职的数据工程师。4 台 MT5 交易服务器的 MySQL 通过 **AWS DMS** 把变更数据（CDC）
# MAGIC 以 Parquet 文件写入云存储。两天内你将搭建交易湖仓：**接入 → 清洗 → 报表集市 → 生产调度 → 治理与监控**。
# MAGIC
# MAGIC | 模块 Module | Notebook / 文件 | 你会做什么 |
# MAGIC |---|---|---|
# MAGIC | M1 | `00_Start_Here` (本页) | 创建自己的 schema，浏览数据 |
# MAGIC | M2 | `01_Unity_Catalog` | 授权、标签、列掩码、行过滤 |
# MAGIC | M3 | `02_Ingestion` | CTAS · COPY INTO · Auto Loader · JSON 与 rescued data |
# MAGIC | M4 | `03_pipeline/` + `03b_Explore_Pipeline` | Spark 声明式管道：bronze → silver → gold |
# MAGIC | M5 | `04_Lakeflow_Jobs` | 作业：DQ 闸门、for-each、Run-if、修复运行 |
# MAGIC | M6 | `05_Genie_Code` · `06_System_Tables` | Genie Code、系统表（成本 / 运行 / 血缘） |
# MAGIC | AI | `07_AI_Functions` | `ai_query` · `ai_classify` · `ai_mask` |
# MAGIC
# MAGIC 运行方式：右上角选择 **Serverless** 计算，然后逐个单元格运行（Shift + Enter）。

# COMMAND ----------

dbutils.widgets.text("catalog", "hytech_de_workshop")
catalog = dbutils.widgets.get("catalog")

me = spark.sql("SELECT current_user()").first()[0]
local = me.split("@")[0].lower()
my_schema = "u_" + "".join(ch if ch.isalnum() else "_" for ch in local).strip("_")
landing = f"/Volumes/{catalog}/raw/landing"

print(f"你好 {me}")
print(f"你的 schema (your schema): {catalog}.{my_schema}")
print(f"数据落地区 (landing zone):  {landing}")

# COMMAND ----------

# MAGIC %md ## 1 · 创建（或确认）你的 schema — Create (or confirm) your schema

# COMMAND ----------

try:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{my_schema} COMMENT 'Workshop schema for {me}'")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.{my_schema}.checkpoints COMMENT 'Auto Loader checkpoints (lab 02)'")
    print("✅ ready:", f"{catalog}.{my_schema}", "and volume", f"{catalog}.{my_schema}.checkpoints")
except Exception as e:  # noqa: BLE001
    print("⚠️ 无法创建 schema，请联系讲师 / Triones (ask the instructor):", str(e).splitlines()[0][:200])

display(spark.sql(f"DESCRIBE SCHEMA EXTENDED {catalog}.{my_schema}"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · 浏览落地区 — Explore the landing zone
# MAGIC
# MAGIC DMS 的目录结构：`mt5/<server>/<table>/`，里面有一个全量文件 `LOAD00000001.parquet`，以及按时间命名的增量 CDC 文件 `yyyymmdd-hhmmssfff.parquet`。每一行都有 `Op`（I 插入 / U 更新 / D 删除）和 `cdc_ts`（提交时间）。
# MAGIC
# MAGIC DMS directory structure: `mt5/<server>/<table>/` contains one full load file `LOAD00000001.parquet` and time-stamped incremental CDC files `yyyymmdd-hhmmssfff.parquet`. Each row has `Op` (I = insert / U = update / D = delete) and `cdc_ts` (commit time).

# COMMAND ----------

servers = [f.name.strip("/") for f in dbutils.fs.ls(f"{landing}/mt5/")]
rows = []
for s in servers:
    for t in ("mt5_users", "mt5_deals", "mt5_positions"):
        files = dbutils.fs.ls(f"{landing}/mt5/{s}/{t}/")
        rows.append((s, t, len(files), sum(f.name.startswith("LOAD") for f in files), max(f.name for f in files)))
display(spark.createDataFrame(rows, "server string, table string, files int, load_files int, newest_file string"))

# COMMAND ----------

# MAGIC %md 看一看全量文件和一个 CDC 文件 (peek at the full load and one CDC file) — 注意 `Op` 和 `cdc_ts`：

# COMMAND ----------

deals_dir = f"{landing}/mt5/mt5-sg-01/mt5_deals/"
cdc_file = sorted(f.path for f in dbutils.fs.ls(deals_dir) if not f.name.startswith("LOAD"))[-1]
display(spark.read.parquet(deals_dir + "LOAD00000001.parquet").limit(5))
display(spark.read.parquet(cdc_file).groupBy("Op").count())

# COMMAND ----------

# MAGIC %md
# MAGIC **MT5 字段速查 (field cheat sheet)**
# MAGIC
# MAGIC | 字段 (Field) | 含义 (Meaning) |
# MAGIC |---|---|
# MAGIC | `Action` | 0 = BUY, 1 = SELL, 2 = BALANCE（入金 `Profit > 0` / 出金 `Profit < 0`）<br>0 = BUY, 1 = SELL, 2 = BALANCE (deposit `Profit > 0` / withdrawal `Profit < 0`) |
# MAGIC | `Entry` | 0 = IN 开仓, 1 = OUT 平仓（已实现盈亏只在 OUT 上）<br>0 = IN open, 1 = OUT close (realized P&L only on OUT) |
# MAGIC | `Volume` | 1/10000 手 → `lots = Volume / 10000`<br>1/10000 lot → `lots = Volume / 10000` |
# MAGIC | `Profit` · `Commission` · `Storage` | 客户盈亏 · 佣金 · 隔夜利息（美元）<br>Client P&L · commission · overnight interest (USD) |
# MAGIC | `RateProfit` | 报价货币 → 美元的汇率；名义金额 = lots × ContractSize × Price × RateProfit<br>Quote currency → USD exchange rate; notional = lots × ContractSize × Price × RateProfit |
# MAGIC | `Group` | `real\<品牌>\<账户类型>-USD`，例如 `real\Apex\RAW-USD`<br>`real\<brand>\<account-type>-USD`, e.g. `real\Apex\RAW-USD` |
# MAGIC | `Agent` | 介绍经纪人 IB 的 login（0 = 无）<br>IB (introducing broker) login (0 = none) |

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 · 复制实验文件到你的目录 — Copy the lab files to your home folder
# MAGIC
# MAGIC 你需要一份**可编辑**的副本（尤其是 `03_pipeline/`）。下面的单元格会把 `labs/` 和作业用的 `jobs/` 复制到 `/Users/<you>/hytech_de_lab/`（已存在的文件不会被覆盖）。也可以在左侧工作区右键 **Clone**。
# MAGIC
# MAGIC You need an **editable** copy (especially `03_pipeline/`). The cell below copies `labs/` and job task notebooks `jobs/` to `/Users/<you>/hytech_de_lab/` (existing files are not overwritten). Alternatively, right-click **Clone** in the left sidebar.

# COMMAND ----------

import os

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ExportFormat, ImportFormat, ObjectType

w = WorkspaceClient()


def ws_path(p: str) -> str:
    return p[len("/Workspace"):] if p.startswith("/Workspace/") else p


def copy_tree(src: str, dst: str) -> None:
    w.workspace.mkdirs(dst)
    for obj in w.workspace.list(src):
        target = f"{dst}/{obj.path.rsplit('/', 1)[-1]}"
        try:
            if obj.object_type in (ObjectType.DIRECTORY, ObjectType.REPO):
                copy_tree(obj.path, target)
            elif obj.object_type == ObjectType.NOTEBOOK:
                exp = w.workspace.export(obj.path, format=ExportFormat.SOURCE)
                w.workspace.import_(target, content=exp.content, format=ImportFormat.SOURCE, language=obj.language)
                print("  notebook", target)
            elif obj.object_type == ObjectType.FILE:
                exp = w.workspace.export(obj.path, format=ExportFormat.AUTO)
                w.workspace.import_(target, content=exp.content, format=ImportFormat.AUTO)
                print("  file    ", target)
        except Exception as e:  # noqa: BLE001 - 已存在，保留学员版本 (already exists, keep the participant's version)
            if "exists" not in str(e).lower():
                raise
            print("  (kept existing)", target)


src_labs = ws_path(os.getcwd())                      # <repo>/labs (<repo>/labs)
src_jobs = src_labs.rsplit("/", 1)[0] + "/jobs"       # <repo>/jobs 包含 lab 04 的任务 notebook (task notebooks for lab 04)
dst_labs = f"/Users/{me}/hytech_de_lab"
if src_labs.rstrip("/") == dst_labs:
    print("You are already running from your own copy.")
else:
    copy_tree(src_labs, dst_labs)
    copy_tree(src_jobs, f"{dst_labs}/jobs")
    print(f"\n✅ 完成。请打开 {dst_labs}/01_Unity_Catalog 继续 (continue from your copy).")
