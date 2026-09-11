SELECT
    TRIM(store_id) AS store_id,
    TRIM(REPLACE(store_name, '#', '')) AS store_name,
    UPPER(TRIM(REPLACE(zone, '#', ''))) AS zone,

    SAFE_CAST(TRIM(latitude) AS FLOAT64) AS latitude,
    SAFE_CAST(TRIM(longitude) AS FLOAT64) AS longitude,
    SAFE_CAST(TRIM(baseline_capacity) AS INT64) AS baseline_capacity,

    UPPER(TRIM(status)) AS status,
    SAFE.PARSE_DATE('%d-%m-%Y',SUBSTR(TRIM(opened_at), 1, 10)) AS opened_at,

    CASE
        WHEN closed_at IS NULL THEN NULL
        WHEN TRIM(closed_at) = '' THEN NULL
        WHEN UPPER(TRIM(closed_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_DATE(
            '%d-%m-%Y',
            SUBSTR(TRIM(closed_at), 1, 10)
        )
    END AS closed_at

FROM {{ source('raw', 'stores') }}

QUALIFY ROW_NUMBER() OVER (
    PARTITION BY store_id
    ORDER BY store_id
) = 1