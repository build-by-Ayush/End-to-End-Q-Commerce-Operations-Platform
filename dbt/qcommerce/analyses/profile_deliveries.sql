SELECT
    --OVERALL TABLE
    COUNT(*) AS total_rows,


    --DELIVERY ID
    COUNTIF(delivery_id IS NULL) AS delivery_id_null_count,
    COUNTIF(delivery_id = '') AS delivery_id_blank_count,
    COUNT(DISTINCT delivery_id) AS delivery_id_distinct_count,
    COUNT(*) - COUNT(DISTINCT delivery_id) AS delivery_id_duplicate_row_count,



    --FULFILMENT UNIT ID
    COUNTIF(fulfilment_unit_id IS NULL) AS fulfilment_unit_id_null_count,
    COUNTIF(fulfilment_unit_id = '') AS fulfilment_unit_id_blank_count,
    COUNT(DISTINCT fulfilment_unit_id) AS fulfilment_unit_id_distinct_count,
    COUNT(*) - COUNT(DISTINCT fulfilment_unit_id) AS fulfilment_unit_id_duplicate_row_count,



    --RIDER ID
    COUNTIF(rider_id IS NULL) AS rider_id_null_count,
    COUNTIF(rider_id = '') AS rider_id_blank_count,
    COUNT(DISTINCT rider_id) AS rider_id_distinct_count,
    COUNT(*) - COUNT(DISTINCT rider_id) AS rider_id_duplicate_row_count,



    --STATUS
    COUNTIF(status IS NULL) AS status_null_count,
    COUNTIF(status = '') AS status_blank_count,
    COUNT(DISTINCT status) AS status_distinct_count,
    COUNTIF(status != TRIM(status)) AS status_whitespace_count,

    

    --DELIVERY DISTANCE
    COUNTIF(delivery_distance IS NULL) AS distance_null_count,
    COUNTIF(delivery_distance = '') AS distance_blank_count,

    COUNTIF(
        delivery_distance IS NOT NULL
        AND delivery_distance != ''
        AND SAFE_CAST(delivery_distance AS FLOAT64) IS NULL
    ) AS distance_invalid_numeric_count,

    COUNTIF(
        SAFE_CAST(delivery_distance AS FLOAT64) < 0
    ) AS distance_negative_count,

    AVG(
        SAFE_CAST(delivery_distance AS FLOAT64)
    ) AS avg_distance,

    MIN(
        SAFE_CAST(delivery_distance AS FLOAT64)
    ) AS min_distance,

    MAX(
        SAFE_CAST(delivery_distance AS FLOAT64)
    ) AS max_distance,



    --TRAFFIC CONDITION
    COUNTIF(traffic_condition IS NULL) AS traffic_condition_null_count,
    COUNTIF(traffic_condition = '') AS traffic_condition_blank_count,
    COUNT(DISTINCT traffic_condition) AS traffic_condition_distinct_count,
    COUNTIF(traffic_condition != TRIM(traffic_condition)) AS traffic_condition_whitespace_count,



    --WEATHER CONDITION
    COUNTIF(weather_condition IS NULL) AS weather_condition_null_count,
    COUNTIF(weather_condition = '') AS weather_condition_blank_count,
    COUNT(DISTINCT weather_condition) AS weather_condition_distinct_count,
    COUNTIF(weather_condition != TRIM(weather_condition)) AS weather_condition_whitespace_count,

   

    --RIDER ARRIVED AT STORE
    COUNTIF(rider_arrived_at_store IS NULL) AS rider_arrived_null_count,
    COUNTIF(rider_arrived_at_store = '') AS rider_arrived_blank_count,
    COUNTIF(
        rider_arrived_at_store IS NOT NULL
        AND rider_arrived_at_store != ''
        AND NOT REGEXP_CONTAINS(
            rider_arrived_at_store,
            r'^\d{2}[-/]\d{2}[-/]\d{4} \d{2}:\d{2}(?::\d{2})?$'
        )
        AND NOT REGEXP_CONTAINS(
            rider_arrived_at_store,
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?$'
        )
    ) AS rider_arrived_unrecognized_format_count,



    --PICKED UP AT
    COUNTIF(picked_up_at IS NULL) AS picked_up_null_count,
    COUNTIF(picked_up_at = '') AS picked_up_blank_count,
    COUNTIF(
        picked_up_at IS NOT NULL
        AND picked_up_at != ''
        AND NOT REGEXP_CONTAINS(
            picked_up_at,
            r'^\d{2}[-/]\d{2}[-/]\d{4} \d{2}:\d{2}(?::\d{2})?$'
        )
        AND NOT REGEXP_CONTAINS(
            picked_up_at,
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?$'
        )
    ) AS picked_up_unrecognized_format_count,

    

    --DELIVERY STARTED AT       
    COUNTIF(delivery_started_at IS NULL) AS delivery_started_null_count,
    COUNTIF(delivery_started_at = '') AS delivery_started_blank_count,
    COUNTIF(
        delivery_started_at IS NOT NULL
        AND delivery_started_at != ''
        AND NOT REGEXP_CONTAINS(
            delivery_started_at,
            r'^\d{2}[-/]\d{2}[-/]\d{4} \d{2}:\d{2}(?::\d{2})?$'
        )
        AND NOT REGEXP_CONTAINS(
            delivery_started_at,
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?$'
        )
    ) AS delivery_started_unrecognized_format_count,

    

    --DELIVERED AT
    COUNTIF(delivered_at IS NULL) AS delivered_null_count,
    COUNTIF(delivered_at = '') AS delivered_blank_count,
    COUNTIF(
        delivered_at IS NOT NULL
        AND delivered_at != ''
        AND NOT REGEXP_CONTAINS(
            delivered_at,
            r'^\d{2}[-/]\d{2}[-/]\d{4} \d{2}:\d{2}(?::\d{2})?$'
        )
        AND NOT REGEXP_CONTAINS(
            delivered_at,
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?$'
        )
    ) AS delivered_unrecognized_format_count,

   

    --CANCELLED AT
    COUNTIF(cancelled_at IS NULL) AS cancelled_at_null_count,
    COUNTIF(cancelled_at = '') AS cancelled_at_blank_count,



    --FAILED AT
    COUNTIF(failed_at IS NULL) AS failed_at_null_count,
    COUNTIF(failed_at = '') AS failed_at_blank_count,

   

    --CANCELLATION REASON
    COUNTIF(cancellation_reason IS NULL) AS cancellation_reason_null_count,
    COUNTIF(cancellation_reason = '') AS cancellation_reason_blank_count,
    COUNTIF(cancellation_reason != TRIM(cancellation_reason)) AS cancellation_reason_whitespace_count,
    COUNT(DISTINCT cancellation_reason) AS cancellation_reason_distinct_count,



    --FAILURE REASON
    COUNTIF(failure_reason IS NULL) AS failure_reason_null_count,
    COUNTIF(failure_reason = '') AS failure_reason_blank_count,
    COUNTIF(failure_reason != TRIM(failure_reason)) AS failure_reason_whitespace_count,
    COUNT(DISTINCT failure_reason) AS failure_reason_distinct_count

FROM `q-commerce-operations-platform.raw.deliveries`;