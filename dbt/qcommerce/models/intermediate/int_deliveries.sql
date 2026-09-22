{{ config(
    materialized='view',
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

    CASE
        WHEN picked_up_at >= rider_arrived_at_store
            THEN TIMESTAMP_DIFF(
                picked_up_at,
                rider_arrived_at_store,
                SECOND
            )
        ELSE NULL
    END AS pickup_wait_time_seconds,

    CASE
        WHEN delivery_started_at >= picked_up_at
            THEN TIMESTAMP_DIFF(
                delivery_started_at,
                picked_up_at,
                SECOND
            )
        ELSE NULL
    END AS pickup_to_delivery_start_seconds,

    CASE
        WHEN delivered_at >= delivery_started_at
            THEN TIMESTAMP_DIFF(
                delivered_at,
                delivery_started_at,
                SECOND
            )
        ELSE NULL
    END AS transit_duration_seconds,

    CASE
        WHEN delivered_at >= rider_arrived_at_store
            THEN TIMESTAMP_DIFF(
                delivered_at,
                rider_arrived_at_store,
                SECOND
            )
        ELSE NULL
    END AS store_arrival_to_delivery_seconds

FROM {{ ref('stg_deliveries') }}