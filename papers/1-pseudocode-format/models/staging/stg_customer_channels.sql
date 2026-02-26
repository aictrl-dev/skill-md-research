-- Deduplicate customer_channels to pick primary attribution per customer (earliest per customer)
WITH source AS (
    SELECT
        customer_id,
        channel,
        attributed_at,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id
            ORDER BY attributed_at ASC
        ) AS row_num
    FROM {{ ref('raw_customer_channels') }}
)
SELECT
    customer_id,
    channel,
    attributed_at
FROM source
WHERE row_num = 1