-- Question: How does request volume change month over month?
-- The latest month is dropped when the data stops before it ends, since a partial month would read as a collapse.
WITH monthly AS (
    SELECT date_trunc('month', created_at)::date AS month, count(*) AS requests
    FROM mart.fct_requests
    WHERE NOT is_duplicate
    GROUP BY 1
),

last_day AS (
    SELECT max(created_at)::date AS last_date FROM mart.fct_requests
)

SELECT
    month,
    requests,
    requests - lag(requests) OVER (ORDER BY month) AS change,
    round(100.0 * (requests - lag(requests) OVER (ORDER BY month)) / lag(requests) OVER (ORDER BY month), 1) AS change_pct
FROM monthly, last_day
WHERE last_day(month) <= last_date
ORDER BY month
