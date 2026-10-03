# Databricks notebook source
# MAGIC %md
# MAGIC # 07 · 成本与运行仪表盘 (Cost & health dashboard)
# MAGIC
# MAGIC Publishes the AI/BI dashboard for the M6b demo from `dashboards/workshop_cost_health.json`. It reads only the
# MAGIC governed `ops` views (created in `05`) and only workshop pipelines and jobs. Re-running updates the same
# MAGIC dashboard in place. It lives in the runner's home folder, not `/Workspace/Shared` (where every user would
# MAGIC inherit CAN MANAGE). The participant group gets **CAN READ**; the dashboard runs with the publisher's
# MAGIC credentials, so viewers need no extra grants.

# COMMAND ----------

dbutils.widgets.text("catalog", "hytech_de_workshop")
dbutils.widgets.text("participant_group", "de_workshop_sz")
dbutils.widgets.text("warehouse_id", "", "SQL warehouse ID (empty = pick a serverless one)")

catalog = dbutils.widgets.get("catalog")
group = dbutils.widgets.get("participant_group").strip()
warehouse_id = dbutils.widgets.get("warehouse_id").strip()

# COMMAND ----------

import json
import os

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
NAME = "Hytech DE Workshop - Cost and Health"
PARENT = f"/Workspace/Users/{w.current_user.me().user_name}/hytech_de_workshop"

src = os.path.abspath(os.path.join(os.getcwd(), "..", "dashboards", "workshop_cost_health.json"))
serialized = open(src, encoding="utf-8").read().replace("hytech_de_workshop.ops.", f"{catalog}.ops.")
json.loads(serialized)  # fail fast on a broken file

if not warehouse_id:
    def running(x):
        return getattr(x.state, "value", "") == "RUNNING"

    serverless = sorted((x for x in w.warehouses.list() if x.enable_serverless_compute),
                        key=lambda x: (not running(x), x.name))
    if not serverless:
        raise ValueError("No serverless SQL warehouse found: set the warehouse_id parameter")
    warehouse_id = serverless[0].id
print("warehouse_id =", warehouse_id)

# COMMAND ----------

w.workspace.mkdirs(PARENT)
try:
    dashboard_id = w.api_client.do("GET", "/api/2.0/workspace/get-status",
                                   query={"path": f"{PARENT}/{NAME}.lvdash.json"})["resource_id"]
except Exception:  # noqa: BLE001 - first run: the dashboard does not exist yet
    dashboard_id = None

body = {"display_name": NAME, "serialized_dashboard": serialized, "warehouse_id": warehouse_id}
if dashboard_id:
    w.api_client.do("PATCH", f"/api/2.0/lakeview/dashboards/{dashboard_id}", body=body)
    print("✅ updated", dashboard_id)
else:
    dashboard_id = w.api_client.do("POST", "/api/2.0/lakeview/dashboards",
                                   body={**body, "parent_path": PARENT})["dashboard_id"]
    print("✅ created", dashboard_id)

w.api_client.do("POST", f"/api/2.0/lakeview/dashboards/{dashboard_id}/published",
                body={"embed_credentials": True, "warehouse_id": warehouse_id})
print("✅ published")

if group:
    try:
        w.api_client.do("PATCH", f"/api/2.0/permissions/dashboards/{dashboard_id}",
                        body={"access_control_list": [{"group_name": group, "permission_level": "CAN_READ"}]})
        print(f"✅ {group}: CAN_READ")
    except Exception as e:  # noqa: BLE001 - the group may not exist yet; the dashboard still works for admins
        print(f"⚠️  could not share with {group} ->", str(e).splitlines()[0][:200])

url = f"{w.config.host.rstrip('/')}/dashboardsv3/{dashboard_id}/published"
print(url)
displayHTML(f'<a href="{url}" target="_blank">{NAME}</a>')
