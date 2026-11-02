-- Question: What are the median and p90 days to close in each neighborhood (ZIP), and which are slowest?
-- Neighborhoods need 500 closed requests. Open requests are not counted.
WITH closed AS (
    SELECT areas.neighborhood, facts.days_to_close
    FROM mart.fct_requests AS facts
    JOIN mart.dim_neighborhood AS areas USING (neighborhood_key)
    WHERE facts.days_to_close IS NOT NULL AND NOT facts.is_duplicate
),

ranked AS (
    SELECT
        neighborhood,
        count(*) OVER by_area AS closed_requests,
        quantile_cont(days_to_close, 0.5) OVER by_area AS median_days,
        quantile_cont(days_to_close, 0.9) OVER by_area AS p90_days,
        row_number() OVER by_area AS row_in_area
    FROM closed
    WINDOW by_area AS (PARTITION BY neighborhood)
)

SELECT
    neighborhood,
    closed_requests,
    round(median_days, 1) AS median_days,
    round(p90_days, 1) AS p90_days,
    rank() OVER (ORDER BY median_days DESC) AS median_rank
FROM ranked
WHERE row_in_area = 1 AND closed_requests >= 500
ORDER BY median_rank
