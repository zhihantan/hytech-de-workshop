"""实验 04c 笔记本的结构检查：手动（UI）模式下检查单元格必须对准你刚做的操作。
Structural checks of the lab 04c notebook: in hand (UI) mode, check cells must look at what you just did."""

import ast
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
PATH = os.path.join(ROOT, "labs", "04c_Failure_Recovery_and_Backfill.py")
with open(PATH, encoding="utf-8") as fh:
    SOURCE = fh.read()
CELLS = SOURCE.split("# COMMAND ----------")
CODE = [c for c in CELLS if "# MAGIC %md" not in c and "# MAGIC %sql" not in c and "# MAGIC %run" not in c]
MD = [c for c in CELLS if "# MAGIC %md" in c]
CJK = re.compile(r"[一-鿿]")


def cell_with(text):
    return next(c for c in CODE if text in c)


def test_step_5_uses_the_policy_fix_and_points_to_03c_for_the_source_fix():
    # 源头修复要删除所有坏文件并完全刷新；本实验的检查按策略修复验证 (a source fix must delete every bad file and fully
    # refresh; this lab's checks verify the policy fix)
    step5 = next(c for c in MD if "## 5 ·" in c)
    assert "DROP ROW" in step5 and "03c 第 7 步" in step5 and "lab 03c step 7" in step5
    assert "删除坏文件" not in step5 and "delete the bad file" not in step5


def test_the_repair_check_survives_a_deleted_bad_file():
    cell = cell_with("for path in [bad_batch] + late_batches:")
    assert 0 <= cell.find("os.path.exists(path)") < cell.find("batch_counts(")


def test_the_step_2_check_only_accepts_a_run_started_after_the_bad_batch():
    write = cell_with('write_batch(spark, catalog, my_schema, "bad_prices")')
    assert "bad_batch_at" in write
    assert "latest_run(since_ms=bad_batch_at" in cell_with("broken_run_id = ")


def test_the_repair_check_waits_for_a_repair():
    assert "wait_repaired(broken_run_id)" in cell_with("for path in [bad_batch] + late_batches:")
    helpers = cell_with("def wait_repaired(")
    assert '"include_history": "true"' in helpers and '"REPAIR"' in helpers


def test_the_backfill_check_waits_for_the_backfill_runs_before_counting():
    cell = cell_with("FROM gold_daily_commentary GROUP BY report_date")
    assert 0 <= cell.find("backfill_runs(") < cell.find("wait_run(") < cell.find("FROM gold_daily_commentary")


def test_the_prepare_check_names_a_missing_run_pipeline_task():
    cell = cell_with("check(\"作业参数 report_date")
    assert 'next((t for t in s["tasks"] if t["task_key"] == "run_pipeline"), None)' in cell
    assert "run_pipeline 存在" in cell


def test_participant_facing_prints_are_chinese_first_and_english():
    for node in ast.walk(ast.parse(SOURCE)):
        # 只看文字消息（字符串或 f-string），不看打印出来的 API 值 (only literal messages, not printed API values)
        if (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print" and node.args
                and isinstance(node.args[0], (ast.Constant, ast.JoinedStr))):
            parts = [v.value for v in ast.walk(node.args[0]) if isinstance(v, ast.Constant) and isinstance(v.value, str)]
            text = "".join(parts)
            if "checks passed" in text or not re.search(r"[A-Za-z]{3,}", text):
                continue   # 最后的计数行和 03c、03d 一样 (the final count line matches 03c and 03d)
            assert CJK.search(text), f"line {node.lineno}: {text!r}"
