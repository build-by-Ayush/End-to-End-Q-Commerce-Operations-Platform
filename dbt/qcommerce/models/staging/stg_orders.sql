SELECT
    TRIM(order_id) AS order_id,
    TRIM(customer_id) AS customer_id,

    COALESCE(
        SAFE.PARSE_TIMESTAMP(
            '%Y-%m-%d %H:%M:%S',
            TRIM(created_at),
            'Asia/Kolkata'
        ),
        SAFE.PARSE_TIMESTAMP(
            '%d/%m/%Y %H:%M',
            TRIM(created_at),
            'Asia/Kolkata'
        ),
        SAFE.PARSE_TIMESTAMP(
            '%Y/%m/%d %H:%M:%S',
            TRIM(created_at),
            'Asia/Kolkata'
        ),
        SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M:%S',
            TRIM(created_at),
            'Asia/Kolkata'
        )
    ) AS created_at,

    COALESCE(
        SAFE.PARSE_TIMESTAMP(
            '%Y-%m-%d %H:%M:%S',
            TRIM(payment_success_at),
            'Asia/Kolkata'
        ),
        SAFE.PARSE_TIMESTAMP(
            '%d/%m/%Y %H:%M',
            TRIM(payment_success_at),
            'Asia/Kolkata'
        ),
        SAFE.PARSE_TIMESTAMP(
            '%Y/%m/%d %H:%M:%S',
            TRIM(payment_success_at),
            'Asia/Kolkata'
        ),
        SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M:%S',
            TRIM(payment_success_at),
            'Asia/Kolkata'
        )
    ) AS payment_success_at,

    SAFE_CAST(TRIM(delivery_latitude) AS FLOAT64) AS delivery_latitude,
    SAFE_CAST(TRIM(delivery_longitude) AS FLOAT64) AS delivery_longitude,

    UPPER(TRIM(REPLACE(delivery_zone, '#', ''))) AS delivery_zone,
    UPPER(TRIM(REPLACE(status, '#', ''))) AS status,

    CASE
        WHEN cancelled_at IS NULL THEN NULL
        WHEN TRIM(cancelled_at) = '' THEN NULL
        WHEN UPPER(TRIM(cancelled_at)) = 'NULL' THEN NULL
        ELSE COALESCE(
            SAFE.PARSE_TIMESTAMP(
                '%Y-%m-%d %H:%M:%S',
                TRIM(cancelled_at),
                'Asia/Kolkata'
            ),
            SAFE.PARSE_TIMESTAMP(
                '%d/%m/%Y %H:%M',
                TRIM(cancelled_at),
                'Asia/Kolkata'
            ),
            SAFE.PARSE_TIMESTAMP(
                '%Y/%m/%d %H:%M:%S',
                TRIM(cancelled_at),
                'Asia/Kolkata'
            ),
            SAFE.PARSE_TIMESTAMP(
                '%d-%m-%Y %H:%M:%S',
                TRIM(cancelled_at),
                'Asia/Kolkata'
            )
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