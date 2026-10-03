# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · 数据接入 (Data ingestion) — CTAS · COPY INTO · Auto Loader · JSON & rescued data
# MAGIC
# MAGIC | 方式 Method | 适合 | 增量? |
# MAGIC |---|---|---|
# MAGIC | `CREATE TABLE AS SELECT` + `read_files` | 一次性 / 小文件全量重建 | 否：每次全量 |
# MAGIC | `COPY INTO` | 批量、幂等地加载新文件（SQL） | 是：已加载的文件会被跳过 |
# MAGIC | **Auto Loader** (`cloudFiles`) | 持续到达的大量文件（DMS CDC!） | 是：checkpoint 记录已处理的文件 |
# MAGIC | Lakeflow Connect 托管连接器 | SaaS / 数据库（NetSuite GA，MySQL CDC 预览） | 是：托管 CDC |

# COMMAND ----------

from pyspark.sql import functions as F

catalog = "hytech_de_workshop"
me = spark.sql("SELECT current_user()").first()[0]
my_schema = "u_" + "".join(ch if ch.isalnum() else "_" for ch in me.split("@")[0].lower()).strip("_")
landing = f"/Volumes/{catalog}/raw/landing"
ref = f"/Volumes/{catalog}/raw/ref"
checkpoints = f"/Volumes/{catalog}/{my_schema}/checkpoints"
spark.sql(f"USE {catalog}.{my_schema}")
print("schema:", f"{catalog}.{my_schema}", "| checkpoints:", checkpoints)

# COMMAND ----------

# MAGIC %md ## A · CTAS — 一次性建表 (one-off load of a small reference file)

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE ref_fx_rates
# MAGIC COMMENT 'Daily USD value of each currency (CTAS from CSV)'
# MAGIC AS SELECT * FROM read_files('/Volumes/hytech_de_workshop/raw/ref/fx_rates/', format => 'csv', header => true);
# MAGIC
# MAGIC SELECT ccy, count(*) AS days, min(rate_date) AS first_day, max(rate_date) AS last_day, round(avg(usd_per_ccy), 6) AS avg_usd
# MAGIC FROM ref_fx_rates GROUP BY ccy ORDER BY ccy;

# COMMAND ----------

# MAGIC %md
# MAGIC ## B · COPY INTO — 幂等的批量加载 (idempotent batch load)
# MAGIC **运行两次！** 第二次 `num_affected_rows = 0`：COPY INTO 记得哪些文件已经加载过。

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE TABLE IF NOT EXISTS ref_symbols_copy COMMENT 'Symbols loaded with COPY INTO';
# MAGIC
# MAGIC COPY INTO ref_symbols_copy
# MAGIC FROM '/Volumes/hytech_de_workshop/raw/ref/symbols/'
# MAGIC FILEFORMAT = CSV
# MAGIC FORMAT_OPTIONS ('header' = 'true', 'inferSchema' = 'true')
# MAGIC COPY_OPTIONS ('mergeSchema' = 'true');

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT asset_class, count(*) AS symbols, collect_list(symbol) AS examples FROM ref_symbols_copy GROUP BY asset_class;

# COMMAND ----------

# MAGIC %md
# MAGIC ## C · Auto Loader — DMS CDC Parquet → bronze
# MAGIC * `cloudFiles.format` = 文件格式；`schemaLocation` = 推断出的 schema 存放处（并支持 schema 演进）
# MAGIC * `checkpointLocation` = 已处理文件的记录 → **只处理新文件**
# MAGIC * `trigger(availableNow=True)` = 处理完现有新文件就停止（批式调度的流）
# MAGIC * 路径通配符 `mt5/*/mt5_deals/`：以后新增的服务器会自动被接入

# COMMAND ----------

