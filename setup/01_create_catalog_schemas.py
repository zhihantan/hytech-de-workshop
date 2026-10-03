# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · 创建 Catalog / Schema / Volume 与授权 (Create catalog, schemas, volumes, grants)
# MAGIC
# MAGIC Idempotent — safe to re-run. Run as a workspace admin or the catalog owner (e.g. Triones).
# MAGIC
# MAGIC | Object | Purpose |
# MAGIC |---|---|
# MAGIC | `<catalog>.raw` · volumes `landing`, `ref`, `producer` | DMS-style MT5 CDC files, app events, reference CSVs, drip-producer state |
# MAGIC | `<catalog>.solutions` | Instructor solution pipeline (catch-up, AI Functions lab) |
# MAGIC | `<catalog>.ops` | Governed views over system tables (observability lab) |
# MAGIC | `<catalog>.u_<name>` | One schema per participant (created by `04_participant_schemas` or by the participant in `labs/00_Start_Here`) |

# COMMAND ----------

dbutils.widgets.text("catalog", "hytech_de_workshop")
dbutils.widgets.text("participant_group", "de_workshop_sz")
dbutils.widgets.dropdown("create_catalog", "true", ["true", "false"])

catalog = dbutils.widgets.get("catalog")
group = dbutils.widgets.get("participant_group").strip()
create_catalog = dbutils.widgets.get("create_catalog") == "true"

# COMMAND ----------


def run(stmt: str, optional: bool = False) -> bool:
    try:
        spark.sql(stmt)
        print("✅", " ".join(stmt.split())[:140])
        return True
    except Exception as e:  # noqa: BLE001 - surface any SQL error, optionally continue
        if not optional:
            raise
        print("⚠️ ", " ".join(stmt.split())[:140], "\n    ->", str(e).splitlines()[0][:220])
        return False


if create_catalog:
    run(f"CREATE CATALOG IF NOT EXISTS {catalog} COMMENT 'Hytech DE workshop — MT5 trade lakehouse'")

schemas = {
    "raw": "Landing zone: DMS-style MT5 CDC Parquet, Sensors-style app events, reference CSVs",
    "solutions": "Instructor solution pipeline output (catch-up, Genie, AI Functions labs)",
    "ops": "Governed views over system tables for the observability lab",
}
for name, comment in schemas.items():
    run(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{name} COMMENT '{comment}'")

volumes = {
    "landing": "MT5 CDC files (landing/mt5/<server>/<table>/) and app events (landing/app_events/<date>/)",
    "ref": "Reference CSVs: symbols, IB hierarchy, servers, daily FX rates",
    "producer": "Drip producer state (instructor only)",
}
for name, comment in volumes.items():
    run(f"CREATE VOLUME IF NOT EXISTS {catalog}.raw.{name} COMMENT '{comment}'")

run(f"ALTER SCHEMA {catalog}.raw SET TAGS ('workshop' = 'hytech_de_2026', 'layer' = 'landing')", optional=True)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Grants for the participant group
# MAGIC Participants can **read** the landing zone, solutions and ops views, and **create their own schema**.
# MAGIC Grants need an **account-level** group; if it does not exist yet, they are skipped with a warning.

# COMMAND ----------

grants = [
    f"GRANT USE CATALOG, CREATE SCHEMA ON CATALOG {catalog} TO `{group}`",
    f"GRANT USE SCHEMA ON SCHEMA {catalog}.raw TO `{group}`",
    f"GRANT READ VOLUME ON VOLUME {catalog}.raw.landing TO `{group}`",
    f"GRANT READ VOLUME ON VOLUME {catalog}.raw.ref TO `{group}`",
    f"GRANT USE SCHEMA, SELECT ON SCHEMA {catalog}.solutions TO `{group}`",
    f"GRANT USE SCHEMA, SELECT ON SCHEMA {catalog}.ops TO `{group}`",
]
results = [run(g, optional=True) for g in grants] if group else []
if group and not all(results):
    print(f"\nSome grants were skipped. Create the account-level group `{group}`, add the participants, and re-run.")

display(spark.sql(f"SHOW SCHEMAS IN {catalog}"))
