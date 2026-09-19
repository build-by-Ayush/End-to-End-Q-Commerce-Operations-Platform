{{ config(
    materialized='table',
    partition_by={
        'field': 'recorded_at',
        'data_type': 'timestamp',
        'granularity': 'day'
    },
    cluster_by=['store_id']
) }}

SELECT
    staffing_snapshot_id,
    store_id,

    recorded_at,

    pickers_scheduled,
    pickers_available,
    packers_scheduled,
    packers_available,

    CASE
        WHEN pickers_available < pickers_scheduled THEN TRUE
        ELSE FALSE
    END AS pickers_understaffed,

    CASE
        WHEN packers_available < packers_scheduled THEN TRUE
        ELSE FALSE
    END AS packers_understaffed,

    CASE
        WHEN pickers_available < pickers_scheduled
            THEN pickers_scheduled - pickers_available
        ELSE NULL
    END AS pickers_understaffed_number,

    CASE
        WHEN packers_available < packers_scheduled
            THEN packers_scheduled - packers_available
        ELSE NULL
    END AS packers_understaffed_number

FROM {{ ref('stg_store_staffing') }}