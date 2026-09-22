{{ config(
    materialized='table',
    partition_by={
        'field': 'offered_at',
        'data_type': 'timestamp',
        'granularity': 'day'
    },
    cluster_by=['delivery_id', 'rider_id', 'response']
) }}

SELECT
    assignment_id,
    delivery_id,
    rider_id,

    offered_at,
    responded_at,
    expired_at,

    response,
    rejection_reason,

    CASE
        WHEN responded_at >= offered_at
            THEN TIMESTAMP_DIFF(
                responded_at,
                offered_at,
                SECOND
            )
        ELSE NULL
    END AS response_time_seconds,

    CASE
        WHEN expired_at >= offered_at
            THEN TIMESTAMP_DIFF(
                expired_at,
                offered_at,
                SECOND
            )
        ELSE NULL
    END AS time_to_expiration_seconds,

    CASE
        WHEN responded_at IS NOT NULL THEN 1
        ELSE 0
    END AS responded_flag,

    CASE
        WHEN expired_at IS NOT NULL THEN 1
        ELSE 0
    END AS expired_flag,

    CASE
        WHEN rejection_reason IS NOT NULL
            AND TRIM(rejection_reason) != ''
        THEN 1
        ELSE 0
    END AS rejected_flag

FROM {{ ref('stg_rider_assignments') }}