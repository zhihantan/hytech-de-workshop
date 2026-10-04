"""为 UC Volumes (或测试中的本地路径) 和生产者状态编写文件。
File writers for UC Volumes (or local paths in tests) and producer state."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def _atomic_copy(local_path: str, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(local_path, dest)


def write_parquet(table: pa.Table, dest: str) -> None:
    """本地写入后复制，以便 FUSE 挂载的 Volumes 只能看到完整文件。
    Write locally then copy, so FUSE-mounted Volumes only ever see whole files."""
    with tempfile.TemporaryDirectory() as d:
        tmp = os.path.join(d, "f.parquet")
        pq.write_table(table, tmp, compression="snappy")
        _atomic_copy(tmp, dest)


def write_text(text: str, dest: str) -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = os.path.join(d, "f.txt")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        _atomic_copy(tmp, dest)


def write_csv(df: pd.DataFrame, dest: str) -> None:
    write_text(df.to_csv(index=False), dest)


def dms_cdc_name(ts_us: int) -> str:
    """AWS DMS CDC 文件名: yyyymmdd-hhmmssfff.parquet
    AWS DMS CDC file name: yyyymmdd-hhmmssfff.parquet"""
    dt = datetime.fromtimestamp(ts_us / 1_000_000, tz=timezone.utc)
    return dt.strftime("%Y%m%d-%H%M%S") + f"{dt.microsecond // 1000:03d}.parquet"


def save_state(state: dict, producer_root: str, frames: dict[str, pd.DataFrame]) -> None:
    for name, df in frames.items():
        write_parquet(pa.Table.from_pandas(df, preserve_index=False), f"{producer_root}/{name}.parquet")
    write_text(json.dumps(state, indent=2, default=str), f"{producer_root}/state.json")


def load_state(producer_root: str) -> tuple[dict, dict[str, pd.DataFrame]]:
    with open(f"{producer_root}/state.json", encoding="utf-8") as fh:
        state = json.load(fh)
    frames = {}
    for name in state.get("frames", []):
        frames[name] = pq.read_table(f"{producer_root}/{name}.parquet").to_pandas()
    return state, frames
