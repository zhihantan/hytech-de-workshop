"""预发布通道辅助函数的离线检查 (offline checks for the staging-lane helpers)."""

import importlib.util
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

HERE = os.path.dirname(__file__)
_spec = importlib.util.spec_from_file_location("staging_feed", os.path.join(HERE, "..", "labs", "staging_feed.py"))
sf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sf)

NOW = datetime(2026, 10, 13, 3, 30, 15, 123456, tzinfo=timezone.utc)


def template(n=40):
    action = np.where(np.arange(n) % 10 == 0, 2, np.arange(n) % 2).astype(np.int32)
    trade = action != 2
    return pd.DataFrame({
        "Op": "I", "cdc_ts": pd.Timestamp("2026-10-12 09:00", tz="UTC"), "Deal": 1_100_000_000 + np.arange(n),
        "Login": 81_000_000 + np.arange(n), "Order": 1_200_000_000 + np.arange(n),
        "Time": pd.Timestamp("2026-10-12 09:00", tz="UTC"), "TimeMsc": 0, "Symbol": np.where(trade, "XAUUSD", ""),
        "Action": action, "Entry": np.zeros(n, dtype=np.int32), "Reason": np.zeros(n, dtype=np.int32),
        "Volume": np.where(trade, 10_000, 0).astype(np.int64), "Price": np.where(trade, 3900.5, 0.0),
        "ContractSize": 100.0, "RateProfit": 1.0, "Profit": np.where(trade, 0.0, 500.0), "Storage": 0.0,
        "Commission": -3.5, "Fee": 0.0, "PositionID": np.where(trade, 2_100_000_000 + np.arange(n), 0).astype(np.int64),
        "Dealer": 0, "Comment": "",
    })


def violations(df):
    trade = df["Action"] != 2
    return {
        "zero_volume": int((trade & (df["Volume"] <= 0)).sum()),
        "no_symbol": int((trade & df["Symbol"].isna()).sum()),
        "bad_price": int((trade & (df["Price"] <= 0)).sum()),
        "future": int((df["Time"] > pd.Timestamp(NOW) + pd.Timedelta(hours=1)).sum()),
        "no_login": int(df["Login"].isna().sum()),
    }


def test_clean_batch_breaks_no_rule():
    df = sf.make_batch(template(), "clean", 7, NOW)
    assert violations(df) == {"zero_volume": 0, "no_symbol": 0, "bad_price": 0, "future": 0, "no_login": 0}
    assert (df["Op"] == "I").all() and len(df) == 40


def test_junk_batch_has_three_zero_volumes_two_missing_symbols_one_future_deal():
    v = violations(sf.make_batch(template(), "junk", 7, NOW))
    assert v == {"zero_volume": 3, "no_symbol": 2, "bad_price": 0, "future": 1, "no_login": 0}


def test_bad_prices_batch_has_five_negative_prices_only():
    v = violations(sf.make_batch(template(), "bad_prices", 7, NOW))
    assert v == {"zero_volume": 0, "no_symbol": 0, "bad_price": 5, "future": 0, "no_login": 0}


def test_batch_is_rekeyed_to_mt5_hk01():
    df = sf.make_batch(template(), "clean", 7, NOW)
    assert df["Deal"].is_unique and df["Deal"].min() == sf.STAGING_DEAL_BASE + 7 * sf.BATCH_ROWS
    assert df["Login"].between(sf.STAGING_LOGIN_BASE, sf.STAGING_LOGIN_BASE + 999).all()
    assert (df.loc[df["Action"] == 2, "Order"] == 0).all()
    assert (df["Time"] <= pd.Timestamp(NOW)).all() and (df["cdc_ts"] > df["Time"]).all()
    assert (df["TimeMsc"] == (df["Time"] - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(milliseconds=1)).all()


def test_batches_with_different_keys_never_share_deal_ids():
    a, b = sf.make_batch(template(), "clean", 7, NOW), sf.make_batch(template(), "clean", 8, NOW)
    assert not set(a["Deal"]) & set(b["Deal"])


def test_unknown_scenario_is_rejected():
    with pytest.raises(ValueError):
        sf.make_batch(template(), "chaos", 1, NOW)


def test_template_without_enough_trades_is_rejected():
    t = template()
    with pytest.raises(ValueError):
        sf.make_batch(t[t["Action"] == 2], "clean", 1, NOW)


def test_dms_file_name():
    assert sf.dms_file_name(NOW) == "20261013-033015123.parquet"


def test_my_names_match_labs_00_and_04b():
    assert sf.my_names("Zhang.San-1@hytech.example") == {
        "name": "zhang_san_1", "schema": "u_zhang_san_1", "pipeline": "trade_lakehouse_zhang_san_1",
        "job": "daily_trading_reporting_zhang_san_1", "lab_root": "/Users/Zhang.San-1@hytech.example/hytech_de_lab",
    }


def test_staging_paths():
    assert sf.staging_root("c", "u_x") == "/Volumes/c/u_x/staging"
    assert sf.staging_dir("c", "u_x") == "/Volumes/c/u_x/staging/mt5/mt5-hk-01/mt5_deals"
