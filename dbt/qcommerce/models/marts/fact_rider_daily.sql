{{ config(
    materialized='table',
    partition_by={
        'field': 'calendar_date',
        'data_type': 'date',
        'granularity': 'day'
    },
    cluster_by=['rider_id']
) }}

WITH rider_date_spine AS (

    SELECT
        r.rider_id,
        d.calendar_date,
        r.vehicle_type,
        r.home_zone

    FROM {{ ref('dim_rider') }} AS r
    CROSS JOIN {{ ref('dim_date') }} AS d

    WHERE d.calendar_date >= r.joined_at
    AND (
        r.deactivated_at IS NULL
        OR d.calendar_date <= r.deactivated_at
    )
),

daily_assignment AS (

    SELECT
        rider_id,
        DATE(offered_at, 'Asia/Kolkata') AS calendar_date,

        COUNT(assignment_id) AS assignment_offers,

        SUM(
            CASE
                WHEN response = 'ACCEPTED' THEN 1
                ELSE 0
            END
        ) AS accepted_assignments,

        SUM(rejected_flag) AS rejected_assignments,
        SUM(expired_flag) AS expired_assignments,
        AVG(response_time_seconds) AS avg_response_time_seconds

    FROM {{ ref('fact_rider_assignments') }}

    GROUP BY 1, 2
),

daily_deliveries AS (

    SELECT
        rider_id,
        DATE(rider_arrived_at_store, 'Asia/Kolkata') AS calendar_date,

        COUNT(delivery_id) AS delivery_count,
        SUM(delivered_flag) AS delivered_count,
        SUM(delivery_cancelled_flag) AS cancelled_delivery_count,

        SUM(delivery_failed_flag) AS failed_delivery_count,
        AVG(transit_duration_seconds) AS avg_transit_duration_seconds

    FROM {{ ref('fact_fulfilment_units') }}
    WHERE delivery_id IS NOT NULL

    GROUP BY 1, 2
)

SELECT
    spine.calendar_date,
    spine.rider_id,
    spine.vehicle_type,
    spine.home_zone,

    COALESCE(asg.assignment_offers, 0) AS assignment_offers,
    COALESCE(asg.accepted_assignments, 0) AS accepted_assignments,
    COALESCE(asg.rejected_assignments, 0) AS rejected_assignments,
    COALESCE(asg.expired_assignments, 0) AS expired_assignments,

    asg.avg_response_time_seconds,

    SAFE_DIVIDE(
        COALESCE(asg.accepted_assignments, 0),
        COALESCE(asg.assignment_offers, 0)
    ) AS acceptance_rate,

    SAFE_DIVIDE(
        COALESCE(asg.rejected_assignments, 0),
        COALESCE(asg.assignment_offers, 0)
    ) AS rejection_rate,

    SAFE_DIVIDE(
        COALESCE(asg.expired_assignments, 0),
        COALESCE(asg.assignment_offers, 0)
    ) AS expiration_rate,

    COALESCE(del.delivery_count, 0) AS delivery_count,
    COALESCE(del.delivered_count, 0) AS delivered_count,
    COALESCE(del.cancelled_delivery_count, 0) AS cancelled_delivery_count,
    COALESCE(del.failed_delivery_count, 0) AS failed_delivery_count,

    del.avg_transit_duration_seconds,

    SAFE_DIVIDE(
        COALESCE(del.delivered_count, 0),
        COALESCE(del.delivery_count, 0)
    ) AS delivery_success_rate

FROM rider_date_spine AS spine

LEFT JOIN daily_assignment AS asg
    ON spine.rider_id = asg.rider_id
    AND spine.calendar_date = asg.calendar_date

LEFT JOIN daily_deliveries AS del
    ON spine.rider_id = del.rider_id
    AND spine.calendar_date = del.calendar_date