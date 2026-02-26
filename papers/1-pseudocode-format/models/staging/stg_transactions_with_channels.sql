-- Join transactions with deduplicated customer channels and stores, preserving all transactions
WITH source AS (
    SELECT
        t.transaction_id,
        t.customer_id,
        t.store_id,
        t.amount,
        t.transaction_date,
        COALESCE(ch.channel, '(unknown)') AS channel,
        COALESCE(ch.attributed_at, NULL) AS attributed_at
    FROM {{ ref('raw_transactions') }} t
    LEFT JOIN {{ ref('stg_customer_channels') }} ch
        ON ch.customer_id = t.customer_id
)
SELECT
    source.transaction_id,
    source.customer_id,
    source.store_id,
    source.amount,
    source.transaction_date,
    source.channel,
    source.attributed_at
FROM source