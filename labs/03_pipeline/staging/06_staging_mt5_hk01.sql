-- ===========================================================================
-- 预发布通道 · 新服务器 mt5-hk-01（实验 03c / 04c）
-- 这些 DMS 文件来自你自己 schema 中的 volume（管道配置 staging_root），
-- 不是共享的落地区。新服务器的数据通过规则之前不进入生产。
-- Staging lane · the new server mt5-hk-01 (labs 03c / 04c)
-- These DMS files come from a volume in your own schema (pipeline setting
-- staging_root), not from the shared landing zone. A new server's data stays
-- out of production until it passes the rules.
--
-- 三种规则行为 (three rule behaviours):
--   WARN（不写 ON VIOLATION）→ 保留该行并计数 (keep the row, count it)
--   DROP ROW                → 丢弃该行并计数 (drop the row, count it)
--   FAIL UPDATE             → 整个更新失败 (the whole update fails)
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- bronze_staging_mt5_deals：原样接入（与 bronze_mt5_deals 形状相同）
-- bronze_staging_mt5_deals : raw ingest (the same shape as bronze_mt5_deals)
-- ---------------------------------------------------------------------------
CREATE OR REFRESH STREAMING TABLE bronze_staging_mt5_deals
COMMENT 'Staging lane: raw DMS deal files of the new server mt5-hk-01, from a volume in your own schema (labs 03c/04c).'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  regexp_extract(_metadata.file_path, '/mt5/([^/]+)/', 1) AS server_id,
  _metadata.file_path                                     AS source_file,
  _metadata.file_modification_time                        AS file_modified_at,
  current_timestamp()                                     AS ingested_at
FROM STREAM read_files('${staging_root}/mt5/*/mt5_deals/', format => 'parquet');

-- ---------------------------------------------------------------------------
-- silver_staging_mt5_deals：与 silver_mt5_deals 相同的列和规则，但价格规则
-- 更严格：负价格说明价格源或复制出了问题，必须停止。
-- silver_staging_mt5_deals : the same columns and rules as silver_mt5_deals,
-- with a stricter price rule: a negative price means the price feed or the
-- replication is broken, so the update must stop.
-- ---------------------------------------------------------------------------
CREATE OR REFRESH STREAMING TABLE silver_staging_mt5_deals (
  CONSTRAINT valid_login             EXPECT (login IS NOT NULL)                           ON VIOLATION DROP ROW,
  CONSTRAINT valid_trade_volume      EXPECT (deal_type = 'BALANCE' OR volume_raw > 0)     ON VIOLATION DROP ROW,
  CONSTRAINT valid_trade_symbol      EXPECT (deal_type = 'BALANCE' OR symbol IS NOT NULL) ON VIOLATION DROP ROW,
  -- 要点 1 · 合同破坏会让整个更新失败；改成 DROP ROW 就变成"丢弃并隔离"
  -- Key point 1 · a contract break fails the whole update; change it to DROP ROW to drop and quarantine instead
  CONSTRAINT valid_trade_price       EXPECT (deal_type = 'BALANCE' OR price > 0)          ON VIOLATION FAIL UPDATE,
  -- 要点 2 · 不写 ON VIOLATION = 只警告：保留该行，事件日志记录违规行数
  -- Key point 2 · no ON VIOLATION = warn only: the row is kept and the event log counts it
  CONSTRAINT deal_time_not_in_future EXPECT (deal_time <= current_timestamp() + INTERVAL 1 HOUR)
)
COMMENT 'Staging lane deals of mt5-hk-01 that passed the rules. Negative prices stop the update (FAIL).'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT
  server_id,
  Deal                                                   AS deal_id,
  `Order`                                                AS order_id,
  Login                                                  AS login,
  `Time`                                                 AS deal_time,
  CAST(`Time` AS DATE)                                   AS deal_date,
  NULLIF(Symbol, '')                                     AS symbol,
  CASE Action WHEN 0 THEN 'BUY' WHEN 1 THEN 'SELL' WHEN 2 THEN 'BALANCE' ELSE 'OTHER' END AS deal_type,
  CASE Entry WHEN 0 THEN 'IN' WHEN 1 THEN 'OUT' ELSE 'OTHER' END                          AS entry,
  Volume                                                 AS volume_raw,
  Volume / 10000.0                                       AS lots,
  Price                                                  AS price,
  ContractSize                                           AS contract_size,
  RateProfit                                             AS rate_profit,
  Profit                                                 AS profit_usd,
  Commission                                             AS commission_usd,
  Storage                                                AS swap_usd,
  source_file,
  cdc_ts,
  ingested_at
