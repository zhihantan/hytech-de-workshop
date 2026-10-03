"""Synthetic MT5 report-database tables (mt5_users, mt5_deals, mt5_positions).

Column names follow the MT5 report tables (PascalCase). Files are laid out like AWS DMS
writes them to S3: a full load (``LOAD00000001.parquet``) plus timestamped CDC files
(``yyyymmdd-hhmmssfff.parquet``) with an ``Op`` column (I/U/D) and a ``cdc_ts`` commit
timestamp. All internal timestamps are int64 microseconds (UTC).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pyarrow as pa

from .config import SERVER_META
from .people import LEVERAGE_CAP, fake_identities
from .reference import ib_hierarchy_df, symbols_df

US_S = 1_000_000
US_H = 3600 * US_S
US_D = 24 * US_H

TS = pa.timestamp("us", tz="UTC")
USERS_SCHEMA = pa.schema([
    ("Op", pa.string()), ("cdc_ts", TS), ("Login", pa.int64()), ("Group", pa.string()),
    ("Registration", TS), ("LastAccess", TS), ("FirstName", pa.string()), ("LastName", pa.string()),
    ("Country", pa.string()), ("Language", pa.string()), ("Phone", pa.string()), ("Email", pa.string()),
    ("Status", pa.string()), ("Leverage", pa.int32()), ("Agent", pa.int64()), ("Comment", pa.string()),
])
DEALS_SCHEMA = pa.schema([
    ("Op", pa.string()), ("cdc_ts", TS), ("Deal", pa.int64()), ("Login", pa.int64()), ("Order", pa.int64()),
    ("Time", TS), ("TimeMsc", pa.int64()), ("Symbol", pa.string()), ("Action", pa.int32()), ("Entry", pa.int32()),
    ("Reason", pa.int32()), ("Volume", pa.int64()), ("Price", pa.float64()), ("ContractSize", pa.float64()),
    ("RateProfit", pa.float64()), ("Profit", pa.float64()), ("Storage", pa.float64()), ("Commission", pa.float64()),
    ("Fee", pa.float64()), ("PositionID", pa.int64()), ("Dealer", pa.int64()), ("Comment", pa.string()),
])
POSITIONS_SCHEMA = pa.schema([
    ("Op", pa.string()), ("cdc_ts", TS), ("Position", pa.int64()), ("Login", pa.int64()), ("Symbol", pa.string()),
    ("Action", pa.int32()), ("Volume", pa.int64()), ("PriceOpen", pa.float64()), ("PriceCurrent", pa.float64()),
    ("PriceSL", pa.float64()), ("PriceTP", pa.float64()), ("Profit", pa.float64()), ("Storage", pa.float64()),
    ("ContractSize", pa.float64()), ("RateProfit", pa.float64()), ("TimeCreate", TS), ("TimeUpdate", TS),
    ("Reason", pa.int32()), ("Comment", pa.string()),
])
SCHEMAS = {"mt5_users": USERS_SCHEMA, "mt5_deals": DEALS_SCHEMA, "mt5_positions": POSITIONS_SCHEMA}

ACCT_TYPES = np.array(["STD", "RAW", "PRO"])
ACCT_P = np.array([0.6, 0.3, 0.1])
SPREAD_MULT = {"STD": 1.5, "RAW": 1.0, "PRO": 1.0}
COMMISSION_PER_LOT = {"STD": 0.0, "RAW": 3.5, "PRO": 2.0}
SWAP_PER_LOT_NIGHT = {"FX_MAJOR": 0.6, "FX_CROSS": 0.8, "FX_EXOTIC": 1.5, "METAL": 2.5, "ENERGY": 1.0,
                      "INDEX": 0.8, "CRYPTO": 15.0}
LEVERAGES = np.array([25, 30, 50, 100, 200, 500, 1000])
HOUR_W = np.array([0.4 + 0.8 * (h < 9) + 1.0 * (7 <= h < 17) + 0.9 * (13 <= h < 21) for h in range(24)])
HOUR_W = HOUR_W / HOUR_W.sum()

DEPOSIT_METHODS = [
    # key, weight, english, chinese
    ("crypto", 0.22, "Deposit USDT-TRC20 #{ref}", "入金 USDT-TRC20 #{ref}"),
    ("crypto", 0.06, "Deposit USDT-ERC20 #{ref}", "入金 USDT-ERC20 #{ref}"),
    ("crypto", 0.03, "Deposit BTC #{ref}", "入金 比特币 #{ref}"),
    ("card", 0.12, "Deposit Visa ****{last4}", "信用卡入金 Visa ****{last4}"),
    ("card", 0.08, "Deposit Mastercard ****{last4}", "信用卡入金 Mastercard ****{last4}"),
    ("bank_transfer", 0.14, "Deposit Bank Wire Ref {ref}", "电汇入金 参考号 {ref}"),
    ("bank_transfer", 0.15, "Deposit Local Bank Transfer ({country}) {ref}", "本地银行转账入金 ({country}) {ref}"),
    ("e_wallet", 0.05, "Deposit Skrill {ref}", "电子钱包入金 Skrill {ref}"),
    ("e_wallet", 0.04, "Deposit Neteller {ref}", "电子钱包入金 Neteller {ref}"),
    ("e_wallet", 0.04, "Deposit FasaPay {ref}", "电子钱包入金 FasaPay {ref}"),
    ("card", 0.04, "Deposit UnionPay {ref}", "银联入金 {ref}"),
    ("internal_transfer", 0.03, "Transfer from {other}", "内部转账 来自 {other}"),
]
WITHDRAWAL_METHODS = [
    ("crypto", 0.34, "Withdrawal USDT-TRC20 to {wallet}", "出金 USDT-TRC20 至 {wallet}"),
    ("bank_transfer", 0.30, "Withdrawal Bank Wire Ref {ref}", "出金 银行电汇 {ref}"),
    ("bank_transfer", 0.18, "Withdrawal Local Bank Transfer ({country}) {ref}", "出金 本地银行转账 ({country}) {ref}"),
    ("e_wallet", 0.10, "Withdrawal Skrill {ref}", "出金 电子钱包 Skrill {ref}"),
    ("card", 0.05, "Withdrawal refund to Visa ****{last4}", "出金 退回 Visa ****{last4}"),
    ("internal_transfer", 0.03, "Transfer to {other}", "内部转账 转至 {other}"),
]
MESSY = {  # free-text variants that rule-based parsing struggles with (used in the AI Functions lab)
    "dep": ["dep usdt trc 20 {ref}", "crypto in {ref}", "DEP-CARD {last4}", "fund in via wire", "入金",
            "deposit (manual) {ref}"],
    "wd": ["wd bank {ref}", "W/D usdt {ref}", "出金 USDT", "withdraw - manual {ref}"],
}


def round_to(x, digits) -> np.ndarray:
    """Round each element to its own number of decimals (np.round only accepts a scalar)."""
    f = np.power(10.0, np.asarray(digits, dtype=float))
    return np.round(np.asarray(x, dtype=float) * f) / f


def weekday(ts_us: np.ndarray) -> np.ndarray:
    return ((ts_us // US_D) + 3) % 7  # Monday = 0; 1970-01-01 was a Thursday


def to_ts(us) -> pd.Series:
    return pd.to_datetime(np.asarray(us, dtype=np.int64), unit="us", utc=True)


# --------------------------------------------------------------------------- users
def gen_users(rng, server: str, n: int, reg_from_us: int, reg_to_us: int, start_seq: int,
              recent_share: float = 0.25, recent_from_us: int | None = None) -> pd.DataFrame:
    """Client accounts. Internal (non-MT5) columns are prefixed with ``_``."""
    meta = SERVER_META[server]
    countries = np.array(list(meta["countries"]))
    cw = np.array(list(meta["countries"].values()), dtype=float)
    country = countries[rng.choice(len(countries), size=n, p=cw / cw.sum())]
    ident = fake_identities(rng, country)
    brands = np.array(list(meta["brands"]))
    bw = np.array(list(meta["brands"].values()), dtype=float)
    brand = brands[rng.choice(len(brands), size=n, p=bw / bw.sum())]
    acct = ACCT_TYPES[rng.choice(3, size=n, p=ACCT_P)]
    group = np.array([f"real\\{b}\\{a}-USD" for b, a in zip(brand, acct)], dtype=object)
    cap = np.array([LEVERAGE_CAP.get(c, 1000) for c in country])
    lev = rng.choice([100, 200, 500, 1000], size=n, p=[0.25, 0.30, 0.30, 0.15])
    lev = np.where(lev > cap, cap, lev).astype(np.int32)

    ibs = ib_hierarchy_df(42)
    agent = np.zeros(n, dtype=np.int64)
    for b in np.unique(brand):
        pool = ibs[(ibs.brand == b) & (ibs.region == meta["region"])].ib_login.to_numpy()
        if len(pool) == 0:
            pool = ibs[ibs.brand == b].ib_login.to_numpy()
        m = (brand == b) & (rng.random(n) < 0.6)
        agent[m] = rng.choice(pool, size=m.sum())

    recent_from_us = reg_from_us if recent_from_us is None else recent_from_us
    old = rng.random(n) >= recent_share
    reg = np.where(
        old,
        rng.integers(reg_from_us - 3 * 365 * US_D, recent_from_us, size=n),
        rng.integers(recent_from_us, reg_to_us, size=n),
    ).astype(np.int64)
    status = rng.choice(["ACTIVE", "DORMANT", "PENDING_KYC", "DISABLED"], size=n, p=[0.78, 0.15, 0.05, 0.02])
    comment = rng.choice(["", "", "", "", "VIP", "IB referral", "migrated from MT4", "seminar lead"], size=n)
    df = pd.DataFrame({
        "Login": meta["login_base"] + start_seq + np.arange(n, dtype=np.int64),
        "Group": group, "Registration": reg, "LastAccess": reg + rng.integers(US_H, 30 * US_D, size=n),
        "FirstName": ident["FirstName"], "LastName": ident["LastName"], "Country": country,
        "Language": ident["Language"], "Phone": ident["Phone"], "Email": ident["Email"],
        "Status": status, "Leverage": lev, "Agent": agent, "Comment": comment,
        "_acct": acct, "_brand": brand, "_activity": rng.lognormal(0.0, 1.2, size=n),
    })
    df["LastAccess"] = np.minimum(df["LastAccess"].to_numpy(), reg_to_us)
    return df


# ----------------------------------------------------------------------- positions
def gen_positions(rng, server: str, users: pd.DataFrame, start_us: int, end_us: int, per_day: float,
                  prices, start_seq: int) -> pd.DataFrame:
    """Round-trip positions opened in [start_us, end_us). close_us may be beyond end_us (still open)."""
    sym = symbols_df().set_index("symbol")
    names = sym.index.to_numpy()
    pop = sym["popularity"].to_numpy(dtype=float)
    crypto = (sym["asset_class"] == "CRYPTO").to_numpy()

    day_starts = np.arange(start_us - start_us % US_D, end_us, US_D, dtype=np.int64)
    counts = np.array([rng.poisson(per_day * (1.0 if weekday(np.array([d]))[0] < 5 else 0.12)) for d in day_starts])
    day = np.repeat(day_starts, counts)
    n = len(day)
    hour = rng.choice(24, size=n, p=HOUR_W)
    open_us = day + hour * US_H + rng.integers(0, US_H, size=n)
    is_weekend = weekday(day) >= 5
    p_all = pop / pop.sum()
    p_crypto = np.where(crypto, pop, 0.0) / np.where(crypto, pop, 0.0).sum()
    symbol = np.where(is_weekend, names[rng.choice(len(names), size=n, p=p_crypto)],
                      names[rng.choice(len(names), size=n, p=p_all)])

    # pick traders registered before the trading day (ACTIVE >> DORMANT; PENDING/DISABLED never trade)
    w = users["_activity"].to_numpy() * users["Status"].map({"ACTIVE": 1.0, "DORMANT": 0.03}).fillna(0.0).to_numpy()
    reg = users["Registration"].to_numpy()
    login = np.empty(n, dtype=np.int64)
    acct = np.empty(n, dtype=object)
    u_login, u_acct = users["Login"].to_numpy(), users["_acct"].to_numpy()
    for d in np.unique(day):
        m = day == d
        elig = (reg < d) & (w > 0)
        p = np.where(elig, w, 0.0)
        idx = rng.choice(len(users), size=m.sum(), p=p / p.sum())
        login[m], acct[m] = u_login[idx], u_acct[idx]

    keep = open_us < end_us
    day, open_us, symbol, login, acct = day[keep], open_us[keep], symbol[keep], login[keep], acct[keep]
    n = len(open_us)
    order = np.argsort(open_us, kind="stable")
    open_us, symbol, login, acct = open_us[order], symbol[order], login[order], acct[order]

    comp = rng.choice(3, size=n, p=[0.35, 0.40, 0.25])
    dur = (rng.exponential(np.array([480, 10_800, 216_000])[comp]) + 5) * US_S
    close_us = open_us + dur.astype(np.int64)
    non_crypto = ~np.isin(symbol, names[crypto])
    wk = weekday(close_us)
    shift = non_crypto & (wk >= 5)
    monday = (close_us // US_D + (7 - wk)) * US_D
    close_us = np.where(shift, monday + rng.integers(5 * 60 * US_S, 2 * US_H, size=n), close_us)

    s = sym.loc[symbol]
    cs = s["contract_size"].to_numpy(dtype=float)
    digits = s["digits"].to_numpy()
    spread = s["spread"].to_numpy() * np.array([SPREAD_MULT[a] for a in acct])
    lots = np.clip(np.round(rng.lognormal(np.log(s["lot_median"].to_numpy()), 0.9), 2), 0.01, 50.0)
    mid_o = prices.prices_at(symbol, open_us)
    mid_c = prices.prices_at(symbol, close_us)
    # retail flow loses on average (~70% of CFD accounts lose money): 56% of trades end on the wrong side
    up = mid_c >= mid_o
    wrong = rng.random(n) < 0.56
    action = np.where(wrong, np.where(up, 1, 0), np.where(up, 0, 1)).astype(np.int32)  # 0 buy, 1 sell
    sign = np.where(action == 0, 1.0, -1.0)
    open_px = round_to(mid_o + sign * spread / 2, digits)
    close_px = round_to(mid_c - sign * spread / 2, digits)
    quote = s["quote_ccy"].to_numpy()
    rate_o = prices.usd_per_quote(quote, open_us)
    rate_c = prices.usd_per_quote(quote, close_us)
    profit = np.round(sign * (close_px - open_px) * lots * cs * rate_c, 2)
    fx_or_metal = np.isin(s["asset_class"].to_numpy(), ["FX_MAJOR", "FX_CROSS", "FX_EXOTIC", "METAL"])
    comm = np.where(fx_or_metal, np.array([COMMISSION_PER_LOT[a] for a in acct]) * lots, 0.0)
    nights = np.clip((close_us - 21 * US_H) // US_D - (open_us - 21 * US_H) // US_D, 0, None)
    swap = -np.round(np.array([SWAP_PER_LOT_NIGHT[c] for c in s["asset_class"]]) * lots * nights, 2)
    reason_open = rng.choice([0, 1, 2, 3], size=n, p=[0.30, 0.50, 0.15, 0.05]).astype(np.int32)
    reason_close = rng.choice([0, 1, 2, 3, 4, 5, 6], size=n, p=[0.27, 0.45, 0.13, 0.045, 0.04, 0.06, 0.005]).astype(np.int32)
    has_sl, has_tp = rng.random(n) < 0.40, rng.random(n) < 0.35
    sl = np.where(has_sl, round_to(open_px * (1 - sign * rng.uniform(0.003, 0.02, size=n)), digits), 0.0)
    tp = np.where(has_tp, round_to(open_px * (1 + sign * rng.uniform(0.003, 0.03, size=n)), digits), 0.0)

    return pd.DataFrame({
        "Position": SERVER_META[server]["position_base"] + start_seq + np.arange(n, dtype=np.int64),
        "Login": login, "Symbol": symbol, "Action": action, "lots": lots, "Volume": np.round(lots * 10_000).astype(np.int64),
        "open_us": open_us, "close_us": close_us, "PriceOpen": open_px, "PriceClose": close_px,
        "PriceSL": sl, "PriceTP": tp, "ContractSize": cs, "RateOpen": rate_o, "RateClose": rate_c,
        "Profit": profit, "CommissionSide": -np.round(comm, 2), "Storage": swap, "ReasonOpen": reason_open,
        "ReasonClose": reason_close, "_digits": digits, "_quote": quote, "_sign": sign, "_spread": spread,
        "_asset": s["asset_class"].to_numpy(),
    })


def position_mark(pos: pd.DataFrame, ts_us: np.ndarray, prices) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mark-to-market (PriceCurrent, Profit, RateProfit) for positions at timestamps."""
    mid = prices.prices_at(pos["Symbol"].to_numpy(), ts_us)
    px = round_to(mid - pos["_sign"].to_numpy() * pos["_spread"].to_numpy() / 2, pos["_digits"].to_numpy())
    rate = prices.usd_per_quote(pos["_quote"].to_numpy(), ts_us)
    pnl = np.round(pos["_sign"].to_numpy() * (px - pos["PriceOpen"].to_numpy()) * pos["lots"].to_numpy()
                   * pos["ContractSize"].to_numpy() * rate, 2)
    return px, pnl, rate


