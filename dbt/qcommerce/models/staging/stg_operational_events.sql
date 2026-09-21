SELECT
    TRIM(event_id) AS event_id,

    CASE
        WHEN event_type IS NULL THEN NULL
        WHEN TRIM(event_type) = '' THEN NULL
        WHEN UPPER(TRIM(event_type)) = 'NULL' THEN NULL
        ELSE UPPER(TRIM(REPLACE(event_type, '#', '')))
    END AS event_type,

    COALESCE(
        SAFE.PARSE_TIMESTAMP(
            '%Y-%m-%d %H:%M:%S',
            TRIM(occurred_at),
            'Asia/Kolkata'
        ),
        SAFE.PARSE_TIMESTAMP(
            '%d/%m/%Y %H:%M',
            TRIM(occurred_at),
            'Asia/Kolkata'
        ),
        SAFE.PARSE_TIMESTAMP(
            '%Y/%m/%d %H:%M:%S',
            TRIM(occurred_at),
            'Asia/Kolkata'
        ),
        SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M:%S',
            TRIM(occurred_at),
            'Asia/Kolkata'
        )
    ) AS occurred_at,

    TRIM(order_id) AS order_id,
    TRIM(fulfilment_unit_id) AS fulfilment_unit_id,
    TRIM(delivery_id) AS delivery_id,
    TRIM(store_id) AS store_id,
    TRIM(rider_id) AS rider_id,

    CASE
        WHEN reason IS NULL THEN NULL
        WHEN TRIM(reason) = '' THEN NULL
        WHEN UPPER(TRIM(reason)) = 'NULL' THEN NULL
        ELSE UPPER(TRIM(REPLACE(reason, '#', '')))
    END AS reason

FROM {{ source('raw', 'operational_events') }}

QUALIFY ROW_NUMBER() OVER(
    PARTITION BY event_id
    ORDER BY event_id
) = 1