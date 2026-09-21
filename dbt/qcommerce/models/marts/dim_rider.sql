{{ config(
    materialized='table',
) }}

SELECT
    rider_id,
    vehicle_type,
    home_zone,
    status,

    joined_at,
    deactivated_at

FROM {{ ref('stg_riders') }}