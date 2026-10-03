# Databricks notebook source
# MAGIC %md
# MAGIC # 99 · 清理 (Teardown)
# MAGIC
# MAGIC Drops the workshop catalog (all schemas, tables, volumes and files) and the Genie Code skill.
# MAGIC Jobs and pipelines deployed by the bundle are removed with `databricks bundle destroy`;
# MAGIC participant-created pipelines and jobs must be deleted in the UI (or by their owners).

# COMMAND ----------

dbutils.widgets.text("catalog", "hytech_de_workshop")
dbutils.widgets.text("confirm", "", "Type the catalog name to confirm")

catalog = dbutils.widgets.get("catalog")
if dbutils.widgets.get("confirm") != catalog:
    dbutils.notebook.exit(f"Not confirmed — type '{catalog}' in the confirm widget to drop it.")

# COMMAND ----------

spark.sql(f"DROP CATALOG IF EXISTS {catalog} CASCADE")
print("dropped catalog", catalog)

from databricks.sdk import WorkspaceClient

try:
    WorkspaceClient().workspace.delete("/Workspace/.assistant/skills/hytech-de-conventions", recursive=True)
    print("removed Genie Code skill")
except Exception as e:  # noqa: BLE001
    print("skill not removed:", str(e).splitlines()[0][:200])
