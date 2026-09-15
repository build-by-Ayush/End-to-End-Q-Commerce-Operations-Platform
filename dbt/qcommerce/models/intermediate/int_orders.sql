{{ config(
    materialized='table',
    partition_by={
        'field': 'payment_success_at',
        'data_type': 'timestamp',
        'granularity': 'day'
    },
    cluster_by=['delivery_zone', 'status']
) }}

SELECT
    order_id,
    customer_id,

    created_at,
    payment_success_at,

    delivery_latitude,
    delivery_longitude,
    delivery_zone,

    status,
    cancelled_at,
    cancellation_reason,
    failure_reason,

    TIMESTAMP_DIFF(
        payment_success_at,
        created_at,
        SECOND
    ) AS payment_processing_seconds,

    TIMESTAMP_DIFF(
        cancelled_at,
        payment_success_at,
        SECOND
    ) AS time_to_cancellation_seconds

FROM {{ ref('stg_orders') }}