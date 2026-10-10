"""文档一致性检查：新实验在每个入口都能找到，文档中的名称与代码一致。
Docs consistency: the new labs can be found from every entry point, and the names in the docs match the code."""

import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
NEW_LABS = ("03c_Data_Quality_and_Monitoring", "03d_Run_If_Dependencies", "04c_Failure_Recovery_and_Backfill",
            "09_AIBI_Dashboard_Lakehouse_RT", "10_Genie_Agent")
ENTRY_POINTS = ("labs/00_Start_Here.py", "README.md", "docs/participant_guide_zh.md")


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def test_every_new_lab_is_listed_in_teaching_order_at_every_entry_point():
    for path in ENTRY_POINTS:
        text = read(path)
        positions = [text.find(lab) for lab in NEW_LABS]
        assert all(p >= 0 for p in positions), (path, dict(zip(NEW_LABS, positions)))
        assert positions == sorted(positions), path


def test_every_lab_file_is_in_the_readme():
    readme = read("README.md")
    for name in sorted(os.listdir(os.path.join(ROOT, "labs"))):
        stem = re.sub(r"\.(py|sql|md)$", "", name)
        if re.match(r"\d\d[a-z]?_", stem):
            assert stem in readme, name


def test_ai_functions_is_marked_optional_everywhere():
    for path in ENTRY_POINTS:
        row = next(line for line in read(path).splitlines() if "07_AI_Functions" in line)
        assert "可选" in row, (path, row)
