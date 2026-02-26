-- Convert raw transaction data to staging format
WITH source AS (
    SELECT
        transaction_id,
        customer_id,
        store_id,
        amount,
        transaction_date
    FROM {{ ref('raw_transactions') }}
)
SELECT
    transaction_id,
    customer_id,
    store_id,
    amount,
    transaction_date
FROM source