# ---------------------------------------------------------------------------- deals
def deals_from_positions(rng, pos: pd.DataFrame, horizon_us: int) -> pd.DataFrame:
    """IN deal at open, OUT deal at close (only if closed before the horizon)."""
    lag_in = rng.integers(1, 30, size=len(pos)) * US_S
    ins = pd.DataFrame({
        "Login": pos["Login"], "Time": pos["open_us"], "Symbol": pos["Symbol"], "Action": pos["Action"],
        "Entry": 0, "Reason": pos["ReasonOpen"], "Volume": pos["Volume"], "Price": pos["PriceOpen"],
        "ContractSize": pos["ContractSize"], "RateProfit": np.round(pos["RateOpen"], 6), "Profit": 0.0,
        "Storage": 0.0, "Commission": pos["CommissionSide"], "PositionID": pos["Position"], "Comment": "",
        "arrival_us": pos["open_us"] + lag_in,
    })
    closed = pos[pos["close_us"] < horizon_us]
    rc = closed["ReasonClose"].to_numpy()
    px = closed["PriceClose"].to_numpy()
    dg = closed["_digits"].to_numpy()
    comment = np.array([
        f"[sl {p:.{d}f}]" if r == 4 else f"[tp {p:.{d}f}]" if r == 5 else
        f"[so {rng.uniform(20, 50):.2f}%/{rng.uniform(100, 900):.2f}/{rng.uniform(1000, 5000):.2f}]" if r == 6 else ""
        for r, p, d in zip(rc, px, dg)
    ], dtype=object)
    outs = pd.DataFrame({
        "Login": closed["Login"], "Time": closed["close_us"], "Symbol": closed["Symbol"],
        "Action": 1 - closed["Action"], "Entry": 1, "Reason": closed["ReasonClose"], "Volume": closed["Volume"],
        "Price": closed["PriceClose"], "ContractSize": closed["ContractSize"],
        "RateProfit": np.round(closed["RateClose"], 6), "Profit": closed["Profit"], "Storage": closed["Storage"],
        "Commission": closed["CommissionSide"], "PositionID": closed["Position"], "Comment": comment,
        "arrival_us": closed["close_us"] + rng.integers(1, 30, size=len(closed)) * US_S,
    })
    return pd.concat([ins, outs], ignore_index=True)


