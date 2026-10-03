-- ===========================================================================
-- Bronze · App events (Sensors-style JSON)
-- An explicit "contract" schema: fields the SDK adds later (e.g. campaign_id)
-- and values with the wrong type (amount sent as "1,234.50") are not lost —
-- they land in _rescued_data as JSON.
-- ===========================================================================

CREATE OR REFRESH STREAMING TABLE bronze_app_events
COMMENT 'Raw app events (JSON lines). Unknown fields / type mismatches are kept in _rescued_data.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT
  *,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM STREAM read_files(
  '${landing_root}/app_events/',
  format => 'json',
  schema => 'event_id STRING, event STRING, distinct_id STRING, time BIGINT,
             lib STRUCT<`$lib`: STRING, `$lib_version`: STRING>,
             properties STRUCT<`$os`: STRING, `$app_version`: STRING, `$country`: STRING, `$ip`: STRING,
                               brand: STRING, server_id: STRING, login: BIGINT, symbol: STRING, screen: STRING,
                               method: STRING, amount: DOUBLE, currency: STRING, feedback_text: STRING, rating: INT>',
  rescuedDataColumn => '_rescued_data'
);
