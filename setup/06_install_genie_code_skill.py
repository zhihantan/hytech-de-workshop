# Databricks notebook source
# MAGIC %md
# MAGIC # 06 · 安装 Genie Code 技能 (Install the `hytech-de-conventions` Genie Code skill)
# MAGIC
# MAGIC Copies `genie_code/.assistant/skills/hytech-de-conventions/SKILL.md` to the workspace-wide skills folder
# MAGIC `/Workspace/.assistant/skills/` (needs workspace-admin rights). Optionally also into each participant's
# MAGIC home `/Users/<email>/.assistant/skills/` — use this if the workspace-wide folder is not allowed.

# COMMAND ----------

dbutils.widgets.text("participants", "", "Optional: emails for per-user install")
dbutils.widgets.dropdown("workspace_wide", "true", ["true", "false"])

# COMMAND ----------

import os

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat

w = WorkspaceClient()
skill = "hytech-de-conventions"
src = os.path.abspath(os.path.join(os.getcwd(), "..", "genie_code", ".assistant", "skills", skill, "SKILL.md"))
content = open(src, "rb").read()

targets = []
if dbutils.widgets.get("workspace_wide") == "true":
    targets.append(f"/Workspace/.assistant/skills/{skill}")
emails = [e.strip() for e in dbutils.widgets.get("participants").replace("\n", ",").split(",") if e.strip()]
targets += [f"/Users/{e}/.assistant/skills/{skill}" for e in emails]

for t in targets:
    try:
        w.workspace.mkdirs(t)
        w.workspace.upload(f"{t}/SKILL.md", content, format=ImportFormat.AUTO, overwrite=True)
        print("✅ installed", f"{t}/SKILL.md")
    except Exception as e:  # noqa: BLE001
        print("⚠️ ", t, "->", str(e).splitlines()[0][:200])
