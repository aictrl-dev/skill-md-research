-- Convert raw store data to staging format
WITH source AS (
    SELECT
        store_id,
        city,
        region
    FROM {{ ref('raw_stores') }}
)
SELECT
    store_id,
    city,
    region
FROM source