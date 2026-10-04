-- ===========================================================================
-- Silver · App events：扁平化、恢复救援数据、去重
-- Silver · App events: flatten, recover rescued values, de-duplicate
-- ===========================================================================

CREATE OR REFRESH MATERIALIZED VIEW silver_app_events
COMMENT 'Parsed app events, one row per event_id (SDK retries removed). amount/campaign_id recovered from _rescued_data.'
AS SELECT
  event_id,
  event,
  distinct_id,
  timestamp_millis(time)                                  AS event_time,
  CAST(timestamp_millis(time) AS DATE)                    AS event_date,
  properties.server_id                                    AS server_id,
  properties.login                                        AS login,
  properties.brand                                        AS brand,
  properties.`$country`                                   AS country,
  properties.`$os`                                        AS os,
  properties.`$app_version`                               AS app_version,
  properties.symbol                                       AS symbol,
  properties.method                                       AS method,
  coalesce(
    properties.amount,
    try_cast(replace(get_json_object(_rescued_data, '$.properties.amount'), ',', '') AS DOUBLE)
  )                                                       AS amount_usd,
  get_json_object(_rescued_data, '$.properties.campaign_id') AS campaign_id,
  properties.feedback_text                                AS feedback_text,
  properties.rating                                       AS rating,
  _rescued_data IS NOT NULL                               AS has_rescued_data
FROM bronze_app_events
QUALIFY row_number() OVER (PARTITION BY event_id ORDER BY ingested_at) = 1;
