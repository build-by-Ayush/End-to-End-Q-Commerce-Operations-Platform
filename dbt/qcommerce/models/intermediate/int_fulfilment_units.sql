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
    fulfilment_unit_id,
    order_id,
    store_id,
    status,

    assigned_to_store_at,
    picking_started_at,
    picking_completed_at,
    packing_started_at,
    packing_completed_at,

    cancelled_at,
    cancellation_reason,
    failed_at,
    failure_reason,
    completed_at,

    CASE
        WHEN picking_started_at >= assigned_to_store_at
            THEN TIMESTAMP_DIFF(
                picking_started_at,
                assigned_to_store_at,
                SECOND
            )
        ELSE NULL
    END AS assignment_to_picking_start_seconds,

    CASE
        WHEN picking_completed_at >= picking_started_at
            THEN TIMESTAMP_DIFF(
                picking_completed_at,
                picking_started_at,
                SECOND
            )
        ELSE NULL
    END AS picking_duration_seconds,

    CASE
        WHEN packing_completed_at >= packing_started_at
            THEN TIMESTAMP_DIFF(
                packing_completed_at,
                packing_started_at,
                SECOND
            )
        ELSE NULL
    END AS packing_duration_seconds,

    CASE
        WHEN packing_completed_at >= assigned_to_store_at
            THEN TIMESTAMP_DIFF(
                packing_completed_at,
                assigned_to_store_at,
                SECOND
            )
        ELSE NULL
    END AS store_processing_duration_seconds

FROM {{ ref('stg_fulfilment_units') }}