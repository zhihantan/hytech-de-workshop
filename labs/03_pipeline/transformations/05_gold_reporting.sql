-- ===========================================================================
-- Gold · Reporting marts（Power BI / AI/BI 仪表盘 / Genie 消费的数据）
-- Gold · Reporting marts (what Power BI / AI/BI dashboards / Genie consume)
-- ===========================================================================

-- 每个服务器和交易对的日交易活动
-- Daily trading activity per server and symbol
CREATE OR REFRESH MATERIALIZED VIEW gold_daily_symbol_volume
COMMENT 'Daily trading activity per server and symbol: deals, lots, USD notional, client P&L, commission, swap.'
AS SELECT
  d.deal_date,
  d.server_id,
  d.symbol,
  s.asset_class,
  count(*)                                                             AS deals,
  count_if(d.entry = 'IN')                                             AS positions_opened,
  round(sum(d.lots), 2)                                                AS lots,
  -- 要点 5 · USD 名义本金 = 手数 × 合约大小 × 价格 × RateProfit（报价货币 → USD）；客户盈亏 = profit_usd 之和
  -- Key point 5 · USD notional = lots × contract size × price × RateProfit (quote ccy → USD); client P&L = sum of profit_usd
  round(sum(d.lots * d.contract_size * d.price * d.rate_profit), 2)    AS notional_usd,
  round(sum(d.profit_usd), 2)                                          AS client_pnl_usd,
  round(sum(d.commission_usd), 2)                                      AS commission_usd,
  round(sum(d.swap_usd), 2)                                            AS swap_usd,
  count(DISTINCT d.login)                                              AS active_clients
FROM silver_mt5_deals_current d
LEFT JOIN ref_symbols s ON d.symbol = s.symbol
WHERE d.deal_type IN ('BUY', 'SELL')
GROUP BY ALL;

-- 每个客户每天：盈亏、成本、资金（带有客户的**当前**属性）
-- Per client per day: P&L, costs, funding (with the client's *current* attributes)
CREATE OR REFRESH MATERIALIZED VIEW gold_client_daily_pnl
COMMENT 'Per client per day: trades, lots, trading P&L, costs, deposits and withdrawals (USD).'
AS WITH clients AS (
  SELECT server_id, login, brand, country, account_type, ib_login
  FROM silver_mt5_users
  WHERE __END_AT IS NULL
)
SELECT
  d.deal_date,
  d.server_id,
  d.login,
  c.brand,
  c.country,
  c.account_type,
  c.ib_login,
  count_if(d.deal_type IN ('BUY', 'SELL'))                                                    AS trades,
  round(sum(CASE WHEN d.deal_type IN ('BUY', 'SELL') THEN d.lots ELSE 0 END), 2)              AS lots,
  round(sum(CASE WHEN d.deal_type IN ('BUY', 'SELL') THEN d.profit_usd ELSE 0 END), 2)        AS trading_pnl_usd,
  round(sum(d.commission_usd + d.swap_usd), 2)                                                AS costs_usd,
  round(sum(CASE WHEN d.deal_type = 'BALANCE' AND d.profit_usd > 0 THEN d.profit_usd ELSE 0 END), 2)  AS deposits_usd,
  round(sum(CASE WHEN d.deal_type = 'BALANCE' AND d.profit_usd < 0 THEN -d.profit_usd ELSE 0 END), 2) AS withdrawals_usd
FROM silver_mt5_deals_current d
LEFT JOIN clients c ON d.server_id = c.server_id AND d.login = c.login
GROUP BY ALL;

-- Introducing-broker (IB) performance per day
CREATE OR REFRESH MATERIALIZED VIEW gold_ib_daily_performance
COMMENT 'IB performance per day: active clients, lots, rebates owed, net funding and client P&L.'
AS SELECT
  p.deal_date,
  ib.ib_code,
  ib.ib_name,
  ib.tier,
  ib.brand,
  ib.region,
  count(DISTINCT CASE WHEN p.trades > 0 THEN p.login END)         AS active_clients,
  round(sum(p.lots), 2)                                           AS lots,
  round(sum(p.lots) * max(ib.rebate_usd_per_lot), 2)              AS rebate_usd,
  round(sum(p.deposits_usd - p.withdrawals_usd), 2)               AS net_funding_usd,
  round(sum(p.trading_pnl_usd), 2)                                AS client_pnl_usd
FROM gold_client_daily_pnl p
JOIN ref_ib_hierarchy ib ON p.ib_login = ib.ib_login
GROUP BY ALL;

-- Current net client exposure per symbol (the dealing desk's B-book risk view)
CREATE OR REFRESH MATERIALIZED VIEW gold_net_exposure_by_symbol
COMMENT 'Net client exposure per symbol from currently open positions: long/short/net lots, USD notional, floating P&L.'
AS SELECT
  p.symbol,
  s.asset_class,
  count(*)                                                                     AS open_positions,
  count(DISTINCT p.login)                                                      AS clients,
  round(sum(CASE WHEN p.side = 'BUY' THEN p.lots ELSE 0 END), 2)               AS long_lots,
  round(sum(CASE WHEN p.side = 'SELL' THEN p.lots ELSE 0 END), 2)              AS short_lots,
  round(sum(CASE WHEN p.side = 'BUY' THEN p.lots ELSE -p.lots END), 2)         AS net_lots,
  round(sum(CASE WHEN p.side = 'BUY' THEN 1 ELSE -1 END
            * p.lots * p.contract_size * p.price_current * p.rate_profit), 2)  AS net_notional_usd,
  round(sum(p.floating_pnl_usd), 2)                                            AS floating_client_pnl_usd
FROM silver_mt5_positions p
LEFT JOIN ref_symbols s ON p.symbol = s.symbol
GROUP BY ALL;

-- Deposits / withdrawals per day, brand and payment method (rule-based parsing of free-text comments)
CREATE OR REFRESH MATERIALIZED VIEW gold_funding_daily
COMMENT 'Funding flows per day, brand and payment method. Method is parsed from MT5 comments with rules (see AI Functions lab).'
AS WITH f AS (
  SELECT
    d.deal_date,
    c.brand,
    d.profit_usd,
    CASE
      WHEN d.comment RLIKE '(?i)usdt|btc|crypto|比特币'                 THEN 'crypto'
      WHEN d.comment RLIKE '(?i)visa|mastercard|unionpay|银联|card'     THEN 'card'
      WHEN d.comment RLIKE '(?i)skrill|neteller|fasapay|wallet|钱包'    THEN 'e_wallet'
      WHEN d.comment RLIKE '(?i)wire|bank|电汇|银行'                    THEN 'bank_transfer'
      WHEN d.comment RLIKE '(?i)transfer|内部转账'                      THEN 'internal_transfer'
      ELSE 'unknown'
    END AS method
  FROM silver_mt5_deals_current d
  LEFT JOIN (SELECT server_id, login, brand FROM silver_mt5_users WHERE __END_AT IS NULL) c
    ON d.server_id = c.server_id AND d.login = c.login
  WHERE d.deal_type = 'BALANCE'
)
SELECT
  deal_date,
  brand,
  method,
  count_if(profit_usd > 0)                                          AS deposits,
  round(sum(CASE WHEN profit_usd > 0 THEN profit_usd ELSE 0 END), 2) AS deposits_usd,
  count_if(profit_usd < 0)                                          AS withdrawals,
  round(sum(CASE WHEN profit_usd < 0 THEN -profit_usd ELSE 0 END), 2) AS withdrawals_usd,
  round(sum(profit_usd), 2)                                         AS net_funding_usd
FROM f
GROUP BY ALL;
