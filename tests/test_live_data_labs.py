"""实验 00、00b 和使用个人落地区的实验的结构检查 (structural checks for labs 00, 00b and the labs that use the personal landing zone)."""

import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def test_00b_takes_the_widgets_loads_the_helpers_and_finds_the_generator_in_either_layout():
    text = read("labs/00b_Live_Data.py")
    for widget in ('"catalog"', '"ticks"', '"new_server"', '"bad_batch_pct"'):
        assert f"dbutils.widgets.text({widget}" in text, widget
    assert "# MAGIC %run ./live_feed" in text
    assert 'os.path.join(os.getcwd(), "src")' in text and 'os.path.join(os.getcwd(), "..", "src")' in text
    assert 'WorkshopConfig(catalog=catalog, volume_root=roots["volume_root"])' in text
    for call in ("check_widgets(", "run_ticks(", "files_since(", "summarize(", "missing_files("):
        assert call in text, call


def test_00b_stops_with_a_bilingual_message_before_writing_anything():
    text = read("labs/00b_Live_Data.py")
    exits = [m.start() for m in re.finditer(r"dbutils\.notebook\.exit\(", text)]
    assert len(exits) == 3 and all(e < text.index("run_ticks(cfg") for e in exits)
    assert "run step 1b of 00_Start_Here first" in text and "re-run step 3 of 00_Start_Here" in text


def test_lab_00_copies_the_history_into_the_participants_own_volumes():
    text = read("labs/00_Start_Here.py")
    assert "# MAGIC %run ./live_feed" in text and "## 1b ·" in text
    assert text.index("## 1b ·") < text.index("## 2 ·")
    assert 'copy_missing(f"/Volumes/{catalog}/raw/landing", roots["landing"])' in text
    assert 'seed_producer(f"/Volumes/{catalog}/raw/producer", roots["producer"])' in text
    assert "except OSError" in text
    assert 'landing = f"/Volumes/{catalog}/{my_schema}/landing"' in text
    assert 'copy_tree(f"{src_repo}/src", f"{dst_labs}/src")' in text
    assert "`00b_Live_Data`" in text
