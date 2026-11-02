-- Question: Where does the same problem keep coming back?
-- A repeat is a request of the same type at the same point (about 11 m) within 30 days of the previous one.
-- Points with 10 or more request types are left out: unrelated problems sharing one spot means a facility
-- or default address, not a location with recurring trouble. Police assistance is inter-agency work.
WITH shared_points AS (
    SELECT round(latitude, 4) AS latitude, round(longitude, 4) AS longitude
    FROM mart.fct_requests
    GROUP BY 1, 2
    HAVING count(DISTINCT request_type_key) >= 10
),

located AS (
    SELECT
        types.request_type,
        areas.neighborhood,
        round(facts.latitude, 4) AS latitude,
        round(facts.longitude, 4) AS longitude,
        facts.created_at,
        lag(facts.created_at) OVER (
            PARTITION BY facts.request_type_key, round(facts.latitude, 4), round(facts.longitude, 4)
            ORDER BY facts.created_at
        ) AS previous_at
    FROM mart.fct_requests AS facts
    JOIN mart.dim_request_type AS types USING (request_type_key)
    JOIN mart.dim_neighborhood AS areas USING (neighborhood_key)
    ANTI JOIN shared_points
        ON round(facts.latitude, 4) = shared_points.latitude AND round(facts.longitude, 4) = shared_points.longitude
    WHERE NOT facts.is_duplicate AND facts.latitude IS NOT NULL AND facts.longitude IS NOT NULL
        AND types.request_type NOT IN ('ASU POLICE ASSISTANCE', 'Police Request for ASD Assistance')
)

SELECT
    request_type,
    neighborhood,
    latitude,
    longitude,
    count(*) AS requests,
    count(*) FILTER (date_diff('day', previous_at, created_at) <= 30) AS repeats_within_30_days
FROM located
GROUP BY ALL
HAVING repeats_within_30_days > 0
ORDER BY repeats_within_30_days DESC, requests DESC
LIMIT 20
