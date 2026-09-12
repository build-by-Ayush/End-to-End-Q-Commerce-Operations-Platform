SELECT
    TRIM(assignment_id) AS assignment_id,
    TRIM(delivery_id) AS delivery_id,
    TRIM(rider_id) AS rider_id,

    CASE
        WHEN offered_at IS NULL THEN NULL
        WHEN TRIM(offered_at) = '' THEN NULL
        WHEN UPPER(TRIM(offered_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(offered_at)
        )
    END AS offered_at,

    CASE
        WHEN responded_at IS NULL THEN NULL
        WHEN TRIM(responded_at) = '' THEN NULL
        WHEN UPPER(TRIM(responded_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(responded_at)
        )
    END AS responded_at,

    CASE
        WHEN expired_at IS NULL THEN NULL
        WHEN TRIM(expired_at) = '' THEN NULL
        WHEN UPPER(TRIM(expired_at)) = 'NULL' THEN NULL
        ELSE SAFE.PARSE_TIMESTAMP(
            '%d-%m-%Y %H:%M',
            TRIM(expired_at)
        )
    END AS expired_at,

    UPPER(TRIM(REPLACE(response,'#',''))) AS response,

    CASE
        WHEN rejection_reason IS NULL THEN NULL
        WHEN TRIM(rejection_reason) = '' THEN NULL
        WHEN UPPER(TRIM(rejection_reason)) = 'NULL' THEN NULL
        ELSE UPPER(TRIM(REPLACE(rejection_reason, '#', '')))
    END AS rejection_reason

FROM {{ source('raw', 'rider_assignments') }}

QUALIFY ROW_NUMBER() OVER(
    PARTITION BY assignment_id
    ORDER BY assignment_id
) = 1