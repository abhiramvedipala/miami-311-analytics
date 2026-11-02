-- Question: When were many old requests of one type closed on a single day?
SELECT
    types.request_type,
    facts.closed_at::date AS closed_date,
    count(*) AS requests,
    round(median(facts.days_to_close), 1) AS median_age_days
FROM mart.fct_requests AS facts
JOIN mart.dim_request_type AS types USING (request_type_key)
WHERE facts.is_bulk_close
GROUP BY 1, 2
ORDER BY requests DESC
