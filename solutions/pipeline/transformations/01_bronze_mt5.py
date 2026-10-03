# ===========================================================================
# Bronze · MT5 CDC files from AWS DMS (Auto Loader)
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
            .option("cloudFiles.format", "parquet")
            .load(f"{LANDING}/mt5/*/{table}/")
            .select(
                "*",
                F.regexp_extract("_metadata.file_path", r"/mt5/([^/]+)/", 1).alias("server_id"),
                F.col("_metadata.file_path").alias("source_file"),
                F.col("_metadata.file_modification_time").alias("file_modified_at"),
                F.current_timestamp().alias("ingested_at"),
            )
        )


for name, description in MT5_TABLES.items():
    bronze_table(name, description)
