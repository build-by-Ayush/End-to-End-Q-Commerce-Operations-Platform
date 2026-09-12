SELECT
    TRIM(order_item_id) AS order_item_id,
    TRIM(order_id) AS order_id,
    TRIM(fulfilment_unit_id) AS fulfilment_unit_id,
    UPPER(TRIM(REPLACE(product_id,'#',''))) AS product_id,
    SAFE_CAST(quantity AS INT64) AS quantity
FROM {{ source('raw', 'order_items') }}

QUALIFY ROW_NUMBER() OVER(
    PARTITION BY order_item_id
    ORDER BY order_item_id
) = 1