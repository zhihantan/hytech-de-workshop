# Databricks notebook source
# MAGIC %md
# MAGIC # run_if_spec · 实验 03d 的作业定义 (the lab 03d job definition)
# MAGIC
# MAGIC 实验 03d 用 `%run ./run_if_spec` 加载本笔记本。这里只有定义，不运行任何东西。
# MAGIC
# MAGIC Lab 03d loads this notebook with `%run ./run_if_spec`. It only holds definitions; nothing runs here.

# COMMAND ----------

# 三个起点任务：检查每台服务器的 DMS 文件并对账（jobs/reconcile_server）
# Three starting tasks: check each server's DMS files and reconcile them (jobs/reconcile_server)
CHECK_TASKS = [
    # (task_key, server_id, 预期结果 expected result)
    ("check_mt5_sg01", "mt5-sg-01", "SUCCESS"),
    ("check_mt5_uk01", "mt5-uk-01", "SUCCESS"),
    ("check_mt5_hk01", "mt5-hk-01", "FAILED"),   # 还在预发布通道，不在生产落地区 (still in staging, not in the production landing zone)
]
# 七个条件任务：每种 Run if 一到两个例子 (seven condition tasks: one or two examples of each Run if)
CONDITION_TASKS = [
    # (task_key, notebook, depends_on, run_if, 预期结果 expected result)
    ("all_success_RUNS", "task_logger", ("check_mt5_sg01", "check_mt5_uk01"), "ALL_SUCCESS", "SUCCESS"),
    ("all_success_SKIPPED", "task_logger", ("check_mt5_uk01", "check_mt5_hk01"), "ALL_SUCCESS", "UPSTREAM_FAILED"),
    ("at_least_one_success_RUNS", "task_logger", ("check_mt5_uk01", "check_mt5_hk01"), "AT_LEAST_ONE_SUCCESS", "SUCCESS"),
    ("none_failed_RUNS", "task_logger", ("check_mt5_sg01", "check_mt5_uk01"), "NONE_FAILED", "SUCCESS"),
    ("none_failed_SKIPPED", "task_logger", ("check_mt5_uk01", "check_mt5_hk01"), "NONE_FAILED", "UPSTREAM_FAILED"),
    ("at_least_one_failed_ALERT", "notify", ("check_mt5_uk01", "check_mt5_hk01"), "AT_LEAST_ONE_FAILED", "SUCCESS"),
    ("all_failed_EXCLUDED", "task_logger", ("check_mt5_uk01", "check_mt5_hk01"), "ALL_FAILED", "EXCLUDED"),
]
# 最后一个任务：无论如何都运行，并记录本次运行中每个任务的状态（jobs/audit）
# The last task: always runs, and records the state of every task of the run (jobs/audit)
AUDIT_TASK = ("all_done_AUDIT", "audit", "ALL_DONE", "SUCCESS")
RUN_RESULT_EXPECTED = "SUCCESS_WITH_FAILURES"
RUN_IF_JOB_NOTEBOOKS = ("reconcile_server", "task_logger", "notify", "audit")


def run_if_job_name(name: str) -> str:
    return f"run_if_lab_{name}"


def run_if_job_settings(job_name: str, jobs_dir: str, catalog: str, schema: str) -> dict:
    """实验 03d 作业的 Jobs API 2.2 设置 (Jobs API 2.2 settings of the lab 03d job)."""
    ids = {"job_id": "{{job.id}}", "run_id": "{{job.run_id}}"}
    tasks = []
    for key, server, expected in CHECK_TASKS:
        task = {"task_key": key,
                "notebook_task": {"notebook_path": f"{jobs_dir}/reconcile_server", "base_parameters": {"server_id": server}}}
        if expected == "FAILED":
            # 故意失败的任务：不重试，也关闭无服务器自动重试，让失败立即可见
            # The task that fails by design: no retries and no serverless automatic retry, so the failure shows at once
            task.update(max_retries=0, disable_auto_optimization=True)
        tasks.append(task)
    for key, notebook, deps, run_if, _ in CONDITION_TASKS:
        if notebook == "notify":
            params = {"reason": "server_check_failed", "detail": f"run_if={run_if}", **ids}
        else:
            params = {"task_key": key, "run_if": run_if, "run_id": "{{job.run_id}}"}
        tasks.append({"task_key": key, "depends_on": [{"task_key": d} for d in deps], "run_if": run_if,
                      "notebook_task": {"notebook_path": f"{jobs_dir}/{notebook}", "base_parameters": params}})
    key, notebook, run_if, _ = AUDIT_TASK
    tasks.append({"task_key": key, "depends_on": [{"task_key": t[0]} for t in CONDITION_TASKS], "run_if": run_if,
                  "notebook_task": {"notebook_path": f"{jobs_dir}/{notebook}", "base_parameters": ids}})
    return {
        "name": job_name,
        "description": "Lab 03d: every Run if condition on the MT5 server checks (two servers pass, mt5-hk-01 fails).",
        "max_concurrent_runs": 1,
        "parameters": [{"name": "catalog", "default": catalog}, {"name": "schema", "default": schema}],
        "tasks": tasks,
    }


def expected_states() -> dict:
    """每个任务的预期结果 (the expected result of every task)."""
    states = {key: expected for key, _, expected in CHECK_TASKS}
    states.update({t[0]: t[4] for t in CONDITION_TASKS})
    states[AUDIT_TASK[0]] = AUDIT_TASK[3]
    return states


def compare_states(actual: dict, expected: dict) -> list:
    """(任务, 预期, 实际, 是否一致) 的列表 (rows of task, expected, actual, match)."""
    return [(key, want, actual.get(key), actual.get(key) == want) for key, want in expected.items()]
