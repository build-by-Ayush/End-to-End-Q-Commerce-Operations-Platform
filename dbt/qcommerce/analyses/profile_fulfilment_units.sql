SELECT
    --OVERALL TABLE
    COUNT(*) AS total_rows,


    --fulfilment_unit_id
    COUNTIF(fulfilment_unit_id IS NULL) AS fulfilment_unit_id_null_count,
    COUNTIF(fulfilment_unit_id = '') AS fulfilment_unit_id_blank_count,
    COUNT(DISTINCT fulfilment_unit_id) AS fulfilment_unit_id_distinct_count,
    COUNT(*) - COUNT(DISTINCT fulfilment_unit_id) AS fulfilment_unit_id_duplicate_row_count,



    --order_id
    COUNTIF(order_id IS NULL) AS order_id_null_count,
    COUNTIF(order_id = '') AS order_id_blank_count,
    COUNT(DISTINCT order_id) AS order_id_distinct_count,
    COUNT(*) - COUNT(DISTINCT order_id) AS order_id_duplicate_row_count,



    --store_id
    COUNTIF(store_id IS NULL) AS store_id_null_count,
    COUNTIF(store_id = '') AS store_id_blank_count,
    COUNT(DISTINCT store_id) AS store_id_distinct_count,
    COUNT(*) - COUNT(DISTINCT store_id) AS store_id_duplicate_row_count,



    --STATUS
    COUNTIF(status IS NULL) AS status_null_count,
    COUNTIF(status = '') AS status_blank_count,
    COUNT(DISTINCT status) AS status_distinct_count,
    COUNTIF(status != TRIM(status)) AS status_whitespace_count,
   

    --assigned_to_store_at
    COUNTIF(assigned_to_store_at IS NULL) AS assigned_to_store_at_null_count,
    COUNTIF(assigned_to_store_at = '') AS assigned_to_store_at_blank_count,
    COUNTIF(
        assigned_to_store_at IS NOT NULL
        AND assigned_to_store_at != ''
        AND NOT REGEXP_CONTAINS(
            assigned_to_store_at,
            r'^\d{2}[-/]\d{2}[-/]\d{4} \d{2}:\d{2}(?::\d{2})?$'
        )
        AND NOT REGEXP_CONTAINS(
            assigned_to_store_at,
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?$'
        )
    ) AS assigned_to_store_at_unrecognized_format_count,



    --picking_started_at
    COUNTIF(picking_started_at IS NULL) AS picked_up_null_count,
    COUNTIF(picking_started_at = '') AS picked_up_blank_count,
    COUNTIF(
        picking_started_at IS NOT NULL
        AND picking_started_at != ''
        AND NOT REGEXP_CONTAINS(
            picking_started_at,
            r'^\d{2}[-/]\d{2}[-/]\d{4} \d{2}:\d{2}(?::\d{2})?$'
        )
        AND NOT REGEXP_CONTAINS(
            picking_started_at,
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?$'
        )
    ) AS picked_up_unrecognized_format_count,

    

    --DELIVERY STARTED AT       
    COUNTIF(picking_completed_at IS NULL) AS picking_completed_null_count,
    COUNTIF(picking_completed_at = '') AS picking_completed_blank_count,
    COUNTIF(
        picking_completed_at IS NOT NULL
        AND picking_completed_at != ''
        AND NOT REGEXP_CONTAINS(
            picking_completed_at,
            r'^\d{2}[-/]\d{2}[-/]\d{4} \d{2}:\d{2}(?::\d{2})?$'
        )
        AND NOT REGEXP_CONTAINS(
            picking_completed_at,
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?$'
        )
    ) AS picking_completed_unrecognized_format_count,

    

    --packing_started_at
    COUNTIF(packing_started_at IS NULL) AS packing_started_null_count,
    COUNTIF(packing_started_at = '') AS packing_started_blank_count,
    COUNTIF(
        packing_started_at IS NOT NULL
        AND packing_started_at != ''
        AND NOT REGEXP_CONTAINS(
            packing_started_at,
            r'^\d{2}[-/]\d{2}[-/]\d{4} \d{2}:\d{2}(?::\d{2})?$'
        )
        AND NOT REGEXP_CONTAINS(
            packing_started_at,
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?$'
        )
    ) AS packing_started_unrecognized_format_count,


    --packing_completed_at
    COUNTIF(packing_completed_at IS NULL) AS packing_completed_null_count,
    COUNTIF(packing_completed_at = '') AS packing_completed_blank_count,
    COUNTIF(
        packing_completed_at IS NOT NULL
        AND packing_completed_at != ''
        AND NOT REGEXP_CONTAINS(
            packing_completed_at,
            r'^\d{2}[-/]\d{2}[-/]\d{4} \d{2}:\d{2}(?::\d{2})?$'
        )
        AND NOT REGEXP_CONTAINS(
            packing_completed_at,
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?$'
        )
    ) AS packing_completed_unrecognized_format_count,
   

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



FROM `q-commerce-operations-platform.raw.fulfilment_units`;