deals_stream = (
    spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "parquet")
    .option("cloudFiles.schemaLocation", f"{checkpoints}/bronze_deals_al/_schema")
    .load(f"{landing}/mt5/*/mt5_deals/")
    .select(
        "*",
        F.regexp_extract("_metadata.file_path", r"/mt5/([^/]+)/", 1).alias("server_id"),
        F.col("_metadata.file_path").alias("source_file"),
        F.col("_metadata.file_modification_time").alias("file_modified_at"),
        F.current_timestamp().alias("ingested_at"),
    )
)
query = (
    deals_stream.writeStream
    .option("checkpointLocation", f"{checkpoints}/bronze_deals_al")
    .trigger(availableNow=True)
    .toTable(f"{catalog}.{my_schema}.bronze_deals_al")
)
query.awaitTermination()
print("rows in this run:", sum(p["numInputRows"] for p in query.recentProgress))

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT server_id, Op, count(*) AS rows, count(DISTINCT source_file) AS files
# MAGIC FROM bronze_deals_al GROUP BY ALL ORDER BY server_id, Op;

# COMMAND ----------

# MAGIC %md
# MAGIC **再运行一次上面的 Auto Loader 单元格 (run the Auto Loader cell again):** 如果没有新文件，`rows in this run: 0`。
# MAGIC 讲师的 drip producer 每 30 秒写入新的 CDC 文件 → 再运行就只会读到那些新文件。

# COMMAND ----------

# MAGIC %md
# MAGIC ## D · JSON + rescued data — 数据契约 (a data contract for app events)
# MAGIC 我们给 Sensors 风格的事件定义一个**契约 schema**。契约外的新字段（如 `campaign_id`）和类型不符的值
# MAGIC （`amount` 以字符串 `"1,234.50"` 到达）不会丢失，而是进入 `_rescued_data`。

# COMMAND ----------

events_schema = """
  event_id STRING, event STRING, distinct_id STRING, time BIGINT,
  lib STRUCT<`$lib`: STRING, `$lib_version`: STRING>,
  properties STRUCT<`$os`: STRING, `$app_version`: STRING, `$country`: STRING, `$ip`: STRING, brand: STRING,
                    server_id: STRING, login: BIGINT, symbol: STRING, screen: STRING, method: STRING,
                    amount: DOUBLE, currency: STRING, feedback_text: STRING, rating: INT>
"""
events_query = (
    spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("rescuedDataColumn", "_rescued_data")
    .schema(events_schema)
    .load(f"{landing}/app_events/")
    .select("*", F.col("_metadata.file_path").alias("source_file"), F.current_timestamp().alias("ingested_at"))
    .writeStream
    .option("checkpointLocation", f"{checkpoints}/bronze_app_events_al")
    .trigger(availableNow=True)
    .toTable(f"{catalog}.{my_schema}.bronze_app_events_al")
)
events_query.awaitTermination()

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT event, properties.amount AS amount_parsed, _rescued_data
# MAGIC FROM bronze_app_events_al
# MAGIC WHERE _rescued_data IS NOT NULL
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- 有多少事件带有被"救回"的数据？哪些字段？
# MAGIC SELECT
# MAGIC   count(*)                                                                    AS events,
# MAGIC   count_if(_rescued_data IS NOT NULL)                                         AS with_rescued_data,
# MAGIC   count_if(get_json_object(_rescued_data, '$.properties.campaign_id') IS NOT NULL) AS new_field_campaign_id,
# MAGIC   count_if(get_json_object(_rescued_data, '$.properties.amount') IS NOT NULL)      AS amount_type_mismatch
# MAGIC FROM bronze_app_events_al;

# COMMAND ----------

# MAGIC %md
# MAGIC ## E · 小结 (Recap)
# MAGIC * bronze 保留**原始**数据 + 元数据列（`server_id`、`source_file`、`ingested_at`）→ 可追溯、可重放
# MAGIC * Auto Loader 的 checkpoint 让流式接入既增量又可靠；COPY INTO 适合 SQL 用户的批量增量加载
# MAGIC * 下一步 (next): 在 **Spark 声明式管道** 中，用更少的代码声明同样的 bronze 表，并加上 silver / gold 与数据质量规则。
