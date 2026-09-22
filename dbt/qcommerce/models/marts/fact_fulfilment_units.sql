{{ config(
    materialized='table',
    partition_by={
        'field': 'assigned_to_store_at',
        'data_type': 'timestamp',
        'granularity': 'day'
    },
    cluster_by=['store_id', 'order_id', 'status']
) }}

SELECT
    ifu.fulfilment_unit_id,
    idl.delivery_id,
    ifu.order_id,
    ifu.store_id,
    idl.rider_id,
    ifu.status,

    ifu.assigned_to_store_at,
    ifu.picking_started_at,
    ifu.picking_completed_at,
    ifu.packing_started_at,
    ifu.packing_completed_at,

    idl.rider_arrived_at_store,
    idl.picked_up_at,
    idl.delivery_started_at,
    idl.delivered_at,

    idl.delivery_distance,
    idl.traffic_condition,
    idl.weather_condition,

    ifu.cancelled_at,
    ifu.cancellation_reason,
    ifu.failed_at,
    ifu.failure_reason,
    ifu.completed_at,

    ifu.assignment_to_picking_start_seconds,
    ifu.picking_duration_seconds,
    ifu.packing_duration_seconds,
    ifu.store_processing_duration_seconds,

    idl.pickup_wait_time_seconds,
    idl.pickup_to_delivery_start_seconds,
    idl.transit_duration_seconds,
    idl.store_arrival_to_delivery_seconds,

    -- Fulfilment outcome flags
    CASE
        WHEN ifu.completed_at IS NOT NULL THEN 1
        ELSE 0
    END AS completed_fulfilment_unit_flag,

    CASE
        WHEN ifu.cancelled_at IS NOT NULL THEN 1
        ELSE 0
    END AS cancelled_fulfilment_unit_flag,

    CASE
        WHEN ifu.failed_at IS NOT NULL THEN 1
        ELSE 0
    END AS failed_fulfilment_unit_flag,

    -- Delivery outcome flags
    CASE
        WHEN idl.delivered_at IS NOT NULL THEN 1
        ELSE 0
    END AS delivered_flag,

    CASE
        WHEN idl.cancelled_at IS NOT NULL THEN 1
        ELSE 0
    END AS delivery_cancelled_flag,

    CASE
        WHEN idl.failed_at IS NOT NULL THEN 1
        ELSE 0
    END AS delivery_failed_flag

FROM {{ ref('int_fulfilment_units') }} AS ifu

LEFT JOIN {{ ref('int_deliveries') }} AS idl
    ON ifu.fulfilment_unit_id = idl.fulfilment_unit_id