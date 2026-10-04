-- ===========================================================================
-- Silver · MT5
-- 经验法则（来自 Hytech 实时 POC）：
--   * 可变实体（用户、持仓）-> AUTO CDC（按键 MERGE）
--   * 不可变事实（成交，~99.9% 插入）-> 只追加流式表
--     + 用于稀有更正/删除的小型 AUTO CDC 表。
--   追加成本与**更改的**数据规模成正比；大表 MERGE 与**存储的**数据规模成正比。
-- Rule of thumb (from Hytech's real-time POC):
--   * Mutable entities (users, positions)  -> AUTO CDC  (MERGE by key)
--   * Immutable facts (deals, ~99.9% inserts) -> APPEND-ONLY streaming table
--     + a tiny AUTO CDC table for the rare corrections/deletes.
--   Append cost scales with data *changed*; a MERGE into a big table scales
--   with data *stored*.
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- silver_mt5_users：AUTO CDC，SCD Type 2（组别 / 杠杆 / IB / 状态的历史）
-- silver_mt5_users : AUTO CDC, SCD Type 2 (history of group / leverage / IB / status)
-- ---------------------------------------------------------------------------
CREATE OR REFRESH STREAMING TABLE silver_mt5_users
COMMENT 'MT5 client accounts with change history (SCD2). Current row: __END_AT IS NULL.'
TBLPROPERTIES ('quality' = 'silver');

CREATE FLOW silver_mt5_users_cdc AS AUTO CDC INTO silver_mt5_users
FROM (
  SELECT
    server_id,
    Login                                                   AS login,
    `Group`                                                 AS mt_group,
    split_part(`Group`, '\\', 2)                            AS brand,
    split_part(split_part(`Group`, '\\', 3), '-', 1)        AS account_type,
    FirstName                                               AS first_name,
    LastName                                                AS last_name,
    Country                                                 AS country,
    Language                                                AS language,
    Email                                                   AS email,
    Phone                                                   AS phone,
    Status                                                  AS status,
    Leverage                                                AS leverage,
    NULLIF(Agent, 0)                                        AS ib_login,
    `Comment`                                               AS comment,
    Registration                                            AS registered_at,
    LastAccess                                              AS last_access_at,
    Op                                                      AS _op,
    cdc_ts
  FROM STREAM(bronze_mt5_users)
)
-- TODO 2 · 完成 AUTO CDC 子句 (Complete the AUTO CDC clauses):
--   * 键 = server + login（在每个 MT5 服务器内 login 是唯一的）
--   * DMS 用 _op = 'D' 标记删除
--   * 按 DMS 提交时间戳 cdc_ts 排序更改
--   * 仅为这些列保留历史（SCD Type 2）：mt_group, account_type, leverage, ib_login, status
-- TODO 2 · Complete the AUTO CDC clauses:
--   * key = server + login (login is only unique per MT5 server)
--   * DMS marks deletes with _op = 'D'
--   * order changes by the DMS commit timestamp cdc_ts
--   * keep history (SCD Type 2) only for: mt_group, account_type, leverage, ib_login, status
KEYS (____)
APPLY AS DELETE WHEN ____
SEQUENCE BY ____
COLUMNS * EXCEPT (_op)
STORED AS SCD TYPE ____
TRACK HISTORY ON ____;

-- ---------------------------------------------------------------------------
-- silver_mt5_positions：AUTO CDC，SCD Type 1（仅当前持仓）
-- silver_mt5_positions : AUTO CDC, SCD Type 1 (current open positions only)
-- ---------------------------------------------------------------------------
CREATE OR REFRESH STREAMING TABLE silver_mt5_positions
COMMENT 'Currently open MT5 positions (SCD1). Closed positions are deleted (DMS Op = D).'
TBLPROPERTIES ('quality' = 'silver');

CREATE FLOW silver_mt5_positions_cdc AS AUTO CDC INTO silver_mt5_positions
FROM (
  SELECT
    server_id,
    Position                                   AS position_id,
    Login                                      AS login,
    Symbol                                     AS symbol,
    CASE Action WHEN 0 THEN 'BUY' WHEN 1 THEN 'SELL' END AS side,
    Volume / 10000.0                           AS lots,
    PriceOpen                                  AS price_open,
    PriceCurrent                               AS price_current,
    PriceSL                                    AS price_sl,
    PriceTP                                    AS price_tp,
    Profit                                     AS floating_pnl_usd,
    Storage                                    AS swap_usd,
    ContractSize                               AS contract_size,
    RateProfit                                 AS rate_profit,
    TimeCreate                                 AS opened_at,
    TimeUpdate                                 AS updated_at,
    Op                                         AS _op,
    cdc_ts
  FROM STREAM(bronze_mt5_positions)
)
KEYS (server_id, position_id)
APPLY AS DELETE WHEN _op = 'D'
SEQUENCE BY cdc_ts
COLUMNS * EXCEPT (_op)
STORED AS SCD TYPE 1;

-- ---------------------------------------------------------------------------
-- silver_mt5_deals：只追加 + 数据质量期望
-- silver_mt5_deals : APPEND-ONLY + data-quality expectations
-- ---------------------------------------------------------------------------
CREATE OR REFRESH STREAMING TABLE silver_mt5_deals (
  CONSTRAINT valid_login             EXPECT (login IS NOT NULL)                        ON VIOLATION DROP ROW,
  -- TODO 3a · 删除 volume_raw 不为正的交易行（余额操作的 volume 为 0 — 保留它们！）
  -- TODO 3a · drop trade rows whose volume_raw is not positive (balance deals have volume 0 — keep them!)
  CONSTRAINT valid_trade_volume      EXPECT (____)  ON VIOLATION DROP ROW,
  CONSTRAINT valid_trade_symbol      EXPECT (deal_type = 'BALANCE' OR symbol IS NOT NULL) ON VIOLATION DROP ROW,
  -- TODO 3b · 删除价格不为正的交易行
  -- TODO 3b · drop trade rows whose price is not positive
  CONSTRAINT valid_trade_price       EXPECT (____)       ON VIOLATION DROP ROW,
  CONSTRAINT deal_time_not_in_future EXPECT (deal_time <= current_timestamp() + INTERVAL 1 HOUR)
)
COMMENT 'MT5 deals (trades + balance operations), append-only. Invalid trade rows are dropped; future-dated rows are flagged (warn).'
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
  Reason                                                 AS reason_code,
  Volume                                                 AS volume_raw,
  Volume / 10000.0                                       AS lots,
  Price                                                  AS price,
  ContractSize                                           AS contract_size,
  RateProfit                                             AS rate_profit,
  Profit                                                 AS profit_usd,
  Storage                                                AS swap_usd,
  Commission                                             AS commission_usd,
  Fee                                                    AS fee_usd,
  NULLIF(PositionID, 0)                                  AS position_id,
  NULLIF(Dealer, 0)                                      AS dealer,
  `Comment`                                              AS comment,
  cdc_ts,
  ingested_at
FROM STREAM(bronze_mt5_deals)
-- TODO 4 · 成交是不可变的：只在这里保留 DMS 插入（修正在下方处理）。
--          为什么不用 AUTO CDC？见文件开头的说明。
-- TODO 4 · Deals are immutable: keep only DMS inserts here (corrections are handled below).
--          Why not AUTO CDC? See the explanation at the top of the file.
WHERE Op = '____';

-- ---------------------------------------------------------------------------
-- silver_mt5_deal_corrections：稀有的做市商修正 (U) / 删除 (D)
-- 小表，所以 MERGE 成本低。
-- silver_mt5_deal_corrections : the rare dealer corrections (U) / deletions (D)
-- Tiny table, so its MERGE is cheap.
-- ---------------------------------------------------------------------------
CREATE OR REFRESH STREAMING TABLE silver_mt5_deal_corrections
COMMENT 'Latest correction or deletion per deal (DMS Op U/D).'
TBLPROPERTIES ('quality' = 'silver');

CREATE FLOW silver_mt5_deal_corrections_cdc AS AUTO CDC INTO silver_mt5_deal_corrections
FROM (
  SELECT
    server_id,
    Deal                AS deal_id,
    Op                  AS change_op,
    Profit              AS profit_usd,
    Commission          AS commission_usd,
    Storage             AS swap_usd,
    `Comment`           AS comment,
    NULLIF(Dealer, 0)   AS dealer,
    cdc_ts
  FROM STREAM(bronze_mt5_deals)
  WHERE Op IN ('U', 'D')
)
KEYS (server_id, deal_id)
SEQUENCE BY cdc_ts
STORED AS SCD TYPE 1;

-- ---------------------------------------------------------------------------
-- silver_mt5_deals_current：已应用修正的成交，已移除删除
-- silver_mt5_deals_current : deals with corrections applied, deletions removed
-- ---------------------------------------------------------------------------
CREATE OR REFRESH MATERIALIZED VIEW silver_mt5_deals_current
COMMENT 'Deals as of now: dealer corrections applied, deleted deals removed. Base for all gold marts.'
AS SELECT
  d.* EXCEPT (profit_usd, commission_usd, swap_usd, comment, dealer),
  coalesce(c.profit_usd, d.profit_usd)         AS profit_usd,
  coalesce(c.commission_usd, d.commission_usd) AS commission_usd,
  coalesce(c.swap_usd, d.swap_usd)             AS swap_usd,
  coalesce(c.comment, d.comment)               AS comment,
  coalesce(c.dealer, d.dealer)                 AS dealer,
  c.change_op IS NOT NULL                      AS is_corrected
FROM silver_mt5_deals d
LEFT JOIN silver_mt5_deal_corrections c
  ON d.server_id = c.server_id AND d.deal_id = c.deal_id
WHERE c.change_op IS NULL OR c.change_op <> 'D';
