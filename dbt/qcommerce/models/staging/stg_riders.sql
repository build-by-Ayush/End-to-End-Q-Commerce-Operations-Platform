SELECT
    TRIM(rider_id) AS rider_id,
    UPPER(TRIM(REPLACE(vehicle_type,'#',''))) AS vehicle_type,
    UPPER(TRIM(REPLACE(home_zone,'#',''))) AS home_zone,
    UPPER(TRIM(REPLACE(status,'#',''))) AS status,

    SAFE.PARSE_DATE('%d-%m-%Y',SUBSTR(TRIM(joined_at), 1, 10)) AS joined_at,

    CASE
        WHEN deactivated_at IS NULL THEN NULL
        WHEN TRIM(deactivated_at) = '' THEN NULL
        WHEN UPPER(TRIM(deactivated_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_DATE(
            '%d-%m-%Y',
            SUBSTR(TRIM(deactivated_at), 1, 10)
        )
    END AS deactivated_at

FROM {{ source('raw', 'riders') }}

QUALIFY ROW_NUMBER() OVER(
    PARTITION BY rider_id
    ORDER BY rider_id
) = 1