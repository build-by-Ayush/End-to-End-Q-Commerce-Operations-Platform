SELECT
    TRIM(order_id) AS order_id,
    TRIM(customer_id) AS customer_id,

    SAFE.PARSE_TIMESTAMP('%d-%m-%Y %H:%M',NULLIF(TRIM(created_at), '')) AS created_at,
    SAFE.PARSE_TIMESTAMP('%d-%m-%Y %H:%M',NULLIF(TRIM(payment_success_at), '')) AS payment_success_at,

    SAFE_CAST(TRIM(delivery_latitude) AS FLOAT64) AS delivery_latitude,
    SAFE_CAST(TRIM(delivery_longitude) AS FLOAT64) AS delivery_longitude,

    UPPER(TRIM(REPLACE(delivery_zone, '#', ''))) AS delivery_zone,
    UPPER(TRIM(REPLACE(status, '#', ''))) AS status,

    CASE
        WHEN cancelled_at IS NULL THEN NULL
        WHEN TRIM(cancelled_at) = '' THEN NULL
        WHEN UPPER(TRIM(cancelled_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(cancelled_at)
        )
    END AS cancelled_at,

    CASE
        WHEN cancellation_reason IS NULL THEN NULL
        WHEN TRIM(cancellation_reason) = '' THEN NULL
        WHEN UPPER(TRIM(cancellation_reason)) = 'NULL' THEN NULL
        ELSE UPPER(TRIM(REPLACE(cancellation_reason, '#', '')))
    END AS cancellation_reason,

    CASE
        WHEN failure_reason IS NULL THEN NULL
        WHEN TRIM(failure_reason) = '' THEN NULL
        WHEN UPPER(TRIM(failure_reason)) = 'NULL' THEN NULL
        ELSE UPPER(TRIM(REPLACE(failure_reason, '#', '')))
    END AS failure_reason

FROM {{ source('raw', 'orders') }}

QUALIFY ROW_NUMBER() OVER (
    PARTITION BY order_id
    ORDER BY order_id
) = 1