def _funding_comment(rng, methods, lang, country, ref, last4, other, wallet, kind="dep"):
    keys = np.array([m[0] for m in methods])
    w = np.array([m[1] for m in methods])
    i = rng.choice(len(methods), p=w / w.sum())
    if rng.random() < 0.06:
        tpl = MESSY[kind][rng.integers(len(MESSY[kind]))]
    elif lang == "zh" and rng.random() < 0.35:
        tpl = methods[i][3]
    else:
        tpl = methods[i][2]
    return keys[i], tpl.format(ref=ref, last4=last4, other=other, wallet=wallet, country=country)


def gen_balance_deals(rng, users: pd.DataFrame, start_us: int, end_us: int) -> pd.DataFrame:
    """Deposits / withdrawals (MT5 balance deals, Action=2) incl. first-time deposits (FTD)."""
    rows = []
    act = users[users["Status"] == "ACTIVE"]
    lw = np.sqrt(act["_activity"].to_numpy())
    for d in np.arange(start_us - start_us % US_D, end_us, US_D, dtype=np.int64):
        elig = act[act["Registration"].to_numpy() < d]
        if elig.empty:
            continue
        p = lw[act["Registration"].to_numpy() < d]
        p = p / p.sum()
        for kind, rate in (("dep", 0.025), ("wd", 0.012)):
            k = rng.poisson(rate * len(elig))
            if k == 0:
                continue
            pick = elig.iloc[rng.choice(len(elig), size=k, p=p)]
            t = d + rng.choice(24, size=k, p=HOUR_W) * US_H + rng.integers(0, US_H, size=k)
            amt = rng.lognormal(np.log(500 if kind == "dep" else 400), 1.0, size=k)
            for (_, u), ti, a in zip(pick.iterrows(), t, amt):
                rows.append(_balance_row(rng, u, int(ti), float(a), kind))
    recent = users[(users["Registration"] >= start_us) & (users["Status"] != "DISABLED")]
    for _, u in recent.iterrows():
        if rng.random() < 0.85:
            t = int(u["Registration"] + rng.integers(10 * 60 * US_S, 72 * US_H))
            rows.append(_balance_row(rng, u, t, float(rng.lognormal(np.log(300), 0.9)), "dep", ftd=True))
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df[df["Time"] < end_us].reset_index(drop=True)


