-- Calculate customer revenue by attribution channel and store city
WITH source AS (
    SELECT
        t.transaction_id,
        t.customer_id,
        t.store_id,
        t.amount,
        t.transaction_date,
        COALESCE(ch.channel, '(unknown)') AS channel,
        COALESCE(s.city, '(unknown)') AS city
    FROM {{ ref('stg_transactions') }} t
    LEFT JOIN {{ ref('stg_customer_channels') }} ch
        ON ch.customer_id = t.customer_id
    LEFT JOIN {{ ref('stg_stores') }} s
        ON s.store_id = t.store_id
)
SELECT
    channel,
    city,
    SUM(amount) AS total_revenue,
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT customer_id) AS unique_customers
FROM source
GROUP BY
    channel,
    city
ORDER BY
    total_revenue DESC