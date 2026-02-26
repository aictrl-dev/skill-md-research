-- Convert raw customer data to staging format
WITH source AS (
    SELECT
        customer_id,
        name,
        email,
        signup_date
    FROM {{ ref('raw_customers') }}
)
SELECT
    customer_id,
    name,
    email,
    signup_date
FROM source