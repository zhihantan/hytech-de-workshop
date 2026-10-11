# Databricks notebook source
# MAGIC %md
# MAGIC # live_feed · 你自己的实时数据 (your own live data)
# MAGIC
# MAGIC 实验 00 和 `00b_Live_Data` 用 `%run ./live_feed` 加载本笔记本：这里只有定义，不运行任何东西。
# MAGIC
# MAGIC Lab 00 and `00b_Live_Data` load this notebook with `%run ./live_feed`: it only holds definitions; nothing runs here.

# COMMAND ----------

import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor

import pyarrow.parquet as pq

PERSONAL_VOLUMES = ("landing", "producer")
LOAD_TABLES = ("mt5_users", "mt5_deals", "mt5_positions")
MAX_TICKS = 20


def personal_roots(catalog: str, user_name: str) -> dict:
    """你的 schema 和个人 volume 的路径（与实验 00、04b 的命名规则相同）。
    Paths of your schema and your personal volumes (the same naming rule as labs 00 and 04b)."""
    local = user_name.split("@")[0].lower()
    schema = "u_" + "".join(ch if ch.isalnum() else "_" for ch in local).strip("_")
    root = f"/Volumes/{catalog}/{schema}"
    return {"schema": schema, "volume_root": root, "landing": f"{root}/landing", "producer": f"{root}/producer"}


def copy_missing(src_root: str, dst_root: str, workers: int = 16) -> tuple:
    """把 src_root 中 dst_root 还没有（或大小不同）的文件复制过去，返回 (复制数, 跳过数)。从不删除；中断后重新运行即可补齐。
    不用临时文件名：落地区里的临时文件会被 Auto Loader 读到；写入 volume 的文件在关闭时才上传，所以只会出现完整的文件。
    Copy the files of src_root that dst_root lacks (or has with another size); returns (copied, skipped). Never deletes;
    a re-run after an interruption completes the copy. No temporary names: Auto Loader would read a temporary file in a
    landing folder; a volume file is uploaded when it is closed, so only whole files appear."""
    os.listdir(src_root)   # 没有读取权限时在这里报错，而不是悄悄地什么都不复制 (fail here when unreadable, instead of silently copying nothing)
    todo, skipped = [], 0
    for folder, _, files in os.walk(src_root):
        rel = os.path.relpath(folder, src_root)
        for name in files:
            src = os.path.join(folder, name)
            dst = os.path.normpath(os.path.join(dst_root, rel, name))
            if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
                skipped += 1
            else:
                todo.append((src, dst))

    def copy_one(pair):
        src, dst = pair
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(copy_one, todo))
    return len(todo), skipped


def seed_producer(src_root: str, dst_root: str) -> bool:
    """复制一次数据生成器的状态：先复制各个 frame，最后复制 state.json（有它就说明复制完整）。dst_root 已经有
    state.json 时什么都不做并返回 False：重新运行实验 00 不会把你的 tick 回滚（回滚会让成交编号重复）。
    Copy the data generator's state once: the frames first, state.json last (its presence means the copy is complete).
    Does nothing and returns False when dst_root already has a state.json: re-running lab 00 never rolls your ticks back
    (a rollback would reuse deal numbers)."""
    if os.path.exists(os.path.join(dst_root, "state.json")):
        return False
    names = sorted(n for n in os.listdir(src_root) if os.path.isfile(os.path.join(src_root, n)))
    if "state.json" not in names:
        raise FileNotFoundError(os.path.join(src_root, "state.json"))
    os.makedirs(dst_root, exist_ok=True)
    for name in [n for n in names if n != "state.json"] + ["state.json"]:
        shutil.copyfile(os.path.join(src_root, name), os.path.join(dst_root, name))
    return True


