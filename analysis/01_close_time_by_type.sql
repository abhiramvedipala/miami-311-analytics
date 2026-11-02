-- Question: What are the median and p90 days to close for each request type, and which types are slowest?
-- Types need 500 closed requests, so one odd ticket cannot top the list. Open requests are not counted.
WITH closed AS (
    SELECT types.request_type, facts.days_to_close
    FROM mart.fct_requests AS facts
    JOIN mart.dim_request_type AS types USING (request_type_key)
    WHERE facts.days_to_close IS NOT NULL AND NOT facts.is_duplicate
),

ranked AS (
    SELECT
        request_type,
        count(*) OVER by_type AS closed_requests,
        quantile_cont(days_to_close, 0.5) OVER by_type AS median_days,
        quantile_cont(days_to_close, 0.9) OVER by_type AS p90_days,
        row_number() OVER by_type AS row_in_type
    FROM closed
    WINDOW by_type AS (PARTITION BY request_type)
)

SELECT
    request_type,
    closed_requests,
    round(median_days, 1) AS median_days,
    round(p90_days, 1) AS p90_days,
    rank() OVER (ORDER BY p90_days DESC) AS p90_rank
FROM ranked
WHERE row_in_type = 1 AND closed_requests >= 500
ORDER BY p90_rank
