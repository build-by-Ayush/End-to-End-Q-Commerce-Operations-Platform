{{ config(
    materialized='table',
) }}

SELECT
    store_id,
    store_name,
    zone,

    latitude,
    longitude,
    baseline_capacity,
    status,

    opened_at,
    closed_at

FROM {{ ref('stg_stores') }}