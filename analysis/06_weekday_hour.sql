-- Question: Which weekdays and hours (Miami time) get the most requests?
SELECT
    dayofweek(created_at) AS weekday_number,
    dayname(created_at) AS weekday,
    hour(created_at) AS hour,
    count(*) AS requests,
    rank() OVER (ORDER BY count(*) DESC) AS volume_rank
FROM mart.fct_requests
WHERE NOT is_duplicate
GROUP BY 1, 2, 3
ORDER BY weekday_number, hour
