# Databricks notebook source
# MAGIC %md
# MAGIC # 08 · 工作坊 SQL 仓库与权限 (Workshop SQL warehouses and permissions)
# MAGIC
# MAGIC 实验 09（AI/BI 仪表盘）和实验 10（Genie Agent、Genie One）需要学员对 SQL 仓库有 **CAN USE** 权限。本笔记本：
# MAGIC
# MAGIC 1. 找到工作坊的 serverless SQL 仓库（不是 Real-Time 仓库），授予学员组 CAN USE。Genie 和成本仪表盘都用它。
# MAGIC 2. 如果工作区已开启 **Lakehouse RT** 预览，找到或创建 Real-Time 仓库 `hytech_workshop_rt`（Small、空闲 10 分钟自动停止），并授予学员组 CAN USE。未开启时打印管理员步骤，然后继续。
# MAGIC
# MAGIC 可以重复运行。
# MAGIC
# MAGIC Labs 09 (AI/BI dashboard) and 10 (Genie Agent, Genie One) need **CAN USE** on a SQL warehouse for the participants. This notebook:
# MAGIC
# MAGIC 1. Finds the workshop's serverless SQL warehouse (not a Real-Time one) and grants the participant group CAN USE. Genie and the cost dashboard use it.
# MAGIC 2. If the workspace has the **Lakehouse RT** preview on, finds or creates the Real-Time warehouse `hytech_workshop_rt` (Small, stops after 10 idle minutes) and grants the participant group CAN USE. If the preview is off, it prints the admin steps and carries on.
# MAGIC
# MAGIC Safe to re-run.

# COMMAND ----------

dbutils.widgets.text("participant_group", "de_workshop_sz")
dbutils.widgets.text("warehouse_id", "", "SQL warehouse ID (empty = pick a serverless one)")
dbutils.widgets.text("rt_warehouse_name", "hytech_workshop_rt")

group = dbutils.widgets.get("participant_group").strip()
warehouse_id = dbutils.widgets.get("warehouse_id").strip()
rt_name = dbutils.widgets.get("rt_warehouse_name").strip()

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
HOST = w.config.host.rstrip("/")
ADMIN_STEPS = """
创建 Real-Time 仓库失败，见上面的错误。如果是因为 Lakehouse RT 还没开启，管理员步骤如下：
(Creating the Real-Time warehouse failed: see the error above. If it is because Lakehouse RT is not enabled yet, the admin steps are:)
  1. 请 Databricks 客户团队为账户开启 Lakehouse//RT Beta (ask the Databricks account team to enable the Lakehouse//RT Beta for the account)
  2. 工作区菜单 → Previews → 搜索 "Lakehouse RT" → 开启 (workspace menu → Previews → search "Lakehouse RT" → enable)
  3. 重新运行本笔记本，或手动创建 Real-Time 仓库（Small，自动停止 10 分钟）并授予学员组 Can use
     (re-run this notebook, or create a Real-Time warehouse by hand — Small, auto stop 10 min — and grant the participant group Can use)
  另请确认：没有 serverless egress control、出站 Private Link 或合规安全配置，workshop catalog 不在 Unity Catalog 默认存储中。
  (Also check: no serverless egress control, outbound Private Link or compliance security profile, and the workshop catalog is not in Unity Catalog default storage.)
"""


def warehouses():
    """原始 JSON（含 warehouse_type）(raw JSON, including warehouse_type)."""
    return w.api_client.do("GET", "/api/2.0/sql/warehouses").get("warehouses", [])


def grant_use(wid, label):
    """授予学员组 CAN USE；组不存在时只提示 (grant the participant group CAN USE; warn if the group doesn't exist)."""
    if not group:
        return
    try:
        w.api_client.do("PATCH", f"/api/2.0/permissions/warehouses/{wid}",
                        body={"access_control_list": [{"group_name": group, "permission_level": "CAN_USE"}]})
        print(f"✅ {group}: CAN_USE on {label} ({wid})")
    except Exception as e:  # noqa: BLE001 - e.g. the account-level group is not created yet
        print(f"⚠️  could not grant CAN_USE on {label} to {group} ->", str(e).splitlines()[0][:200])


# 1 · serverless 仓库（Genie 不支持 Real-Time 仓库）(the serverless warehouse; Genie doesn't run on Real-Time warehouses)
if not warehouse_id:
    candidates = sorted((x for x in warehouses() if x.get("enable_serverless_compute") and x.get("warehouse_type") != "REALTIME"),
                        key=lambda x: (x.get("state") != "RUNNING", x["name"]))
    if not candidates:
        raise ValueError("找不到 serverless SQL 仓库：请设置 warehouse_id 参数 (no serverless SQL warehouse found: set the warehouse_id parameter)")
    warehouse_id = candidates[0]["id"]
grant_use(warehouse_id, "the workshop warehouse")
print("warehouse_id =", warehouse_id)

# COMMAND ----------

# 2 · Lakehouse RT
rt = next((x for x in warehouses() if x["name"] == rt_name), None)
if rt is None:
    try:
        rt = w.api_client.do("POST", "/api/2.0/sql/warehouses", body={
            "name": rt_name, "warehouse_type": "REALTIME", "cluster_size": "Small", "auto_stop_mins": 10,
            "min_num_clusters": 1, "max_num_clusters": 1,
            "enable_serverless_compute": True,
            "tags": {"custom_tags": [{"key": "workshop", "value": "hytech_de_2026"}, {"key": "managed_by", "value": "master_setup"}]},
        })
        print("✅ created Real-Time warehouse", rt_name, rt["id"])
    except Exception as e:  # noqa: BLE001 - the preview is off or the region is not supported
        print("⚠️ ", str(e).splitlines()[0][:300])
        print(ADMIN_STEPS)
        rt = None
if rt:
    grant_use(rt["id"], rt_name)
    print(f"{HOST}/sql/warehouses/{rt['id']}")
