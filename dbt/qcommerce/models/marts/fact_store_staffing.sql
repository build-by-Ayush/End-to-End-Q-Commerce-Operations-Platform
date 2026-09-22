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

    -- Picker staffing
    CASE
        WHEN pickers_available < pickers_scheduled THEN 1
        ELSE 0
    END AS pickers_understaffed_flag,

    CASE
        WHEN pickers_available < pickers_scheduled
            THEN pickers_scheduled - pickers_available
        ELSE 0
    END AS pickers_understaffed_number,

    CASE
        WHEN pickers_scheduled > 0
            THEN SAFE_DIVIDE(
                pickers_available,
                pickers_scheduled
            )
        ELSE NULL
    END AS picker_availability_rate,

    -- Packer staffing
    CASE
        WHEN packers_available < packers_scheduled THEN 1
        ELSE 0
    END AS packers_understaffed_flag,

    CASE
        WHEN packers_available < packers_scheduled
            THEN packers_scheduled - packers_available
        ELSE 0
    END AS packers_understaffed_number,

    CASE
        WHEN packers_scheduled > 0
            THEN SAFE_DIVIDE(
                packers_available,
                packers_scheduled
            )
        ELSE NULL
    END AS packer_availability_rate,

    -- Overall staffing condition
    CASE
        WHEN pickers_available < pickers_scheduled
          OR packers_available < packers_scheduled
        THEN 1
        ELSE 0
    END AS understaffed_flag

FROM {{ ref('stg_store_staffing') }}