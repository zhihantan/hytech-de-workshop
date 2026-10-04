-- ===========================================================================
-- Reference data · 参考数据
-- 由业务部门维护的小型 CSV 文件。物化视图在每次更新时重新读取它们，
-- 所以编辑后的 CSV 会在下次运行时生效。
-- Small CSV files maintained by the business. Materialized views re-read them
-- on every update, so an edited CSV shows up on the next run.
-- ===========================================================================

CREATE OR REFRESH MATERIALIZED VIEW ref_symbols
COMMENT 'Tradable symbols: asset class, quote currency, contract size, digits (ref/symbols CSV)'
AS SELECT * FROM read_files('${ref_root}/symbols/', format => 'csv', header => true);

CREATE OR REFRESH MATERIALIZED VIEW ref_ib_hierarchy
COMMENT 'Introducing brokers (IB): master/sub hierarchy and rebate per lot (ref/ib_hierarchy CSV)'
AS SELECT * FROM read_files('${ref_root}/ib_hierarchy/', format => 'csv', header => true);

CREATE OR REFRESH MATERIALIZED VIEW ref_servers
COMMENT 'MT5 trade servers replicated by DMS (ref/servers CSV)'
AS SELECT * FROM read_files('${ref_root}/servers/', format => 'csv', header => true);