def check_widgets(ticks: str, new_server: str, bad_batch_pct: str, known_servers) -> list:
    """检查 00b 的输入，返回问题列表（空 = 没问题）(check the 00b inputs; returns the problems, empty = fine)."""
    problems = []
    try:
        if not 1 <= int(ticks) <= MAX_TICKS:
            raise ValueError
    except ValueError:
        problems.append(f"ticks 必须是 1–{MAX_TICKS} 的整数 (ticks must be a whole number from 1 to {MAX_TICKS})")
    server = new_server.strip()
    if server and server not in known_servers:
        names = ", ".join(sorted(known_servers))
        problems.append(f"不认识的服务器 {server}，可选：{names} (unknown server {server}; choose one of: {names})")
    try:
        if not 0 <= float(bad_batch_pct) <= 100:
            raise ValueError
    except ValueError:
        problems.append("bad_batch_pct 必须是 0–100 的数字 (bad_batch_pct must be a number from 0 to 100)")
    return problems


def run_ticks(cfg, ticks: int, new_server: str = "", bad_pct: float = 0.0, log=print) -> list:
    """连续写入 ticks 批新文件；new_server 在第一批中上线。bad_pct 是 0–1 的比例。
    Write `ticks` batches of new files one after another; new_server is onboarded in the first batch. bad_pct is a
    fraction from 0 to 1."""
    from hytech_workshop.drip import run_drip

    def quiet_ticks(msg):   # run_drip 每次都打印 "tick 1/1"；进度由下面打印 (run_drip prints "tick 1/1" every call; progress is printed below)
        if not str(msg).startswith("tick "):
            log(msg)

    results = []
    for i in range(ticks):
        if i:
            # 下一秒才开始：事件文件名精确到秒，同一秒的两批会互相覆盖
            # start in the next second: event file names are per second, so two batches in one second overwrite each other
            time.sleep(1.0 - time.time() % 1.0 + 0.01)
        result = run_drip(cfg, interval_seconds=30, max_ticks=1, bad_batch_pct=bad_pct, log=quiet_ticks,
                          new_server=(new_server.strip() or None) if i == 0 else None)
        log(f"tick {i + 1}/{ticks}: {result['rows']}")
        results.append(result)
    return results


def files_since(root: str, since: float) -> list:
    """root 下修改时间不早于 since 的文件，按路径排序 (files under root modified at or after `since`, sorted by path)."""
    out = []
    for folder, _, files in os.walk(root):
        for name in files:
            path = os.path.join(folder, name)
            if os.path.getmtime(path) >= since:
                out.append((path, os.path.getsize(path)))
    return sorted(out)


def summarize(landing_root: str, files) -> list:
    """把新文件整理成 (表, 服务器, 文件, 行数) 的列表 (turn the new files into (table, server, file, rows) rows)."""
    out = []
    for path, _ in files:
        parts = os.path.relpath(path, landing_root).split(os.sep)
        if parts[0] == "mt5" and len(parts) == 4:
            out.append((parts[2], parts[1], parts[3], pq.read_metadata(path).num_rows))
        elif parts[0] == "app_events":
            with open(path, encoding="utf-8") as fh:
                out.append(("app_events", "", "/".join(parts[1:]), sum(1 for line in fh if line.strip())))
    return out


def missing_files(summary, servers, new_server: str = "") -> list:
    """本次运行应该写入、却没有出现的文件：每个服务器至少一个新的 mt5_deals 文件；new_server 的三个 LOAD 文件。
    The files this run should have written but didn't: at least one new mt5_deals file per server; the three LOAD
    files of new_server."""
    seen = {(table, server, name) for table, server, name, _ in summary}
    missing = [f"{s}/mt5_deals" for s in servers if not any(t == "mt5_deals" and sv == s for t, sv, _ in seen)]
    server = new_server.strip()
    if server:
        missing += [f"{server}/{t}/LOAD00000001.parquet" for t in LOAD_TABLES
                    if (t, server, "LOAD00000001.parquet") not in seen]
    return missing