def _balance_row(rng, u, t_us: int, amount: float, kind: str, ftd: bool = False) -> dict:
    ref = f"{rng.integers(10**7, 10**8):d}"
    last4 = f"{rng.integers(1000, 9999):d}"
    other = int(u["Login"]) + int(rng.integers(1, 500))
    wallet = f"T{rng.integers(10**9, 10**10):d}...{rng.integers(100, 999):d}"
    methods = DEPOSIT_METHODS if kind == "dep" else WITHDRAWAL_METHODS
    _, comment = _funding_comment(rng, methods, u["Language"], u["Country"], ref, last4, other, wallet, kind)
    if ftd and rng.random() < 0.5:
        comment = f"{comment} FTD"
    amount = round(min(max(amount, 20.0), 50_000.0), 2)
    return {
        "Login": int(u["Login"]), "Time": t_us, "Symbol": "", "Action": 2, "Entry": 0, "Reason": 0, "Volume": 0,
        "Price": 0.0, "ContractSize": 0.0, "RateProfit": 1.0, "Profit": amount if kind == "dep" else -amount,
        "Storage": 0.0, "Commission": 0.0, "PositionID": 0, "Comment": comment,
        "arrival_us": t_us + int(rng.integers(1, 30)) * US_S,
    }


def finalize_deals(rng, deals: pd.DataFrame, server: str, start_seq: int, invalid_pct: float,
                   now_us: int) -> pd.DataFrame:
    """Assign Deal/Order ids in time order and inject invalid rows for the expectations lab."""
    deals = deals.sort_values(["Time", "PositionID"], kind="stable").reset_index(drop=True)
    n = len(deals)
    deals["Deal"] = SERVER_META[server]["deal_base"] + start_seq + np.arange(n, dtype=np.int64)
    deals["Order"] = np.where(deals["Action"] == 2, 0, deals["Deal"] + 100_000_000)
    deals["Fee"] = 0.0
    deals["Dealer"] = np.where(deals["Action"] == 2, 9001, 0).astype(np.int64)
    trade_idx = np.flatnonzero(deals["Action"].to_numpy() != 2)
    k = int(len(trade_idx) * invalid_pct)
    if k:
        bad = rng.choice(trade_idx, size=k, replace=False)
        kind = rng.choice(4, size=k, p=[0.4, 0.2, 0.2, 0.2])
        deals.loc[bad[kind == 0], "Volume"] = 0
        deals.loc[bad[kind == 1], "Symbol"] = None
        deals.loc[bad[kind == 2], "Price"] = -deals.loc[bad[kind == 2], "Price"].abs()
        deals.loc[bad[kind == 3], "Time"] = now_us + 3 * US_D + rng.integers(0, US_D, size=(kind == 3).sum())
    deals["TimeMsc"] = deals["Time"] // 1000
    return deals


