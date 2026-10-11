"""solutions/ 中的副本 = 实验文件去掉「要点」注释行 (solutions copies = the labs without the key-point lines)."""

import os
import re

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
PAIRS = [
    ("labs/02_Ingestion.py", "solutions/02_Ingestion.py"),
    ("labs/staging_feed.py", "solutions/staging_feed.py"),
    ("labs/run_if_spec.py", "solutions/run_if_spec.py"),
    ("labs/03c_Data_Quality_and_Monitoring.py", "solutions/03c_Data_Quality_and_Monitoring.py"),
    ("labs/03d_Run_If_Dependencies.py", "solutions/03d_Run_If_Dependencies.py"),
    ("labs/03_pipeline/staging/06_staging_mt5_hk01.sql", "solutions/pipeline/staging/06_staging_mt5_hk01.sql"),
    ("labs/04c_Failure_Recovery_and_Backfill.py", "solutions/04c_Failure_Recovery_and_Backfill.py"),
]
KEY_POINT = re.compile(r"^\s*(# MAGIC\s+)?(#|--)\s*(要点|Key point)")
PREAMBLE = ("本实验包含完整代码", "This lab has the complete code")


def strip_lab(text: str) -> str:
    """去掉要点注释、"完整代码"说明和标题中的 · LAB (drop key-point comments, the complete-code note and · LAB)."""
    out = []
    for line in text.splitlines(keepends=True):
        if KEY_POINT.match(line) or any(p in line for p in PREAMBLE):
            continue
        out.append(line.replace(" · LAB", ""))
    return "".join(out)


@pytest.mark.parametrize("lab, solution", PAIRS)
def test_solution_is_the_lab_without_key_points(lab, solution):
    with open(os.path.join(ROOT, lab), encoding="utf-8") as fh:
        expected = strip_lab(fh.read())
    with open(os.path.join(ROOT, solution), encoding="utf-8") as fh:
        assert fh.read() == expected
