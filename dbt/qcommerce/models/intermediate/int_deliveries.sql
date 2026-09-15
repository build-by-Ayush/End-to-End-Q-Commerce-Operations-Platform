{{ config(
    materialized='table',
    partition_by={
        'field': 'rider_arrived_at_store',
        'data_type': 'timestamp',
        'granularity': 'day'
    },
    cluster_by=['fulfilment_unit_id', 'rider_id', 'status']
) }}

SELECT
    delivery_id,
    fulfilment_unit_id,
    rider_id,

    status,

    rider_arrived_at_store,
    picked_up_at,
    delivery_started_at,
    delivered_at,

    delivery_distance,
    traffic_condition,
    weather_condition,

    cancelled_at,
    cancellation_reason,
    failed_at,
    failure_reason,

    TIMESTAMP_DIFF(
        picked_up_at,
        rider_arrived_at_store,
        SECOND
    ) AS pickup_wait_time_seconds,

    TIMESTAMP_DIFF(
        delivery_started_at,
        picked_up_at,
        SECOND
    ) AS pickup_to_delivery_start_seconds,

    TIMESTAMP_DIFF(
        delivered_at,
        delivery_started_at,
        SECOND
    ) AS transit_duration_seconds,

    TIMESTAMP_DIFF(
        delivered_at,
        rider_arrived_at_store,
        SECOND
    ) AS store_arrival_to_delivery_seconds

FROM {{ ref('stg_deliveries') }}