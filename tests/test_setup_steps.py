"""设置步骤的结构检查 (structural checks for the setup steps)."""

import os

ROOT = os.path.join(os.path.dirname(__file__), "..")


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def test_the_warehouse_step_is_in_both_setup_job_definitions():
    assert "../setup/08_workshop_warehouses.py" in read("resources/setup.job.yml")
    assert 'task("workshop_warehouses", "setup/08_workshop_warehouses")' in read("setup/00_master_setup.py")


def test_the_warehouse_step_grants_can_use_and_creates_a_small_realtime_warehouse():
    text = read("setup/08_workshop_warehouses.py")
    assert '"permission_level": "CAN_USE"' in text
    assert '"warehouse_type": "REALTIME"' in text and '"cluster_size": "Small"' in text and '"auto_stop_mins": 10' in text


def test_teardown_removes_the_realtime_warehouse_setup_created():
    assert "hytech_workshop_rt" in read("setup/99_teardown.py")


def test_cost_dashboard_never_picks_a_realtime_warehouse():
    # SDK 把 warehouse_type = REALTIME 解析成 None（databricks-sdk 0.151），所以要读原始 JSON
    # The SDK parses warehouse_type = REALTIME as None (databricks-sdk 0.151), so the raw JSON must be read
    text = read("setup/07_cost_dashboard.py")
    assert '"/api/2.0/sql/warehouses"' in text and 'x.get("warehouse_type") != "REALTIME"' in text


def test_the_realtime_warehouse_is_created_with_a_cluster_range():
    # 在 fevm 上实测：不写 max_num_clusters 时 API 拒绝（0 is not a valid value for max_num_clusters）
    # Live on fevm: without max_num_clusters the API rejects the create (0 is not a valid value for max_num_clusters)
    text = read("setup/08_workshop_warehouses.py")
    assert '"min_num_clusters": 1' in text and '"max_num_clusters": 1' in text
    # 创建失败不一定是因为预览没开：先看错误 (a failed create is not always the preview being off: read the error first)
    assert "见上面的错误" in text and "see the error above" in text
