# ===========================================================================
# Bronze · MT5 CDC files from AWS DMS (Auto Loader)
# 一个函数为每个 MT5 表创建一个流式表。路径模式 `mt5/*/<table>/` 会选择每个服务器 —
# 包括稍后加入的服务器 — 无需修改管道（元数据驱动的数据接入）。
# One function creates one streaming table per MT5 table. The path glob
# `mt5/*/<table>/` picks up every server — including servers onboarded later —
# without changing the pipeline (metadata-driven ingestion).
# ===========================================================================
from pyspark import pipelines as dp
from pyspark.sql import functions as F

LANDING = spark.conf.get("landing_root")

MT5_TABLES = {
    "mt5_users": "MT5 client accounts — raw DMS full load + CDC (Op = I/U/D)",
    "mt5_deals": "MT5 deals (trades in/out, deposits/withdrawals) — raw DMS full load + CDC",
    "mt5_positions": "MT5 open positions — raw DMS full load + CDC",
}


def bronze_table(table: str, comment: str) -> None:
    @dp.table(name=f"bronze_{table}", comment=comment, table_properties={"quality": "bronze"})
    def _bronze():
        return (
            spark.readStream.format("cloudFiles")
            # TODO 1a · DMS 写入 Parquet 文件。提示：Auto Loader 的文件格式选项
            # TODO 1a · DMS writes Parquet files. Hint: Auto Loader's file format option
            .option("cloudFiles.format", "____")
            .load(f"{LANDING}/mt5/*/{table}/")
            .select(
                "*",
                # TODO 1b · 从 /mt5/ 后面捕获文件夹名称（例如 mt5-sg-01）。提示：r"/mt5/([^/]+)/"
                # TODO 1b · capture the folder name after /mt5/ (e.g. mt5-sg-01). Hint: r"/mt5/([^/]+)/"
                F.regexp_extract("_metadata.file_path", r"____", 1).alias("server_id"),
                F.col("_metadata.file_path").alias("source_file"),
                F.col("_metadata.file_modification_time").alias("file_modified_at"),
                F.current_timestamp().alias("ingested_at"),
            )
        )


for name, description in MT5_TABLES.items():
    bronze_table(name, description)
