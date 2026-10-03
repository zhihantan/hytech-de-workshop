"""Build the full landing zone: reference CSVs, DMS full load + 48h of CDC per server, app events."""

from __future__ import annotations

import time
import zlib

import numpy as np
import pandas as pd

from . import mt5
from .config import MT5_TABLES, WorkshopConfig
from .events import gen_events, write_events
from .mt5 import US_D, US_H, US_S
from .prices import PriceModel
from .reference import fx_rates_daily_df, ib_hierarchy_df, servers_df, symbols_csv_df
from .storage import dms_cdc_name, save_state, write_csv, write_parquet

LOAD_CHUNK = 250_000
OPEN_COLS = ["Position", "Login", "Symbol", "Action", "lots", "Volume", "open_us", "close_us", "PriceOpen",
             "PriceSL", "PriceTP", "ContractSize", "RateOpen", "CommissionSide", "ReasonOpen", "ReasonClose",
             "_digits", "_quote", "_sign", "_spread", "_asset"]


def server_rng(seed: int, server: str) -> np.random.Generator:
    return np.random.default_rng(seed + zlib.crc32(server.encode()) % 100_000)


def write_table_files(cfg: WorkshopConfig, server: str, table: str, load: pd.DataFrame | None,
                      cdc: pd.DataFrame | None, t0_us: int, now_us: int) -> dict:
    """DMS layout: LOAD0000000N.parquet (Op=I, cdc_ts=T0) + one CDC file per hour bucket."""
    out_dir = cfg.mt5_dir(server, table)
    stats = {"load_rows": 0, "load_files": 0, "cdc_rows": 0, "cdc_files": 0}
    if load is not None and len(load):
        load = load.copy()
        load["Op"], load["cdc_ts"] = "I", t0_us
        for i, start in enumerate(range(0, len(load), LOAD_CHUNK), start=1):
            write_parquet(mt5.to_arrow(load.iloc[start:start + LOAD_CHUNK], table), f"{out_dir}/LOAD{i:08d}.parquet")
            stats["load_files"] += 1
        stats["load_rows"] = len(load)
    if cdc is not None and len(cdc):
        cdc = cdc.sort_values("cdc_ts", kind="stable")
        bucket = (cdc["cdc_ts"].to_numpy() - t0_us) // US_H
        for b in np.unique(bucket):
            part = cdc[bucket == b]
            name_us = min(t0_us + int(b + 1) * US_H, now_us)
            write_parquet(mt5.to_arrow(part, table), f"{out_dir}/{dms_cdc_name(name_us)}")
            stats["cdc_files"] += 1
        stats["cdc_rows"] = len(cdc)
    return stats


