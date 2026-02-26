-- Final mart layer: revenue by channel and city
WITH source AS (
    SELECT
        t.transaction_id,
        t.customer_id,
        t.store_id,
        t.amount,
        t.transaction_date,
        COALESCE(ch.channel, '(unknown)') AS channel,
        COALESCE(s.city, '(unknown)') AS city,
        COALESCE(s.region, '(unknown)') AS region
    FROM {{ ref('stg_transactions_with_channels') }} t
    LEFT JOIN {{ ref('raw_stores') }} s
        ON s.store_id = t.store_id
)
SELECT
    s.channel,
    s.city,
    SUM(s.amount) AS total_revenue,
    COUNT(DISTINCT s.transaction_id) AS transaction_count,
    COUNT(DISTINCT s.customer_id) AS unique_customers
FROM source s
GROUP BY
    s.channel,
    s.city
ORDER BY
    s.channel,
    s.city