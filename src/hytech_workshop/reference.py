"""Reference data: tradable symbols, IB hierarchy, MT5 servers, daily FX rates."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import SERVER_META

# symbol, description, asset_class, base, quote, contract_size, digits,
# start_price, annual_vol, popularity, spread, lot_median
SYMBOL_ROWS = [
    ("XAUUSD", "Gold vs US Dollar", "METAL", "XAU", "USD", 100, 2, 3900.0, 0.18, 22, 0.20, 0.20),
    ("XAGUSD", "Silver vs US Dollar", "METAL", "XAG", "USD", 5000, 3, 46.0, 0.30, 3, 0.030, 0.10),
    ("EURUSD", "Euro vs US Dollar", "FX_MAJOR", "EUR", "USD", 100000, 5, 1.1650, 0.07, 10, 0.00008, 0.30),
    ("GBPUSD", "British Pound vs US Dollar", "FX_MAJOR", "GBP", "USD", 100000, 5, 1.3450, 0.08, 5, 0.00010, 0.30),
    ("USDJPY", "US Dollar vs Japanese Yen", "FX_MAJOR", "USD", "JPY", 100000, 3, 147.50, 0.09, 6, 0.010, 0.30),
    ("AUDUSD", "Australian Dollar vs US Dollar", "FX_MAJOR", "AUD", "USD", 100000, 5, 0.6600, 0.09, 3, 0.00010, 0.30),
    ("USDCAD", "US Dollar vs Canadian Dollar", "FX_MAJOR", "USD", "CAD", 100000, 5, 1.3800, 0.06, 2, 0.00012, 0.30),
    ("USDCHF", "US Dollar vs Swiss Franc", "FX_MAJOR", "USD", "CHF", 100000, 5, 0.7950, 0.07, 2, 0.00012, 0.30),
    ("NZDUSD", "New Zealand Dollar vs US Dollar", "FX_MAJOR", "NZD", "USD", 100000, 5, 0.5850, 0.09, 1, 0.00012, 0.30),
    ("EURJPY", "Euro vs Japanese Yen", "FX_CROSS", "EUR", "JPY", 100000, 3, 171.80, 0.09, 2, 0.015, 0.25),
    ("GBPJPY", "British Pound vs Japanese Yen", "FX_CROSS", "GBP", "JPY", 100000, 3, 198.40, 0.11, 3, 0.025, 0.25),
    ("EURGBP", "Euro vs British Pound", "FX_CROSS", "EUR", "GBP", 100000, 5, 0.8660, 0.05, 1, 0.00012, 0.25),
    ("AUDJPY", "Australian Dollar vs Japanese Yen", "FX_CROSS", "AUD", "JPY", 100000, 3, 97.30, 0.11, 1, 0.015, 0.25),
    ("EURAUD", "Euro vs Australian Dollar", "FX_CROSS", "EUR", "AUD", 100000, 5, 1.7650, 0.08, 1, 0.00018, 0.25),
    ("GBPAUD", "British Pound vs Australian Dollar", "FX_CROSS", "GBP", "AUD", 100000, 5, 2.0380, 0.09, 1, 0.00022, 0.25),
    ("CADJPY", "Canadian Dollar vs Japanese Yen", "FX_CROSS", "CAD", "JPY", 100000, 3, 106.90, 0.10, 1, 0.018, 0.25),
    ("EURCHF", "Euro vs Swiss Franc", "FX_CROSS", "EUR", "CHF", 100000, 5, 0.9300, 0.05, 1, 0.00015, 0.25),
    ("USDSGD", "US Dollar vs Singapore Dollar", "FX_EXOTIC", "USD", "SGD", 100000, 5, 1.2900, 0.04, 1, 0.00020, 0.20),
    ("USDCNH", "US Dollar vs Offshore Yuan", "FX_EXOTIC", "USD", "CNH", 100000, 5, 7.1300, 0.04, 1, 0.00080, 0.20),
    ("USDMXN", "US Dollar vs Mexican Peso", "FX_EXOTIC", "USD", "MXN", 100000, 5, 18.400, 0.12, 1, 0.00400, 0.20),
    ("USOUSD", "WTI Crude Oil", "ENERGY", "USO", "USD", 1000, 3, 62.50, 0.35, 4, 0.030, 0.20),
    ("UKOUSD", "Brent Crude Oil", "ENERGY", "UKO", "USD", 1000, 3, 66.20, 0.33, 2, 0.030, 0.20),
    ("US30", "Dow Jones 30 Index", "INDEX", "US30", "USD", 1, 1, 46500.0, 0.16, 6, 2.0, 1.00),
    ("NAS100", "Nasdaq 100 Index", "INDEX", "NAS100", "USD", 1, 1, 24800.0, 0.22, 7, 1.5, 1.00),
    ("SP500", "S&P 500 Index", "INDEX", "SP500", "USD", 1, 1, 6700.0, 0.16, 3, 0.5, 1.00),
    ("GER40", "Germany 40 Index", "INDEX", "GER40", "EUR", 1, 1, 24200.0, 0.18, 2, 1.5, 1.00),
    ("UK100", "UK 100 Index", "INDEX", "UK100", "GBP", 1, 1, 9400.0, 0.14, 1, 1.2, 1.00),
    ("JPN225", "Japan 225 Index", "INDEX", "JPN225", "JPY", 100, 0, 45500.0, 0.20, 2, 10.0, 0.50),
    ("HK50", "Hong Kong 50 Index", "INDEX", "HK50", "HKD", 1, 0, 26500.0, 0.24, 3, 5.0, 2.00),
    ("AUS200", "Australia 200 Index", "INDEX", "AUS200", "AUD", 1, 1, 8900.0, 0.15, 1, 1.0, 1.00),
    ("BTCUSD", "Bitcoin vs US Dollar", "CRYPTO", "BTC", "USD", 1, 2, 112000.0, 0.55, 6, 25.0, 0.05),
    ("ETHUSD", "Ethereum vs US Dollar", "CRYPTO", "ETH", "USD", 1, 2, 4300.0, 0.70, 3, 2.5, 0.50),
    ("SOLUSD", "Solana vs US Dollar", "CRYPTO", "SOL", "USD", 10, 3, 210.0, 0.90, 1, 0.25, 0.50),
    ("XRPUSD", "XRP vs US Dollar", "CRYPTO", "XRP", "USD", 1000, 4, 2.85, 0.95, 1, 0.005, 0.50),
]

SYMBOL_COLUMNS = [
    "symbol", "description", "asset_class", "base_ccy", "quote_ccy", "contract_size", "digits",
    "start_price", "annual_vol", "popularity", "spread", "lot_median",
]

# Currencies whose USD value is derived from a traded pair: ccy -> (pair, invert)
USD_PER_CCY = {
    "EUR": ("EURUSD", False), "GBP": ("GBPUSD", False), "AUD": ("AUDUSD", False), "NZD": ("NZDUSD", False),
    "JPY": ("USDJPY", True), "CAD": ("USDCAD", True), "CHF": ("USDCHF", True), "SGD": ("USDSGD", True),
    "CNH": ("USDCNH", True), "MXN": ("USDMXN", True),
}
HKD_PEG = 7.80

IB_NAMES = [
    "Lion City Partners", "Andaman Capital", "Mekong Traders", "Klang Valley FX Club", "Pacific Edge",
    "Orchard Wealth", "Borneo Signals", "Siam Alpha", "Saigon Pips", "Java Trading House", "Manila Bay FX",
    "Harbour Line Advisors", "Formosa Markets", "Sydney Quant Desk", "Seoul Wave Trading", "Tokyo Tick",
    "Thames Alpha", "Rhine Signals", "Seine Capital", "Iberia Trading", "Roma Pips", "Gulf Horizon",
    "Desert Falcon FX", "Cape Markets", "Lagos Trade Hub", "Aegean Partners", "Vistula Traders",
    "Bosphorus Markets", "Andes Trading Group", "Pampas FX", "Aztec Signals", "Cartagena Capital",
    "Santiago Quant", "Rio Ticks", "Copacabana Trading", "Limassol Prime",
]

REGION_OF_SERVER = {s: m["region"] for s, m in SERVER_META.items()}


def symbols_df() -> pd.DataFrame:
    return pd.DataFrame(SYMBOL_ROWS, columns=SYMBOL_COLUMNS)


def symbols_csv_df() -> pd.DataFrame:
    """Public reference file (what COPY INTO loads): no simulator-only columns."""
    df = symbols_df()
    df["pip_size"] = np.power(10.0, -np.maximum(df["digits"].to_numpy() - 1, 0))
    return df[["symbol", "description", "asset_class", "base_ccy", "quote_ccy", "contract_size", "digits", "pip_size"]]


def ib_hierarchy_df(seed: int) -> pd.DataFrame:
    """~60 introducing brokers: masters per (brand, region) plus sub-IBs."""
    rng = np.random.default_rng(seed + 7)
    rows = []
    login = 70_000_001
    name_i = 0
    for server, meta in SERVER_META.items():
        for brand in meta["brands"]:
            n_master = 2 if meta["brands"][brand] >= 0.5 else 1
            for _ in range(n_master):
                master_login = login
                rows.append(_ib_row(master_login, None, brand, meta["region"], name_i, rng, master=True))
                login += 1
                name_i += 1
                for _ in range(int(rng.integers(2, 5))):
                    rows.append(_ib_row(login, master_login, brand, meta["region"], name_i, rng, master=False))
                    login += 1
                    name_i += 1
    df = pd.DataFrame(rows)
    df["ib_code"] = [f"IB-{i:04d}" for i in range(1, len(df) + 1)]
    return df[["ib_login", "ib_code", "ib_name", "parent_ib_login", "brand", "region", "tier",
               "rebate_usd_per_lot", "onboard_date", "status"]]


def _ib_row(login, parent, brand, region, name_i, rng, master):
    base = IB_NAMES[name_i % len(IB_NAMES)]
    suffix = "" if name_i < len(IB_NAMES) else f" {name_i // len(IB_NAMES) + 1}"
    return {
        "ib_login": login,
        "ib_name": base + suffix,
        "parent_ib_login": parent,
        "brand": brand,
        "region": region,
        "tier": "MASTER" if master else "SUB",
        "rebate_usd_per_lot": float(rng.choice([5.0, 6.0, 7.0, 8.0])) if master else float(rng.choice([2.0, 3.0, 4.0])),
        "onboard_date": (pd.Timestamp("2022-01-01") + pd.Timedelta(days=int(rng.integers(0, 1300)))).date().isoformat(),
        "status": "ACTIVE" if rng.random() > 0.05 else "SUSPENDED",
    }


def servers_df() -> pd.DataFrame:
    rows = []
    for server, meta in SERVER_META.items():
        rows.append({
            "server_id": server,
            "region": meta["region"],
            "brands": ",".join(meta["brands"].keys()),
            "platform": "MT5",
            "replication": "AWS DMS (full load + CDC, Parquet)",
            "go_live": "2026-10-13" if server == "mt5-hk-01" else "2023-01-01",
        })
    return pd.DataFrame(rows)


def fx_rates_daily_df(price_model, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    """Daily USD value of each quote currency, from the simulated price paths (closes)."""
    days = pd.date_range(start_date.normalize(), end_date.normalize(), freq="D", tz="UTC")
    rows = []
    for d in days:
        t = d + pd.Timedelta(hours=21)  # 21:00 UTC "daily close"
        rows.append({"rate_date": d.date().isoformat(), "ccy": "USD", "usd_per_ccy": 1.0})
        rows.append({"rate_date": d.date().isoformat(), "ccy": "HKD", "usd_per_ccy": round(1.0 / HKD_PEG, 6)})
        for ccy, (pair, invert) in USD_PER_CCY.items():
            px = float(price_model.price_at(pair, np.array([t.value // 1000]))[0])
            rows.append({"rate_date": d.date().isoformat(), "ccy": ccy, "usd_per_ccy": round(1.0 / px if invert else px, 6)})
    return pd.DataFrame(rows)
