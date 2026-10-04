"""滴灌程序 (drip producer): 在讲习班期间保持落地区 (landing zone) 活跃。
每 ``interval_seconds`` 为每个服务器的每个 MT5 表写入一个 DMS 风格的 CDC 文件
(新成交、平仓、持仓标记、入出金、客户更新) 加上一个应用事件 JSON 文件。
还可以登录全新的服务器 (先全量，然后 CDC) 并注入"坏批次"。
Drip producer: keeps the landing zone alive during the labs.

Every ``interval_seconds`` it writes one DMS-style CDC file per MT5 table per server (new trades,
closes, position marks, deposits/withdrawals, client updates) plus one app-events JSON file.
It can also onboard a brand-new server (full load first, then CDC) and inject a "bad batch".
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import mt5
from .config import SERVER_META, WorkshopConfig
from .events import gen_events
from .history import OPEN_COLS, server_rng, write_table_files
from .mt5 import US_D, US_H, US_S
from .prices import LivePrices, PriceModel
from .reference import symbols_df
from .storage import dms_cdc_name, load_state, save_state, write_parquet, write_text


def _now_us() -> int:
    """获取当前时间的微秒表示。
    Get current time in microseconds."""
    return int(time.time() * 1_000_000)


def onboard_server(cfg: WorkshopConfig, state: dict, frames: dict, server: str, now: int, live: LivePrices,
                   log=print) -> None:
    """新服务器的 DMS 全量: 7 天历史记录，以 LOAD 文件形式写入在 ``now``。
    DMS full load for a new server: 7 days of history, written as LOAD files at ``now``."""
    rng = server_rng(cfg.seed, server)
    pm = PriceModel(now - 8 * US_D, now + US_D, cfg.seed + 5).rescale_to(live.px, now)
    users = mt5.gen_users(rng, server, 300, now - 7 * US_D, now - US_H, start_seq=1, recent_share=0.4)
    pos = mt5.gen_positions(rng, server, users, now - 7 * US_D, now, 250, pm, 1)
    trades = mt5.deals_from_positions(rng, pos, now)
    bal = mt5.gen_balance_deals(rng, users, now - 7 * US_D, now)
    deals = mt5.finalize_deals(rng, pd.concat([trades, bal], ignore_index=True), server, 1, 0.002, now)
    open_now = pos[(pos["open_us"] < now) & (pos["close_us"] >= now)]
    px, pnl, rate = mt5.position_mark(open_now, np.full(len(open_now), now), pm)
    write_table_files(cfg, server, "mt5_users", mt5.users_frame(users), None, now, now)
    write_table_files(cfg, server, "mt5_deals", deals, None, now, now)
    write_table_files(cfg, server, "mt5_positions", mt5.positions_frame(open_now, "I", now, now, px, pnl, rate),
                      None, now, now)
    state["servers"][server] = {
        "next_deal": int(deals["Deal"].max()) + 1,
        "next_position": int(pos["Position"].max()) + 1,
        "next_login": int(users["Login"].max()) + 1,
    }
    frames[f"users_{server}"] = users
    frames[f"open_{server}"] = open_now[OPEN_COLS].reset_index(drop=True)
    state["frames"] = sorted(frames)
    log(f"  onboarded {server}: {len(users)} users, {len(deals)} deals, {len(open_now)} open positions (full load)")


def _new_positions(rng, users: pd.DataFrame, k: int, t_from: int, t_to: int, live: LivePrices,
                   next_pos: int) -> pd.DataFrame:
    """生成新开仓的持仓数据。
    Generate position data for newly opened trades."""
    sym = symbols_df().set_index("symbol")
    act = users[users["Status"] == "ACTIVE"]
    if k == 0 or act.empty:
        return pd.DataFrame(columns=OPEN_COLS)
    w = act["_activity"].to_numpy()
    pick = act.iloc[rng.choice(len(act), size=k, p=w / w.sum())]
    names = sym.index.to_numpy()
    pop = sym["popularity"].to_numpy(dtype=float)
    symbol = names[rng.choice(len(names), size=k, p=pop / pop.sum())]
    s = sym.loc[symbol]
    acct = pick["_acct"].to_numpy()
    spread = s["spread"].to_numpy() * np.array([mt5.SPREAD_MULT[a] for a in acct])
    lots = np.clip(np.round(rng.lognormal(np.log(s["lot_median"].to_numpy()), 0.9), 2), 0.01, 50.0)
    action = (rng.random(k) >= 0.55).astype(np.int32)
    sign = np.where(action == 0, 1.0, -1.0)
    digits = s["digits"].to_numpy()
    mid = np.array([live.price(x) for x in symbol])
    open_px = mt5.round_to(mid + sign * spread / 2, digits)
    open_us = np.sort(rng.integers(t_from, t_to, size=k))
    comp = rng.choice(3, size=k, p=[0.45, 0.40, 0.15])
    dur = ((rng.exponential(np.array([300, 7200, 172_800])[comp]) + 5) * US_S).astype(np.int64)
    fx_or_metal = np.isin(s["asset_class"].to_numpy(), ["FX_MAJOR", "FX_CROSS", "FX_EXOTIC", "METAL"])
    comm = np.where(fx_or_metal, np.array([mt5.COMMISSION_PER_LOT[a] for a in acct]) * lots, 0.0)
    has_sl = rng.random(k) < 0.40
    has_tp = rng.random(k) < 0.35
    return pd.DataFrame({
        "Position": next_pos + np.arange(k, dtype=np.int64), "Login": pick["Login"].to_numpy(), "Symbol": symbol,
        "Action": action, "lots": lots, "Volume": np.round(lots * 10_000).astype(np.int64), "open_us": open_us,
        "close_us": open_us + dur, "PriceOpen": open_px,
        "PriceSL": np.where(has_sl, mt5.round_to(open_px * (1 - sign * rng.uniform(0.003, 0.02, size=k)), digits), 0.0),
        "PriceTP": np.where(has_tp, mt5.round_to(open_px * (1 + sign * rng.uniform(0.003, 0.03, size=k)), digits), 0.0),
        "ContractSize": s["contract_size"].to_numpy(dtype=float),
        "RateOpen": np.array([live.usd_per_quote(q) for q in s["quote_ccy"]]),
        "CommissionSide": -np.round(comm, 2), "ReasonOpen": rng.choice([0, 1, 2, 3], size=k, p=[0.3, 0.5, 0.15, 0.05]),
        "ReasonClose": rng.choice([0, 1, 2, 3, 4, 5, 6], size=k, p=[0.27, 0.45, 0.13, 0.045, 0.04, 0.06, 0.005]),
        "_digits": digits, "_quote": s["quote_ccy"].to_numpy(), "_sign": sign, "_spread": spread,
        "_asset": s["asset_class"].to_numpy(),
    })


def _mark_live(pos: pd.DataFrame, live: LivePrices) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """使用实时价格为持仓标记市值。
    Mark-to-market positions using live prices."""
    mid = np.array([live.price(x) for x in pos["Symbol"]])
    px = mt5.round_to(mid - pos["_sign"].to_numpy() * pos["_spread"].to_numpy() / 2, pos["_digits"].to_numpy())
    rate = np.array([live.usd_per_quote(q) for q in pos["_quote"]])
    pnl = np.round(pos["_sign"].to_numpy() * (px - pos["PriceOpen"].to_numpy()) * pos["lots"].to_numpy()
                   * pos["ContractSize"].to_numpy() * rate, 2)
    return px, pnl, rate


def tick_server(cfg: WorkshopConfig, state: dict, frames: dict, server: str, t_from: int, now: int,
                live: LivePrices, rng, deals_per_tick: int, bad_pct: float) -> dict:
    """在一个时间步长内为单个服务器生成新数据。
    Generate new data for single server at one time step."""
    ctr = state["servers"][server]
    users = frames[f"users_{server}"]
    open_pos = frames[f"open_{server}"]

    new = _new_positions(rng, users, int(rng.poisson(deals_per_tick / 2)), t_from, now, live, ctr["next_position"])
    ctr["next_position"] += len(new)
    due = open_pos[open_pos["close_us"] <= now]
    keep = open_pos[open_pos["close_us"] > now]

    # 持仓 CDC: I (开仓) · U (5% 重新标记) · D (平仓)
    # positions CDC: I (opened) · U (5% re-marked) · D (closed)
    rows = []
    if len(new):
        rows.append(mt5.positions_frame(new, "I", new["open_us"].to_numpy() + 2 * US_S, new["open_us"].to_numpy(),
                                        new["PriceOpen"].to_numpy(), 0.0, new["RateOpen"].to_numpy(), 0.0))
    upd = keep.sample(frac=0.05, random_state=int(rng.integers(1 << 31))) if len(keep) else keep
    if len(upd):
        px, pnl, rate = _mark_live(upd, live)
        rows.append(mt5.positions_frame(upd, "U", now, now, px, pnl, rate, 0.0))
    deals = []
    if len(due):
        px, pnl, rate = _mark_live(due, live)
        close_us = np.maximum(due["close_us"].to_numpy(), t_from)
        nights = np.clip((close_us - 21 * US_H) // US_D - (due["open_us"].to_numpy() - 21 * US_H) // US_D, 0, None)
        swap = -np.round(np.array([mt5.SWAP_PER_LOT_NIGHT[a] for a in due["_asset"]]) * due["lots"].to_numpy() * nights, 2)
        rows.append(mt5.positions_frame(due, "D", close_us + 2 * US_S, close_us, px, pnl, rate, swap))
        rc = due["ReasonClose"].to_numpy()
        comment = [f"[sl {p:.{d}f}]" if r == 4 else f"[tp {p:.{d}f}]" if r == 5 else "" for r, p, d in
                   zip(rc, px, due["_digits"].to_numpy())]
        deals.append(pd.DataFrame({
            "Login": due["Login"], "Time": close_us, "Symbol": due["Symbol"], "Action": 1 - due["Action"], "Entry": 1,
            "Reason": rc, "Volume": due["Volume"], "Price": px, "ContractSize": due["ContractSize"],
            "RateProfit": np.round(rate, 6), "Profit": pnl, "Storage": swap, "Commission": due["CommissionSide"],
            "PositionID": due["Position"], "Comment": comment}))
    if len(new):
        deals.append(pd.DataFrame({
            "Login": new["Login"], "Time": new["open_us"], "Symbol": new["Symbol"], "Action": new["Action"],
            "Entry": 0, "Reason": new["ReasonOpen"], "Volume": new["Volume"], "Price": new["PriceOpen"],
            "ContractSize": new["ContractSize"], "RateProfit": np.round(new["RateOpen"], 6), "Profit": 0.0,
            "Storage": 0.0, "Commission": new["CommissionSide"], "PositionID": new["Position"], "Comment": ""}))
    for kind, lam in (("dep", 0.6), ("wd", 0.25)):
        act = users[users["Status"] == "ACTIVE"]
        for _ in range(int(rng.poisson(lam))):
            u = act.iloc[int(rng.integers(len(act)))]
            amt = float(rng.lognormal(np.log(500 if kind == "dep" else 400), 1.0))
            deals.append(pd.DataFrame([mt5._balance_row(rng, u, int(rng.integers(t_from, now)), amt, kind)]))

    out = {"mt5_positions": pd.concat(rows, ignore_index=True) if rows else None}
    if deals:
        d = pd.concat(deals, ignore_index=True).sort_values("Time", kind="stable").reset_index(drop=True)
        d["Deal"] = ctr["next_deal"] + np.arange(len(d), dtype=np.int64)
        ctr["next_deal"] += len(d)
        d["Order"] = np.where(d["Action"] == 2, 0, d["Deal"] + 100_000_000)
        d["Fee"], d["Dealer"] = 0.0, np.where(d["Action"] == 2, 9001, 0)
        trade = np.flatnonzero(d["Action"].to_numpy() != 2)
        n_bad = int(round(len(trade) * bad_pct)) if bad_pct > 0 else int(rng.random() < 0.05)
        if n_bad and len(trade):
            bad = rng.choice(trade, size=min(n_bad, len(trade)), replace=False)
            kind = rng.choice(3, size=len(bad))
            d.loc[bad[kind == 0], "Volume"] = 0
            d.loc[bad[kind == 1], "Price"] = -d.loc[bad[kind == 1], "Price"].abs()
            d.loc[bad[kind == 2], "Symbol"] = None
        d["TimeMsc"] = d["Time"] // 1000
        d["Op"], d["cdc_ts"] = "I", np.maximum(d["Time"].to_numpy(), t_from) + 2 * US_S
        out["mt5_deals"] = d

    # 用户 CDC: 少量登录 (LastAccess)、偶发杠杆变化、偶发新注册
    # users CDC: a few logins (LastAccess), occasional leverage change, occasional new registration
    urows = []
    for _ in range(int(rng.poisson(0.6))):
        i = int(rng.integers(len(users)))
        users.loc[users.index[i], "LastAccess"] = now
        if rng.random() < 0.15:
            users.loc[users.index[i], "Leverage"] = int(rng.choice([100, 200, 500]))
        urows.append(mt5.users_frame(users.iloc[[i]], "U", now))
    if rng.random() < 0.1:
        reg = mt5.gen_users(rng, server, 1, t_from, now, start_seq=ctr["next_login"] - SERVER_META[server]["login_base"],
                            recent_share=1.0, recent_from_us=t_from)
        reg["Status"], reg["LastAccess"] = "PENDING_KYC", reg["Registration"]
        ctr["next_login"] += 1
        users = pd.concat([users, reg], ignore_index=True)
        urows.append(mt5.users_frame(reg, "I", now))
    out["mt5_users"] = pd.concat(urows, ignore_index=True) if urows else None

    frames[f"users_{server}"] = users
    frames[f"open_{server}"] = pd.concat([keep, new[OPEN_COLS]], ignore_index=True) if len(new) else keep.reset_index(drop=True)
    counts = {}
    for table, df in out.items():
        if df is not None and len(df):
            write_parquet(mt5.to_arrow(df, table), f"{cfg.mt5_dir(server, table)}/{dms_cdc_name(now)}")
            counts[table] = len(df)
    return counts


def run_drip(cfg: WorkshopConfig, duration_minutes: float = 60, interval_seconds: float = 30,
             servers: list[str] | None = None, new_server: str | None = None, bad_batch_pct: float = 0.0,
             deals_per_tick: int = 24, events_per_tick: int = 150, max_ticks: int | None = None, log=print) -> dict:
    """运行滴灌程序: 持续生成并写入 CDC 和事件数据。
    Run drip producer: continuously generate and write CDC and event data."""
    state, frames = load_state(cfg.producer_root)
    live = LivePrices(state["prices"], seed=int(time.time()))
    rng = np.random.default_rng(int(time.time() * 1000) % (1 << 31))
    now = _now_us()
    if new_server and new_server not in state["servers"]:
        onboard_server(cfg, state, frames, new_server, now, live, log)
    active = [s for s in (servers or list(state["servers"])) if s in state["servers"]]
    if new_server and new_server not in active:
        active.append(new_server)
    n_ticks = max_ticks if max_ticks is not None else max(1, int(duration_minutes * 60 // interval_seconds))
    totals: dict[str, int] = {}
    last = state.get("last_tick_us", now)
    for tick in range(n_ticks):
        started = time.time()
        now = _now_us()
        t_from = max(last, now - int(interval_seconds * US_S))
        live.step((now - last) / US_S)
        for s in active:
            for table, c in tick_server(cfg, state, frames, s, t_from, now, live, rng, deals_per_tick, bad_batch_pct).items():
                totals[table] = totals.get(table, 0) + c
        users_by_server = {s: frames[f"users_{s}"] for s in active}
        evs = gen_events(rng, users_by_server, t_from, now, events_per_tick, drift_from_us=0, mismatch_from_us=0)
        dt = datetime.fromtimestamp(now / 1e6, tz=timezone.utc)
        write_text("\n".join(json.dumps(e, ensure_ascii=False) for _, e in evs) + "\n",
                   f"{cfg.events_dir}/{dt:%Y-%m-%d}/events-{dt:%Y%m%d-%H%M%S}.json")
        totals["app_events"] = totals.get("app_events", 0) + len(evs)
        state["prices"], state["last_tick_us"], last = dict(live.px), now, now
        save_state(state, cfg.producer_root, frames)
        log(f"tick {tick + 1}/{n_ticks} {dt:%H:%M:%S} servers={len(active)} totals={totals}")
        if tick < n_ticks - 1:
            time.sleep(max(0.0, interval_seconds - (time.time() - started)))
    return {"ticks": n_ticks, "servers": active, "rows": totals}
