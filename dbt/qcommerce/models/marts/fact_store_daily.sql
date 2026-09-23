{{ config(
    materialized='table',
    partition_by={
        'field': 'calendar_date',
        'data_type': 'date',
        'granularity': 'day'
    },
    cluster_by=['store_id']
) }}

WITH store_date_spine AS (

    SELECT
        s.store_id,
        s.store_name,
        d.calendar_date

    FROM {{ ref('dim_store') }} AS s
    CROSS JOIN {{ ref('dim_date') }} AS d

    WHERE d.calendar_date >= s.opened_at
    AND (
        s.closed_at IS NULL
        OR d.calendar_date <= s.closed_at
    )
),

daily_units AS (

    SELECT
        store_id,

        DATE(
            assigned_to_store_at,
            'Asia/Kolkata'
        ) AS calendar_date,

        COUNT(DISTINCT order_id) AS orders_served,
        COUNT(*) AS fulfilment_units_handled,

        SUM(completed_fulfilment_unit_flag) AS completed_units,
        SUM(cancelled_fulfilment_unit_flag) AS cancelled_units,
        SUM(failed_fulfilment_unit_flag) AS failed_units,

        AVG(store_processing_duration_seconds) AS avg_store_processing_seconds,
        AVG(store_arrival_to_delivery_seconds) AS avg_store_arrival_to_delivery_seconds,
        COUNT(delivery_id) AS delivery_attempts,

        SUM(delivered_flag) AS delivered_units,
        SUM(delivery_cancelled_flag) AS delivery_cancelled_units,
        SUM(delivery_failed_flag) AS delivery_failed_units

    FROM {{ ref('fact_fulfilment_units') }}
    GROUP BY 1, 2
),

daily_staff AS (

    SELECT
        store_id,

        DATE(
            recorded_at,
            'Asia/Kolkata'
        ) AS calendar_date,

        COUNT(*) AS total_staffing_snapshots,
        SUM(understaffed_flag) AS understaffed_snapshots,
        AVG(understaffed_flag) AS understaffed_snapshot_rate,
        AVG(picker_availability_rate) AS avg_picker_availability_rate,
        AVG(packer_availability_rate) AS avg_packer_availability_rate

    FROM {{ ref('fact_store_staffing') }}
    GROUP BY 1, 2
)

SELECT
    spine.calendar_date,
    spine.store_id,
    spine.store_name,

    COALESCE(units.orders_served,0) AS orders_served,
    COALESCE(units.fulfilment_units_handled,0) AS fulfilment_units_handled,

    COALESCE(units.completed_units,0) AS completed_units,
    COALESCE(units.cancelled_units,0) AS cancelled_units,
    COALESCE(units.failed_units,0) AS failed_units,
    units.avg_store_processing_seconds,


    COALESCE(units.delivery_attempts,0) AS delivery_attempts,
    COALESCE(units.delivered_units,0) AS delivered_units,
    COALESCE(units.delivery_cancelled_units,0) AS delivery_cancelled_units,
    COALESCE(units.delivery_failed_units,0) AS delivery_failed_units,
    units.avg_store_arrival_to_delivery_seconds,

    SAFE_DIVIDE(
        COALESCE(units.delivered_units, 0),
        COALESCE(units.delivery_attempts, 0)
    ) AS delivery_success_rate,

    COALESCE(staff.total_staffing_snapshots,0) AS total_staffing_snapshots,
    COALESCE(staff.understaffed_snapshots,0) AS understaffed_snapshots,
    COALESCE(staff.understaffed_snapshot_rate,0) AS understaffed_snapshot_rate,
    staff.avg_picker_availability_rate,
    staff.avg_packer_availability_rate

FROM store_date_spine AS spine

LEFT JOIN daily_units AS units
    ON spine.store_id = units.store_id
    AND spine.calendar_date = units.calendar_date

LEFT JOIN daily_staff AS staff
    ON spine.store_id = staff.store_id
    AND spine.calendar_date = staff.calendar_date