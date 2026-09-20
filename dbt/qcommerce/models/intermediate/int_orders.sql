{{ config(
    materialized='table',
    partition_by={
        'field': 'payment_success_at',
        'data_type': 'timestamp',
        'granularity': 'day'
    },
    cluster_by=['delivery_zone', 'status']
) }}

WITH order_item_summary AS (
    SELECT 
        order_id,
        COUNT(DISTINCT fulfilment_unit_id) AS fulfilment_unit_count,
        COUNT(DISTINCT product_id) AS unique_product_count,
        COUNT(*) AS order_item_count,
        SUM(quantity) AS total_quantity
    FROM {{ ref('stg_order_items') }}
    GROUP BY order_id
)
SELECT
    so.order_id,
    so.customer_id,

    so.created_at,
    so.payment_success_at,

    so.delivery_latitude,
    so.delivery_longitude,
    so.delivery_zone,

    so.status,
    ois.fulfilment_unit_count,
    ois.unique_product_count,
    ois.total_quantity,
    ois.order_item_count,

    so.cancelled_at,
    so.cancellation_reason,
    so.failure_reason,

    CASE
        WHEN payment_success_at >= created_at
            THEN TIMESTAMP_DIFF(
                payment_success_at,
                created_at,
                SECOND
            )
        ELSE NULL
    END AS payment_processing_seconds,

    CASE
        WHEN cancelled_at >= payment_success_at
            THEN TIMESTAMP_DIFF(
                cancelled_at,
                payment_success_at,
                SECOND
            )
        ELSE NULL
    END AS time_to_cancellation_seconds

FROM {{ ref('stg_orders') }} AS so
LEFT JOIN order_item_summary AS ois
    ON so.order_id = ois.order_id