def build_server(cfg: WorkshopConfig, server: str, prices: PriceModel, hist_start: int, t0: int, now: int,
                 log=print) -> tuple[dict, dict]:
    rng = server_rng(cfg.seed, server)
    users = mt5.gen_users(rng, server, cfg.users_per_server, hist_start, t0, start_seq=1, recent_share=0.25)
    window_days = (now - t0) / US_D
    new = mt5.gen_users(rng, server, max(1, int(rng.poisson(10 * window_days))), t0, now,
                        start_seq=len(users) + 1, recent_share=1.0, recent_from_us=t0)
    new["Status"] = np.where(rng.random(len(new)) < 0.7, "PENDING_KYC", "ACTIVE")
    new["LastAccess"] = new["Registration"]

    pos = mt5.gen_positions(rng, server, users, hist_start, now, cfg.positions_per_server_per_day, prices, 1)
    trades = mt5.deals_from_positions(rng, pos, now)
    balance = mt5.gen_balance_deals(rng, pd.concat([users, new], ignore_index=True), hist_start, now)
    deals = mt5.finalize_deals(rng, pd.concat([trades, balance], ignore_index=True), server, 1, 0.002, now)

    # ---- deals: full load = arrived before T0; CDC = inserts in window + corrections + deletes
    arrival = deals["arrival_us"].to_numpy()
    deals_load = deals[arrival < t0]
    ins = deals[(arrival >= t0) & (arrival < now)].copy()
    ins["Op"], ins["cdc_ts"] = "I", ins["arrival_us"]
    cand = deals[(deals["Entry"] == 1) & (arrival >= t0 - US_D) & (arrival < now - 2 * US_H)]
    corr = cand.sample(n=max(1, int(len(cand) * 0.01)), random_state=int(rng.integers(1 << 31))).copy()
    corr["cdc_ts"] = np.clip(corr["arrival_us"].to_numpy() + rng.integers(US_H, 30 * US_H, size=len(corr)),
                             t0 + 60 * US_S, now - 60 * US_S)
    corr["Profit"] = np.round(corr["Profit"].to_numpy() * rng.uniform(0.8, 1.0, size=len(corr)), 2)
    corr["Comment"] = (corr["Comment"].fillna("") + " [adj]").str.strip()
    corr["Dealer"], corr["Op"] = 9100, "U"
    rest = cand.drop(index=corr.index)
    dele = rest.sample(n=max(1, int(len(cand) * 0.001)), random_state=int(rng.integers(1 << 31))).copy()
    dele["cdc_ts"] = np.clip(dele["arrival_us"].to_numpy() + rng.integers(US_H, 12 * US_H, size=len(dele)),
                             t0 + 60 * US_S, now - 60 * US_S)
    dele["Op"] = "D"
    deals_cdc = pd.concat([ins, corr, dele], ignore_index=True)

    # ---- users: full load as of T0, then U/D after-images + new registrations
    change_rows, users_final = mt5.user_change_rows(rng, users, t0, now, server)
    new_i = mt5.users_frame(new, "I")
    new_i["cdc_ts"] = new["Registration"].to_numpy() + 5 * US_S
    kyc = new[(new["Status"] == "PENDING_KYC") & (rng.random(len(new)) < 0.5)].copy()
    kyc_t = kyc["Registration"].to_numpy() + rng.integers(2 * US_H, 30 * US_H, size=len(kyc))
    kyc, kyc_t = kyc[kyc_t < now], kyc_t[kyc_t < now]
    kyc_u = mt5.users_frame(kyc.assign(Status="ACTIVE"), "U")
    kyc_u["cdc_ts"] = kyc_t
    new_final = new.copy()
    new_final.loc[kyc.index, "Status"] = "ACTIVE"
    users_cdc = pd.concat([pd.DataFrame(change_rows), new_i, kyc_u], ignore_index=True)

    # ---- positions: snapshot at T0, then I (open) / U (every 4h) / D (close) in the window
    open_t0 = pos[(pos["open_us"] < t0) & (pos["close_us"] >= t0)]
    px, pnl, rate = mt5.position_mark(open_t0, np.full(len(open_t0), t0), prices)
    nights = np.clip((t0 - 21 * US_H) // US_D - (open_t0["open_us"].to_numpy() - 21 * US_H) // US_D, 0, None)
    swap_rate = np.array([mt5.SWAP_PER_LOT_NIGHT[a] for a in open_t0["_asset"]])
    pos_load = mt5.positions_frame(open_t0, "I", t0, t0, px, pnl, rate, -np.round(swap_rate * open_t0["lots"].to_numpy() * nights, 2))

    opened = pos[(pos["open_us"] >= t0) & (pos["open_us"] < now)]
    lag = rng.integers(1, 30, size=len(opened)) * US_S
    p_i = mt5.positions_frame(opened, "I", opened["open_us"].to_numpy() + lag, opened["open_us"].to_numpy(),
                              opened["PriceOpen"].to_numpy(), 0.0, opened["RateOpen"].to_numpy(), 0.0)
    live = pos[(pos["open_us"] < now) & (pos["close_us"] > t0)]
    k0 = -(-np.maximum(live["open_us"].to_numpy(), t0) // (4 * US_H))
    k1 = (np.minimum(live["close_us"].to_numpy(), now) - 1) // (4 * US_H)
    cnt = np.clip(k1 - k0 + 1, 0, None)
    rep = live.loc[live.index.repeat(cnt)]
    ts = np.concatenate([np.arange(a, b + 1) for a, b, c in zip(k0, k1, cnt) if c > 0]) * 4 * US_H if cnt.sum() else np.array([], dtype=np.int64)
    upx, upnl, urate = mt5.position_mark(rep, ts, prices) if len(rep) else (np.array([]),) * 3
    p_u = mt5.positions_frame(rep, "U", ts + rng.integers(1, 30, size=len(ts)) * US_S, ts, upx, upnl, urate)
    closed = pos[(pos["close_us"] >= t0) & (pos["close_us"] < now)]
    p_d = mt5.positions_frame(closed, "D", closed["close_us"].to_numpy() + rng.integers(1, 30, size=len(closed)) * US_S,
                              closed["close_us"].to_numpy(), closed["PriceClose"].to_numpy(),
                              closed["Profit"].to_numpy(), closed["RateClose"].to_numpy())
    pos_cdc = pd.concat([p_i, p_u, p_d], ignore_index=True)

    stats = {
        "mt5_users": write_table_files(cfg, server, "mt5_users", mt5.users_frame(users), users_cdc, t0, now),
        "mt5_deals": write_table_files(cfg, server, "mt5_deals", deals_load, deals_cdc, t0, now),
        "mt5_positions": write_table_files(cfg, server, "mt5_positions", pos_load, pos_cdc, t0, now),
    }
    log(f"  {server}: users={len(users)}+{len(new)} positions={len(pos)} deals={len(deals)} "
        f"(load {len(deals_load)}, cdc {len(deals_cdc)}: {len(corr)} corrections, {len(dele)} deletes)")

    state_users = pd.concat([users_final, new_final], ignore_index=True)
    open_now = pos[(pos["open_us"] < now) & (pos["close_us"] >= now)][OPEN_COLS].reset_index(drop=True)
    counters = {
        "next_deal": int(deals["Deal"].max()) + 1,
        "next_position": int(pos["Position"].max()) + 1,
        "next_login": int(state_users["Login"].max()) + 1,
    }
    return {"stats": stats, "counters": counters}, {f"users_{server}": state_users, f"open_{server}": open_now}


def build_all(cfg: WorkshopConfig, now_us: int | None = None, log=print) -> dict:
    t_start = time.time()
    now = now_us or int(time.time() // 60 * 60) * US_S
    t0 = now - cfg.cdc_window_hours * US_H
    hist_start = t0 - cfg.history_days * US_D
    prices = PriceModel(hist_start - US_D, now + US_D, cfg.seed)

    log("Reference data ...")
    write_csv(symbols_csv_df(), f"{cfg.ref_root}/symbols/symbols.csv")
    write_csv(ib_hierarchy_df(42), f"{cfg.ref_root}/ib_hierarchy/ib_hierarchy.csv")
    write_csv(servers_df(), f"{cfg.ref_root}/servers/servers.csv")
    write_csv(fx_rates_daily_df(prices, pd.Timestamp(hist_start, unit="us", tz="UTC"),
                                pd.Timestamp(now, unit="us", tz="UTC")), f"{cfg.ref_root}/fx_rates/fx_rates_daily.csv")

    log("MT5 servers ...")
    manifest = {"now_us": now, "t0_us": t0, "hist_start_us": hist_start, "servers": {}}
    frames: dict[str, pd.DataFrame] = {}
    users_by_server = {}
    for server in cfg.servers:
        info, fr = build_server(cfg, server, prices, hist_start, t0, now, log)
        manifest["servers"][server] = info
        frames.update(fr)
        users_by_server[server] = fr[f"users_{server}"]

    log("App events ...")
    ev_rng = np.random.default_rng(cfg.seed + 99)
    ev_start = now - cfg.event_days * US_D
    events = gen_events(ev_rng, users_by_server, ev_start, now, cfg.event_days * cfg.events_per_day,
                        drift_from_us=now - 2 * US_D, mismatch_from_us=now - US_D)
    manifest["app_events"] = {"events": len(events), "files": write_events(events, cfg.events_dir)}

    state = {
        "created_at_us": now, "last_tick_us": now, "seed": cfg.seed,
        "prices": {s: float(prices.price_at(s, np.array([now]))[0]) for s in prices.paths},
        "servers": {s: manifest["servers"][s]["counters"] for s in cfg.servers},
        "frames": sorted(frames),
    }
    save_state(state, cfg.producer_root, frames)
    manifest["seconds"] = round(time.time() - t_start, 1)
    log(f"Done in {manifest['seconds']}s")
    return manifest


def landing_tables() -> tuple[str, ...]:
    return MT5_TABLES
