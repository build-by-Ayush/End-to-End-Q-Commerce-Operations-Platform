SELECT
    TRIM(delivery_id) AS delivery_id,
    TRIM(fulfilment_unit_id) AS fulfilment_unit_id,
    
    CASE
        WHEN rider_id IS NULL THEN NULL
        WHEN TRIM(rider_id) = '' THEN NULL
        WHEN UPPER(TRIM(rider_id)) = 'NULL' THEN NULL
        ELSE UPPER(TRIM(REPLACE(rider_id, '#', '')))
    END AS rider_id,

    UPPER(TRIM(REPLACE(status,'#',''))) AS status,

    CASE
        WHEN rider_arrived_at_store IS NULL THEN NULL
        WHEN TRIM(rider_arrived_at_store) = '' THEN NULL
        WHEN UPPER(TRIM(rider_arrived_at_store)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(rider_arrived_at_store)
        )
    END AS rider_arrived_at_store,

    CASE
        WHEN picked_up_at IS NULL THEN NULL
        WHEN TRIM(picked_up_at) = '' THEN NULL
        WHEN UPPER(TRIM(picked_up_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(picked_up_at)
        )
    END AS picked_up_at,

    CASE
        WHEN delivery_started_at IS NULL THEN NULL
        WHEN TRIM(delivery_started_at) = '' THEN NULL
        WHEN UPPER(TRIM(delivery_started_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(delivery_started_at)
        )
    END AS delivery_started_at,

    CASE
        WHEN delivered_at IS NULL THEN NULL
        WHEN TRIM(delivered_at) = '' THEN NULL
        WHEN UPPER(TRIM(delivered_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(delivered_at)
        )
    END AS delivered_at,

    SAFE_CAST(TRIM(delivery_distance) AS FLOAT64) AS delivery_distance,
    UPPER(TRIM(REPLACE(traffic_condition,'#',''))) AS traffic_condition,
    UPPER(TRIM(REPLACE(weather_condition,'#',''))) AS weather_condition,

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
        WHEN failed_at IS NULL THEN NULL
        WHEN TRIM(failed_at) = '' THEN NULL
        WHEN UPPER(TRIM(failed_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(failed_at)
        )
    END AS failed_at,

    CASE
        WHEN failure_reason IS NULL THEN NULL
        WHEN TRIM(failure_reason) = '' THEN NULL
        WHEN UPPER(TRIM(failure_reason)) = 'NULL' THEN NULL
        ELSE UPPER(TRIM(REPLACE(failure_reason, '#', '')))
    END AS failure_reason

FROM {{ source('raw', 'deliveries') }}

QUALIFY ROW_NUMBER() OVER(
    PARTITION BY delivery_id
    ORDER BY delivery_id
) = 1