# -------------------------------------------------------------- user change stream
def user_change_rows(rng, users: pd.DataFrame, t0_us: int, now_us: int, server: str) -> tuple[list[dict], pd.DataFrame]:
    """CDC after-images (U/D) for existing users during [t0, now). Returns rows and final state."""
    days = (now_us - t0_us) / US_D
    ibs = ib_hierarchy_df(42)
    region = SERVER_META[server]["region"]
    events = []
    status = users["Status"].to_numpy()
    for i in range(len(users)):
        st = status[i]
        if st == "ACTIVE" and rng.random() < 0.25 * days:
            events.append((int(rng.integers(t0_us, now_us)), i, "access"))
        if st == "ACTIVE" and rng.random() < 0.01 * days:
            events.append((int(rng.integers(t0_us, now_us)), i, "leverage"))
        if users["_acct"].iat[i] == "STD" and rng.random() < 0.003 * days:
            events.append((int(rng.integers(t0_us, now_us)), i, "upgrade"))
        if rng.random() < 0.002 * days:
            events.append((int(rng.integers(t0_us, now_us)), i, "agent"))
        if st == "ACTIVE" and rng.random() < 0.004 * days:
            events.append((int(rng.integers(t0_us, now_us)), i, "dormant"))
        if st == "DORMANT" and rng.random() < 0.01 * days:
            events.append((int(rng.integers(t0_us, now_us)), i, "reactivate"))
        if st == "PENDING_KYC" and rng.random() < 0.5:
            events.append((int(rng.integers(t0_us, now_us)), i, "kyc_ok"))
        if rng.random() < 0.0003 * days:
            events.append((int(rng.integers(t0_us, now_us)), i, "delete"))
    events.sort()
    state = users.copy()
    deleted = set()
    rows = []
    for t, i, kind in events:
        if i in deleted:
            continue
        u = state.iloc[i].copy()
        op = "U"
        if kind == "access":
            u["LastAccess"] = t
        elif kind == "leverage":
            cap = LEVERAGE_CAP.get(u["Country"], 1000)
            opts = [lv for lv in LEVERAGES if lv <= cap and lv != u["Leverage"]]
            if not opts:
                continue
            u["Leverage"] = int(rng.choice(opts))
        elif kind == "upgrade":
            u["Group"] = u["Group"].replace("\\STD-", "\\RAW-")
            u["_acct"] = "RAW"
        elif kind == "agent":
            pool = ibs[(ibs.brand == u["_brand"]) & (ibs.region == region)].ib_login.to_numpy()
            u["Agent"] = int(rng.choice(pool)) if len(pool) and rng.random() < 0.85 else 0
        elif kind == "dormant":
            u["Status"] = "DORMANT"
        elif kind in ("reactivate", "kyc_ok"):
            u["Status"] = "ACTIVE"
        elif kind == "delete":
            op = "D"
            deleted.add(i)
        state.iloc[i] = u
        row = {c: u[c] for c in users.columns if not c.startswith("_")}
        row.update(Op=op, cdc_ts=t + int(rng.integers(1, 20)) * US_S)
        rows.append(row)
    final = state.drop(index=state.index[list(deleted)]) if deleted else state
    return rows, final.reset_index(drop=True)


