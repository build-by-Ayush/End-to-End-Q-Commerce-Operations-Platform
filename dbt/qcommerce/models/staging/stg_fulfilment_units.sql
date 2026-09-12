SELECT
    TRIM(fulfilment_unit_id) AS fulfilment_unit_id,
    TRIM(order_id) AS order_id,
    TRIM(store_id) AS store_id,

    UPPER(TRIM(REPLACE(status,'#',''))) AS status,

    CASE
        WHEN assigned_to_store_at IS NULL THEN NULL
        WHEN TRIM(assigned_to_store_at) = '' THEN NULL
        WHEN UPPER(TRIM(assigned_to_store_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(assigned_to_store_at)
        )
    END AS assigned_to_store_at,

    CASE
        WHEN picking_started_at IS NULL THEN NULL
        WHEN TRIM(picking_started_at) = '' THEN NULL
        WHEN UPPER(TRIM(picking_started_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(picking_started_at)
        )
    END AS picking_started_at,

    CASE
        WHEN picking_completed_at IS NULL THEN NULL
        WHEN TRIM(picking_completed_at) = '' THEN NULL
        WHEN UPPER(TRIM(picking_completed_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(picking_completed_at)
        )
    END AS picking_completed_at,

    CASE
        WHEN packing_started_at IS NULL THEN NULL
        WHEN TRIM(packing_started_at) = '' THEN NULL
        WHEN UPPER(TRIM(packing_started_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(packing_started_at)
        )
    END AS packing_started_at,

    CASE
        WHEN packing_completed_at IS NULL THEN NULL
        WHEN TRIM(packing_completed_at) = '' THEN NULL
        WHEN UPPER(TRIM(packing_completed_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(packing_completed_at)
        )
    END AS packing_completed_at,

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
    END AS failure_reason,

    CASE
        WHEN completed_at IS NULL THEN NULL
        WHEN TRIM(completed_at) = '' THEN NULL
        WHEN UPPER(TRIM(completed_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(completed_at)
        )
    END AS completed_at

FROM {{ source('raw', 'fulfilment_units') }}

QUALIFY ROW_NUMBER() OVER(
    PARTITION BY fulfilment_unit_id
    ORDER BY fulfilment_unit_id
) = 1