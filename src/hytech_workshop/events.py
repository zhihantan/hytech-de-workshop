"""Sensors-Data-style mobile/web app events (JSON lines), with deliberate schema drift."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .mt5 import HOUR_W, US_D, US_H
from .reference import symbols_df
from .storage import write_text

EVENT_MIX = [("$AppStart", 0.22), ("login", 0.15), ("view_quote", 0.28), ("trade_open_click", 0.12),
             ("deposit_click", 0.07), ("deposit_submit", 0.04), ("withdraw_submit", 0.02), ("kyc_upload", 0.02),
             ("app_feedback", 0.03), ("$AppViewScreen", 0.05)]
SCREENS = ["Home", "Markets", "Deposit", "Withdraw", "Positions", "History", "Profile", "Promotions"]
METHODS = ["USDT-TRC20", "USDT-ERC20", "Visa", "Mastercard", "Bank Wire", "Local Bank", "Skrill", "UnionPay"]
CAMPAIGNS = ["OCT_GOLD_RUSH", "NFP_WEBINAR", "IB_DOUBLE_REBATE"]
FEEDBACK_ZH = [
    "出金到账太慢了，已经三天了，请尽快处理。我的电话 {phone}",
    "黄金点差在非农期间太大了",
    "App 在行情波动时经常卡顿，平仓按钮没反应",
    "KYC 审核被拒绝了，不知道原因，请联系我 {email}",
    "入金 USDT 很快，体验很好",
    "希望增加更多加密货币品种",
    "无法上传身份证照片，一直显示错误",
    "客服回复很及时，谢谢！",
    "图表加载太慢，希望优化",
]
FEEDBACK_EN = [
    "Withdrawal still pending after 48 hours, please check. Call me on {phone}",
    "Great app, fast execution on XAUUSD!",
    "Spread on NAS100 widened a lot during the US open.",
    "The app crashed when I tried to close my position.",
    "Please email me the KYC requirements: {email}",
    "Customer support replied quickly, thanks!",
    "Deposit by card failed twice, money was deducted.",
    "Love the new dark mode.",
]


def _ip(rng) -> str:
    prefix = ["192.0.2", "198.51.100", "203.0.113"][rng.integers(3)]  # RFC 5737 documentation ranges
    return f"{prefix}.{rng.integers(1, 255)}"


def gen_events(rng, users_by_server: dict[str, pd.DataFrame], start_us: int, end_us: int, n: int,
               drift_from_us: int, mismatch_from_us: int) -> list[tuple[int, dict]]:
    servers = list(users_by_server)
    sizes = np.array([len(users_by_server[s]) for s in servers], dtype=float)
    syms = symbols_df()["symbol"].to_numpy()
    names = [e for e, _ in EVENT_MIX]
    p = np.array([w for _, w in EVENT_MIX])
    days = np.arange(start_us - start_us % US_D, end_us, US_D)
    t = (rng.choice(days, size=n) + rng.choice(24, size=n, p=HOUR_W) * US_H + rng.integers(0, US_H, size=n))
    t = np.where((t >= start_us) & (t < end_us), t, rng.integers(start_us, end_us, size=n))
    out: list[tuple[int, dict]] = []
    for ti in np.sort(t):
        ti = int(ti)
        s = servers[rng.choice(len(servers), p=sizes / sizes.sum())]
        u = users_by_server[s].iloc[int(rng.integers(len(users_by_server[s])))]
        ev = names[rng.choice(len(names), p=p / p.sum())]
        anon = ev in ("$AppStart", "$AppViewScreen") and rng.random() < 0.3
        os_ = ["iOS", "Android", "Web"][rng.choice(3, p=[0.45, 0.45, 0.10])]
        drifted = ti >= drift_from_us
        props = {
            "$os": os_, "$app_version": "3.5.0" if drifted and rng.random() < 0.6 else "3.4.1",
            "$country": u["Country"], "$ip": _ip(rng), "brand": u["_brand"], "server_id": s,
            "login": None if anon else int(u["Login"]),
        }
        if ev in ("view_quote", "trade_open_click"):
            props["symbol"] = str(syms[rng.integers(len(syms))])
        elif ev == "$AppViewScreen":
            props["screen"] = SCREENS[rng.integers(len(SCREENS))]
        elif ev in ("deposit_click", "deposit_submit", "withdraw_submit"):
            props["method"] = METHODS[rng.integers(len(METHODS))]
            if ev != "deposit_click":
                amt = round(float(rng.lognormal(np.log(450), 0.9)), 2)
                # type drift: amount sometimes arrives as a formatted string -> lands in _rescued_data
                props["amount"] = f"{amt:,.2f}" if ti >= mismatch_from_us and rng.random() < 0.15 else amt
                props["currency"] = "USD"
        elif ev == "app_feedback":
            pool = FEEDBACK_ZH if (u["Language"] == "zh" and rng.random() < 0.7) else FEEDBACK_EN
            props["feedback_text"] = pool[rng.integers(len(pool))].format(email=u["Email"], phone=u["Phone"])
            props["rating"] = int(rng.integers(1, 6))
        if drifted and rng.random() < 0.3:
            props["campaign_id"] = CAMPAIGNS[rng.integers(len(CAMPAIGNS))]  # new field (schema drift)
        event = {
            "event_id": "e" + "".join(f"{x:02x}" for x in rng.integers(0, 256, size=8)),
            "event": ev,
            "distinct_id": f"dev-{rng.integers(10**8, 10**9)}" if anon else str(int(u["Login"])),
            "time": ti // 1000,
            "lib": {"$lib": os_, "$lib_version": "4.3.0" if drifted else "4.2.0"},
            "properties": props,
        }
        out.append((ti, event))
        if rng.random() < 0.01:  # SDK retry -> duplicate event
            out.append((ti + int(rng.integers(1, 120)) * 1_000_000, event))
    return out


def write_events(events: list[tuple[int, dict]], events_dir: str, bucket_us: int = US_H) -> int:
    """Group events into files by bucket (hour) -> <dir>/<yyyy-mm-dd>/events-<yyyymmdd-HHMMSS>.json"""
    buckets: dict[int, list[str]] = {}
    for ti, ev in events:
        buckets.setdefault(ti - ti % bucket_us, []).append(json.dumps(ev, ensure_ascii=False))
    for b, lines in sorted(buckets.items()):
        dt = datetime.fromtimestamp(b / 1_000_000, tz=timezone.utc)
        write_text("\n".join(lines) + "\n", f"{events_dir}/{dt:%Y-%m-%d}/events-{dt:%Y%m%d-%H%M%S}.json")
    return len(buckets)