# ------------------------------------------------------------------ table builders
def users_frame(df: pd.DataFrame, op: str | None = None, cdc_us: int | None = None) -> pd.DataFrame:
    out = df[[c for c in USERS_SCHEMA.names if c in df.columns]].copy()
    if op is not None:
        out["Op"] = op
    if cdc_us is not None:
        out["cdc_ts"] = cdc_us
    return out


def positions_frame(pos: pd.DataFrame, op: str, cdc_us, t_update_us, price_current, profit, rate,
                    storage=None) -> pd.DataFrame:
    return pd.DataFrame({
        "Op": op, "cdc_ts": cdc_us, "Position": pos["Position"].to_numpy(), "Login": pos["Login"].to_numpy(),
        "Symbol": pos["Symbol"].to_numpy(), "Action": pos["Action"].to_numpy(), "Volume": pos["Volume"].to_numpy(),
        "PriceOpen": pos["PriceOpen"].to_numpy(), "PriceCurrent": price_current, "PriceSL": pos["PriceSL"].to_numpy(),
        "PriceTP": pos["PriceTP"].to_numpy(), "Profit": profit,
        "Storage": pos["Storage"].to_numpy() if storage is None else storage,
        "ContractSize": pos["ContractSize"].to_numpy(), "RateProfit": np.round(rate, 6),
        "TimeCreate": pos["open_us"].to_numpy(), "TimeUpdate": t_update_us,
        "Reason": pos["ReasonOpen"].to_numpy(), "Comment": "",
    })


def to_arrow(df: pd.DataFrame, table: str) -> pa.Table:
    schema = SCHEMAS[table]
    data = {}
    for f in schema:
        col = df[f.name] if f.name in df.columns else pd.Series([None] * len(df))
        if pa.types.is_timestamp(f.type):
            data[f.name] = pa.array(pd.to_datetime(col.astype("int64"), unit="us", utc=True), type=f.type)
        elif pa.types.is_integer(f.type):
            data[f.name] = pa.array(col.astype("int64"), type=f.type)
        elif pa.types.is_floating(f.type):
            data[f.name] = pa.array(col.astype("float64"), type=f.type)
        else:
            data[f.name] = pa.array([None if (v is None or (isinstance(v, float) and np.isnan(v))) else str(v)
                                     for v in col], type=f.type)
    return pa.table(data, schema=schema)
