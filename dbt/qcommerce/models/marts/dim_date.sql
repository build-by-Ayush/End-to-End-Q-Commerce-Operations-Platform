{{ config(
    materialized='table'
) }}

WITH date_bounds AS (

    -- Order activity
    SELECT
        MIN(DATE(created_at, 'Asia/Kolkata')) AS min_date,
        MAX(DATE(created_at, 'Asia/Kolkata')) AS max_date
    FROM {{ ref('int_orders') }}

    UNION ALL

    -- Fulfilment-unit activity
    SELECT
        MIN(DATE(assigned_to_store_at, 'Asia/Kolkata')) AS min_date,
        MAX(DATE(assigned_to_store_at, 'Asia/Kolkata')) AS max_date
    FROM {{ ref('int_fulfilment_units') }}

    UNION ALL

    -- Delivery activity
    SELECT
        MIN(DATE(rider_arrived_at_store, 'Asia/Kolkata')) AS min_date,
        MAX(DATE(rider_arrived_at_store, 'Asia/Kolkata')) AS max_date
    FROM {{ ref('int_deliveries') }}

    UNION ALL

    -- Rider assignment activity
    SELECT
        MIN(DATE(offered_at, 'Asia/Kolkata')) AS min_date,
        MAX(DATE(offered_at, 'Asia/Kolkata')) AS max_date
    FROM {{ ref('int_rider_assignments') }}

    UNION ALL

    -- Store staffing activity
    SELECT
        MIN(DATE(recorded_at, 'Asia/Kolkata')) AS min_date,
        MAX(DATE(recorded_at, 'Asia/Kolkata')) AS max_date
    FROM {{ ref('int_store_staffing') }}
),

overall_bounds AS (

    SELECT
        MIN(min_date) AS min_date,
        MAX(max_date) AS max_date
    FROM date_bounds
),

calendar AS (

    SELECT
        calendar_date
    FROM overall_bounds,
    UNNEST(
        GENERATE_DATE_ARRAY(
            min_date,
            max_date
        )
    ) AS calendar_date
)

SELECT
    -- Natural calendar key in YYYYMMDD format
    CAST(FORMAT_DATE('%Y%m%d', calendar_date) AS INT64) AS date_key,

    -- Actual calendar date
    calendar_date,

    -- Day attributes
    EXTRACT(DAY FROM calendar_date) AS day_of_month,

    MOD(
        EXTRACT(DAYOFWEEK FROM calendar_date) + 5,
        7
    ) + 1 AS day_of_week_number,

    FORMAT_DATE('%A', calendar_date) AS day_name,

    -- Week attributes
    EXTRACT(ISOWEEK FROM calendar_date) AS iso_week_number,

    EXTRACT(ISOYEAR FROM calendar_date) AS iso_year,

    DATE_TRUNC(
        calendar_date,
        WEEK(MONDAY)
    ) AS week_start_date,

    -- Month attributes
    EXTRACT(MONTH FROM calendar_date) AS month_number,

    FORMAT_DATE('%B', calendar_date) AS month_name,

    FORMAT_DATE('%Y-%m', calendar_date) AS year_month,

    DATE_TRUNC(
        calendar_date,
        MONTH
    ) AS month_start_date,

    -- Quarter attributes
    EXTRACT(QUARTER FROM calendar_date) AS quarter_number,

    CONCAT(
        'Q',
        CAST(EXTRACT(QUARTER FROM calendar_date) AS STRING)
    ) AS quarter_name,

    DATE_TRUNC(
        calendar_date,
        QUARTER
    ) AS quarter_start_date,

    -- Year attributes
    EXTRACT(YEAR FROM calendar_date) AS year,

    DATE_TRUNC(
        calendar_date,
        YEAR
    ) AS year_start_date,

    -- Business flags
    CASE
        WHEN MOD(
            EXTRACT(DAYOFWEEK FROM calendar_date) + 5,
            7
        ) + 1 IN (6, 7)
        THEN TRUE
        ELSE FALSE
    END AS is_weekend

FROM calendar