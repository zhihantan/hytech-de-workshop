# Databricks notebook source
# MAGIC %md
# MAGIC # genie_spec · 实验 10 的 Genie Agent 定义 (the lab 10 Genie Agent definition)
# MAGIC
# MAGIC 实验 10b 用 `%run ./genie_spec` 加载本笔记本：这里只有定义，不运行任何东西。它生成与实验 10 手动配置的 Genie Agent 相同的设置（serialized_space）。
# MAGIC
# MAGIC Lab 10b loads this notebook with `%run ./genie_spec`: it only holds definitions; nothing runs here. It builds the same settings (serialized_space) as the Genie Agent that lab 10 configures by hand.

# COMMAND ----------

import hashlib

# 参考版用自己的标题，不会覆盖你在实验 10 中手动配置的 Agent (the reference copy has its own title, so it never overwrites the agent you configure by hand in lab 10)
GENIE_TITLE = "MT5 交易分析助手 · {name} · 参考 (reference)"
GENIE_DESCRIPTION = "MT5 交易湖仓的 gold 表：成交、客户盈亏、出入金、IB 业绩和风险敞口。(Gold tables of the MT5 trade lakehouse: trading, client P&L, funding, IB performance and exposure.)"
GENIE_TABLES = ("gold_client_daily_pnl", "gold_daily_symbol_volume", "gold_funding_daily", "gold_ib_daily_performance",
                "gold_net_exposure_by_symbol", "ref_ib_hierarchy")
INSTRUCTIONS = [
    "用简体中文回答；表名、列名和 SQL 保持英文。(Answer in Simplified Chinese; keep table names, column names and SQL in English.)",
    "金额都是美元：直接引用数值并加千分位，不要换算成万或亿。(All amounts are USD: quote the values with thousands separators; never convert to 万 or 亿.)",
    "client_pnl_usd 和 trading_pnl_usd 是客户视角：负数表示客户亏钱（经纪商的收入）。(client_pnl_usd and trading_pnl_usd are from the client's side: negative means clients lost money, which is the broker's income.)",
    "lots 是标准手数；notional_usd 是美元名义金额。(lots are standard lots; notional_usd is the USD notional value.)",
    "品种别名：黄金 = XAUUSD，白银 = XAGUSD，原油 = USOUSD 或 UKOUSD，比特币 = BTCUSD，以太坊 = ETHUSD，纳指 = NAS100，道指 = US30。(Symbol aliases, as listed.)",
    "'上周' = 最近 7 天：deal_date >= date_sub(current_date(), 7)；'昨天' = 数据中最近的一个 deal_date。('last week' = the last 7 days; 'yesterday' = the latest deal_date in the data.)",
    "风险敞口用 gold_net_exposure_by_symbol：它是当前持仓的快照，没有日期。(Exposure comes from gold_net_exposure_by_symbol: a snapshot of open positions, with no date.)",
]
COLUMN_SYNONYMS = {
    "gold_client_daily_pnl": {"brand": ["品牌"], "deposits_usd": ["入金"], "login": ["客户账号", "账户"],
                              "trading_pnl_usd": ["客户交易盈亏", "客户盈亏"], "withdrawals_usd": ["出金"]},
    "gold_daily_symbol_volume": {"asset_class": ["资产类别"], "client_pnl_usd": ["客户盈亏", "client P&L"], "deals": ["成交笔数"],
                                 "lots": ["手数"], "notional_usd": ["名义金额", "成交额", "notional"], "symbol": ["品种", "交易品种"]},
    "gold_funding_daily": {"brand": ["品牌"], "deposits_usd": ["入金"], "method": ["支付方式", "入金方式"],
                           "net_funding_usd": ["净入金"], "withdrawals_usd": ["出金"]},
    "gold_ib_daily_performance": {"ib_name": ["代理", "IB", "介绍经纪人"], "net_funding_usd": ["净入金"], "rebate_usd": ["返佣"]},
    "gold_net_exposure_by_symbol": {"floating_client_pnl_usd": ["浮动盈亏"], "net_lots": ["净手数"],
                                    "net_notional_usd": ["净敞口", "净名义金额"]},
    "ref_ib_hierarchy": {"ib_name": ["代理", "IB"], "tier": ["层级"]},
}
SAMPLE_QUESTIONS = ["昨天名义金额最大的 5 个品种是什么？", "上周每个品牌的客户盈亏是多少？", "哪个代理 (IB) 上周的返佣最多？"]
BRAND_PNL_SQL = ("SELECT brand, round(sum(trading_pnl_usd), 2) AS client_pnl_usd FROM {fq}.gold_client_daily_pnl "
                 "WHERE deal_date >= date_sub(current_date(), 7) GROUP BY brand ORDER BY client_pnl_usd")
