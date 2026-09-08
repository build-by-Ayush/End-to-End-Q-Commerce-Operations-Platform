SELECT
    -- Overall table
    COUNT(*) AS total_rows,

    -- customer_id
    COUNTIF(customer_id IS NULL) AS customer_id_null_count,
    COUNTIF(customer_id = '') AS customer_id_blank_count,
    COUNT(DISTINCT customer_id) AS customer_id_distinct_count,

    -- zone_id
    COUNTIF(zone_id IS NULL) AS zone_id_null_count,
    COUNTIF(zone_id = '') AS zone_id_blank_count,
    COUNT(DISTINCT zone_id) AS zone_id_distinct_count,
    COUNTIF(zone_id != TRIM(zone_id)) AS zone_id_whitespace_count,

    -- latitude
    COUNTIF(latitude IS NULL) AS latitude_null_count,
    COUNTIF(latitude = '') AS latitude_blank_count,
    COUNTIF(
        latitude IS NOT NULL
        AND latitude != ''
        AND SAFE_CAST(latitude AS FLOAT64) IS NULL
    ) AS latitude_invalid_numeric_count,
    COUNTIF(
        SAFE_CAST(latitude AS FLOAT64) < -90
        OR SAFE_CAST(latitude AS FLOAT64) > 90
    ) AS latitude_out_of_range_count,

    -- longitude
    COUNTIF(longitude IS NULL) AS longitude_null_count,
    COUNTIF(longitude = '') AS longitude_blank_count,
    COUNTIF(
        longitude IS NOT NULL
        AND longitude != ''
        AND SAFE_CAST(longitude AS FLOAT64) IS NULL
    ) AS longitude_invalid_numeric_count,
    COUNTIF(
        SAFE_CAST(longitude AS FLOAT64) < -180
        OR SAFE_CAST(longitude AS FLOAT64) > 180
    ) AS longitude_out_of_range_count

FROM `q-commerce-operations-platform.raw.customers`;