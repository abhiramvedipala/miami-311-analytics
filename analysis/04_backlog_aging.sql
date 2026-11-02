-- Question: How many requests are still open, and how old are they?
-- Age is measured at the newest request in the data, so results do not drift with the run date.
WITH as_of AS (
    SELECT max(created_at) AS as_of_time FROM mart.fct_requests
),

aged AS (
    SELECT date_diff('day', created_at, as_of_time) AS age_days
    FROM mart.fct_requests, as_of
    WHERE is_backlog
)

SELECT
    CASE
        WHEN age_days <= 30 THEN '0-30 days'
        WHEN age_days <= 90 THEN '31-90 days'
        WHEN age_days <= 180 THEN '91-180 days'
        WHEN age_days <= 365 THEN '181-365 days'
        ELSE 'Over 365 days'
    END AS age_bucket,
    min(age_days) AS sort_key,
    count(*) AS open_requests,
    round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS share_pct
FROM aged
GROUP BY 1
ORDER BY sort_key