TOP_SYMBOLS_SQL = ("SELECT symbol, round(sum(notional_usd), 2) AS notional_usd FROM {fq}.gold_daily_symbol_volume "
                   "WHERE deal_date = (SELECT max(deal_date) FROM {fq}.gold_daily_symbol_volume) "
                   "GROUP BY symbol ORDER BY notional_usd DESC LIMIT 5")


def _id(seed: str, *parts: str) -> str:
    """确定性的 32 位十六进制 id：同一个 schema 每次生成相同的 id (deterministic 32-hex ids: the same schema always gets the same ids)."""
    return hashlib.sha256("|".join((seed,) + parts).encode("utf-8")).hexdigest()[:32]


def _sorted(items):
    return sorted(items, key=lambda x: x["id"])


def genie_space(catalog: str, schema: str) -> dict:
    """实验 10 的 Genie Agent 设置（serialized_space v2）(the lab 10 Genie Agent settings, serialized_space v2)."""
    fq_plain, fq = f"{catalog}.{schema}", f"`{catalog}`.`{schema}`"
    seed = fq_plain
    tables = []
    for t in sorted(GENIE_TABLES):
        entry = {"identifier": f"{fq_plain}.{t}"}
        cols = COLUMN_SYNONYMS.get(t, {})
        if cols:
            entry["column_configs"] = [{"column_name": c, "synonyms": s} for c, s in sorted(cols.items())]
        tables.append(entry)
    return {
        "version": 2,
        "config": {"sample_questions": _sorted({"id": _id(seed, "sample", q), "question": [q]} for q in SAMPLE_QUESTIONS)},
        "data_sources": {"tables": tables},
        "instructions": {
            "text_instructions": [{"id": _id(seed, "instructions"), "content": list(INSTRUCTIONS)}],
            "example_question_sqls": _sorted([
                {"id": _id(seed, "example", SAMPLE_QUESTIONS[1]), "question": [SAMPLE_QUESTIONS[1]], "sql": [BRAND_PNL_SQL.format(fq=fq)]},
            ]),
            "join_specs": _sorted([{
                "id": _id(seed, "join", "ib"),
                "left": {"identifier": f"{fq_plain}.gold_client_daily_pnl", "alias": "gold_client_daily_pnl"},
                "right": {"identifier": f"{fq_plain}.ref_ib_hierarchy", "alias": "ref_ib_hierarchy"},
                "sql": ["`gold_client_daily_pnl`.`ib_login` = `ref_ib_hierarchy`.`ib_login`",
                        "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"],
            }]),
            "sql_snippets": {
                "measures": _sorted([{
                    "id": _id(seed, "measure", "notional_per_deal"), "alias": "notional_per_deal",
                    "display_name": "每笔名义金额 (Notional per deal)",
                    "sql": ["SUM(gold_daily_symbol_volume.notional_usd) / SUM(gold_daily_symbol_volume.deals)"],
                    "synonyms": ["平均每笔名义金额", "notional per deal"],
                }]),
                "filters": _sorted([{
                    "id": _id(seed, "filter", "crypto"), "display_name": "加密货币品种 (Crypto symbols)",
                    "sql": ["gold_daily_symbol_volume.asset_class = 'CRYPTO'"], "synonyms": ["加密货币", "crypto"],
                }]),
            },
        },
        "benchmarks": {"questions": _sorted([
            {"id": _id(seed, "benchmark", SAMPLE_QUESTIONS[0]), "question": [SAMPLE_QUESTIONS[0]],
             "answer": [{"format": "SQL", "content": [TOP_SYMBOLS_SQL.format(fq=fq)]}]},
        ])},
    }