FROM STREAM(bronze_staging_mt5_deals)
WHERE Op = 'I';

-- ---------------------------------------------------------------------------
-- silver_staging_mt5_deals_quarantine：违反任一规则的行，以及违反了哪些规则。
-- 它直接读 bronze，所以即使 silver 失败，它也会完成（并显示出问题的行）。
-- silver_staging_mt5_deals_quarantine : rows that break any rule, and which ones.
-- It reads bronze directly, so it still completes when silver fails (and shows the culprits).
-- ---------------------------------------------------------------------------
CREATE OR REFRESH STREAMING TABLE silver_staging_mt5_deals_quarantine
COMMENT 'Staging lane rows that break a silver rule, with failed_rules (quarantine pattern): review, fix at the source, replay.'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT * FROM (
  SELECT
    server_id,
    Deal                AS deal_id,
    Login               AS login,
    `Time`              AS deal_time,
    NULLIF(Symbol, '')  AS symbol,
    Action              AS action,
    Volume              AS volume_raw,
    Price               AS price,
    -- 要点 3 · 与 silver 相同的规则，并记录每一行违反的规则名称
    -- Key point 3 · the same rules as silver, recording the name of every rule a row breaks
    filter(array(
      CASE WHEN Login IS NULL THEN 'valid_login' END,
      CASE WHEN Action <> 2 AND NOT coalesce(Volume > 0, false) THEN 'valid_trade_volume' END,
      CASE WHEN Action <> 2 AND NULLIF(Symbol, '') IS NULL THEN 'valid_trade_symbol' END,
      CASE WHEN Action <> 2 AND NOT coalesce(Price > 0, false) THEN 'valid_trade_price' END
    ), r -> r IS NOT NULL) AS failed_rules,
    source_file,
    cdc_ts,
    ingested_at
  FROM STREAM(bronze_staging_mt5_deals)
  WHERE Op = 'I'
)
WHERE size(failed_rules) > 0;

-- ---------------------------------------------------------------------------
-- gold_staging_daily_volume：预发布通道每天每个品种的交易，用来判断新服务器能否上线。
-- 它依赖 silver_staging_mt5_deals：silver 失败时，它会被跳过 (SKIPPED)。
-- gold_staging_daily_volume : the staging lane's daily trading per symbol: is the new server ready?
-- It depends on silver_staging_mt5_deals: when silver fails, it is SKIPPED.
-- ---------------------------------------------------------------------------
CREATE OR REFRESH MATERIALIZED VIEW gold_staging_daily_volume
COMMENT 'Staging lane (mt5-hk-01) trading per day and symbol: deals, lots, USD notional, client P&L, batches.'
TBLPROPERTIES ('quality' = 'gold')
AS SELECT
  d.deal_date,
  d.server_id,
  d.symbol,
  s.asset_class,
  count(*)                                                          AS deals,
  round(sum(d.lots), 2)                                             AS lots,
  round(sum(d.lots * d.contract_size * d.price * d.rate_profit), 2) AS notional_usd,
  round(sum(d.profit_usd), 2)                                       AS client_pnl_usd,
  count(DISTINCT d.source_file)                                     AS batches
FROM silver_staging_mt5_deals d
LEFT JOIN ref_symbols s ON d.symbol = s.symbol
WHERE d.deal_type IN ('BUY', 'SELL')
GROUP BY ALL;
