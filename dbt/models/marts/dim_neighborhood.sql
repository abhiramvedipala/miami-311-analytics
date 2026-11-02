-- One row per ZIP code, the finest area the source has for all rows. The source
-- has no neighborhood field and most rows share one municipality.
select
    zip as neighborhood_key,
    mode(municipality) as municipality,
    zip::varchar || ' (' || mode(municipality) || ')' as neighborhood
from {{ ref('stg_requests') }}
where zip is not null
group by zip
