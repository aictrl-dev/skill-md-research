-- Calculate customer revenue by channel and city
WITH source AS (
    SELECT
        c.channel,
        COALESCE(s.city, '(unknown)') AS city,
        SUM(t.amount) AS total_revenue,
        COUNT(*) AS transaction_count,
        COUNT(DISTINCT t.customer_id) AS unique_customers
    FROM {{ ref('stg_deduped_channels') }} c
    LEFT JOIN {{ ref('stg_transactions') }} t
        ON t.customer_id = c.customer_id
    LEFT JOIN {{ ref('stg_stores') }} s
        ON s.store_id = t.store_id
    GROUP BY
        c.channel,
        COALESCE(s.city, '(unknown)')
    ORDER BY
        c.channel,
        city
)
SELECT
    channel,
    city,
    total_revenue,
    transaction_count,
    unique_customers
FROM source