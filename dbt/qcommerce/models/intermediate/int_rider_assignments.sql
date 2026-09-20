{{ config(
    materialized='table',
    partition_by={
        'field': 'offered_at',
        'data_type': 'timestamp',
        'granularity': 'day'
    },
    cluster_by=['delivery_id', 'response']
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
    END AS time_to_expiration_seconds

FROM {{ ref('stg_rider_assignments') }}