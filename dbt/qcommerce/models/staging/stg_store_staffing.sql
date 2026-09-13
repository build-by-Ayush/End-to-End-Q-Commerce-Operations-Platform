SELECT
    TRIM(staffing_snapshot_id) AS staffing_snapshot_id,
    TRIM(store_id) AS store_id,

    SAFE.PARSE_TIMESTAMP('%d-%m-%Y %H:%M',TRIM(recorded_at)) AS recorded_at,

    SAFE_CAST(pickers_scheduled AS INT64) AS pickers_scheduled,
    SAFE_CAST(pickers_available AS INT64) AS pickers_available,
    SAFE_CAST(packers_scheduled AS INT64) AS packers_scheduled,
    SAFE_CAST(packers_available AS INT64) AS packers_available

FROM {{ source('raw', 'store_staffing') }}

QUALIFY ROW_NUMBER() OVER(
    PARTITION BY staffing_snapshot_id
    ORDER BY staffing_snapshot_id
) = 1