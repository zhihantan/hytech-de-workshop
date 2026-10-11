"""作业定义和作业任务的结构检查 (structural checks for the job definitions and job tasks)."""

import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def test_every_job_definition_passes_report_date():
    for path in ("labs/04b_Jobs_Catch_Up.py", "setup/00_master_setup.py"):
        assert '{"name": "report_date", "default": ""}' in read(path), path
    assert re.search(r'- name: report_date\n\s+default: ""', read("resources/solution.job.yml"))


def test_publish_daily_summary_is_date_aware_and_idempotent():
    text = read("jobs/publish_daily_summary.py")
    assert 'dbutils.widgets.text("report_date", ""' in text
    assert "MERGE INTO {cs}.gold_daily_commentary" in text
    assert "INSERT INTO {cs}.gold_daily_commentary" not in text


def test_dq_gate_merges_per_update():
    text = read("jobs/dq_gate.py")
    assert "MERGE INTO {cs}.ops_dq_results" in text
    assert 'mode("append")' not in text


def test_publish_daily_summary_accepts_a_backfill_date_or_datetime():
    # Run backfill 的参数可以选 {{backfill.iso_date}} 或 {{backfill.iso_datetime}}：两种都要能用
    # Run backfill can pass {{backfill.iso_date}} or {{backfill.iso_datetime}}: both must work
    assert "date.fromisoformat(requested[:10])" in read("jobs/publish_daily_summary.py")
