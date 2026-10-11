"""实验 03c 笔记本的结构检查：手动（UI）模式下的单元格顺序和防护。
Structural checks of the lab 03c notebook: cell order and guards for the hand (UI) mode."""

import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
with open(os.path.join(ROOT, "labs", "03c_Data_Quality_and_Monitoring.py"), encoding="utf-8") as fh:
    SOURCE = fh.read()
CELLS = SOURCE.split("# COMMAND ----------")
CODE = [c for c in CELLS if "# MAGIC %md" not in c and "# MAGIC %sql" not in c and "# MAGIC %run" not in c]
READS = re.compile(r"batch_counts\(|latest_update_flows\(|FROM silver_staging")


def test_no_cell_both_writes_a_batch_and_runs_the_pipeline():
    # 重新运行"运行管道"的单元格不能再写一个坏批次 (re-running a "run the pipeline" cell must not write another bad batch)
    for cell in CODE:
        assert not ("write_batch(" in cell and "pipeline_run(" in cell), cell.strip()[:200]


def test_every_check_cell_waits_for_the_update_before_reading_results():
    readers = [c for c in CODE if READS.search(c)]
    assert readers
    for cell in readers:
        wait = cell.find("wait_for_latest_update(")
        assert 0 <= wait < READS.search(cell).start(), cell.strip()[:200]


def test_the_lineage_query_is_guarded():
    cell = next(c for c in CODE if "ops.table_lineage" in c)
    assert "try:" in cell and "except Exception" in cell


def test_hand_wiring_is_checked_in_ui_mode():
    cell = next(c for c in CODE if "lane_status(" in c and 'lane["staging_root"]' in c)
    for key in ('lane["file"]', 'lane["price_rule"]'):
        assert key in cell


def test_the_lab_ends_by_checking_the_pipeline_is_green_for_day_2():
    final = [c for c in CODE if 'lane_status(' in c and '["latest_update"]' in c]
    assert final and CODE.index(final[-1]) > CODE.index(next(c for c in CODE if "ops.table_lineage" in c))
    md = [c for c in CELLS if "# MAGIC %md" in c]
    fail_section = next(c for c in md if "## 4 ·" in c)
    assert "第 6 步" in fail_section and "step 6" in fail_section
