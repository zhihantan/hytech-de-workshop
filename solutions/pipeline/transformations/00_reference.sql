-- ===========================================================================
-- Reference data · 参考数据
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
