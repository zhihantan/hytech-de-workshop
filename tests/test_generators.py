"""合成数据生成器的快速本地检查 (pip install pandas numpy pyarrow pytest)。
Fast local checks for the synthetic data generator (pip install pandas numpy pyarrow pytest)."""

import glob
import os
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hytech_workshop.config import WorkshopConfig, participant_schema  # noqa: E402
from hytech_workshop.drip import run_drip  # noqa: E402
from hytech_workshop.history import build_all  # noqa: E402
from hytech_workshop.mt5 import round_to  # noqa: E402


@pytest.fixture(scope="module")
def landing(tmp_path_factory):
    root = str(tmp_path_factory.mktemp("vol"))
    cfg = WorkshopConfig(volume_root=root, users_per_server=200, positions_per_server_per_day=150,
                         history_days=5, events_per_day=500, event_days=2)
    manifest = build_all(cfg, log=lambda *a: None)
    return cfg, manifest


def read(cfg, server, table):
    files = sorted(glob.glob(f"{cfg.mt5_dir(server, table)}/*.parquet"))
    return pd.concat([pq.read_table(f).to_pandas() for f in files], ignore_index=True), files


def test_participant_schema():
    assert participant_schema("zhihan.tan@databricks.com") == "u_zhihan_tan"
    assert participant_schema("Li-Wei.Zhang@hytech.example") == "u_li_wei_zhang"


def test_round_to_per_element():
    assert list(round_to([1.23456, 1.23456], [2, 4])) == [1.23, 1.2346]


def test_dms_layout(landing):
    cfg, manifest = landing
    for server in cfg.servers:
        for table in ("mt5_users", "mt5_deals", "mt5_positions"):
            _, files = read(cfg, server, table)
            names = [os.path.basename(f) for f in files]
            assert "LOAD00000001.parquet" in names
            assert any(n[:8].isdigit() and n[8] == "-" for n in names), "no CDC files"


def test_deal_ids_unique_and_inserts_dominate(landing):
    cfg, _ = landing
    deals, _ = read(cfg, cfg.servers[0], "mt5_deals")
    inserts = deals[deals.Op == "I"]
    assert inserts.Deal.is_unique
    assert (deals.Op == "I").mean() > 0.98
    trades = inserts[inserts.Action != 2]
    # finalize_deals injects four kinds of invalid row; small test batches may get only one, of any kind
    future = trades.Time > pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=1)
    invalid = (trades.Volume == 0) | trades.Symbol.isna() | (trades.Price <= 0) | future
    assert invalid.sum() > 0, "no invalid rows injected"


def test_clients_lose_on_average(landing):
    cfg, _ = landing
    deals = pd.concat([read(cfg, s, "mt5_deals")[0] for s in cfg.servers])
    outs = deals[(deals.Action != 2) & (deals.Entry == 1) & (deals.Op == "I")]
    assert outs.Profit.sum() < 0


def test_positions_cdc_ops(landing):
    cfg, _ = landing
    pos, _ = read(cfg, cfg.servers[0], "mt5_positions")
    assert set(pos.Op) == {"I", "U", "D"}


def test_events_drift(landing):
    cfg, manifest = landing
    assert manifest["app_events"]["events"] > 0
    lines = [ln for f in glob.glob(f"{cfg.events_dir}/*/*.json") for ln in open(f, encoding="utf-8")]
    assert any('"campaign_id"' in ln for ln in lines)


def test_drip_onboards_new_server(landing):
    cfg, _ = landing
    result = run_drip(cfg, interval_seconds=0.1, max_ticks=1, new_server="mt5-hk-01", log=lambda *a: None)
    assert "mt5-hk-01" in result["servers"]
    _, files = read(cfg, "mt5-hk-01", "mt5_deals")
    assert any(os.path.basename(f) == "LOAD00000001.parquet" for f in files)
    assert np.isfinite(result["rows"].get("mt5_deals", 0))
