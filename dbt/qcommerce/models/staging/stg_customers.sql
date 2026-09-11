SELECT
    customer_id,
    TRIM(zone_id) AS zone_id,
    
    SAFE_CAST(latitude AS FLOAT64) AS latitude,
    SAFE_CAST(longitude AS FLOAT64) AS longitude

FROM {{ source('raw', 'customers') }}

QUALIFY ROW_NUMBER() OVER (
    PARTITION BY customer_id
    ORDER BY customer_id
) = 1