-- One row per request type. Labels in the crosswalk share a type across both
-- source systems; any other label keeps its own name.
with labels as (
    select distinct raw_label from {{ ref('stg_requests') }} where raw_label is not null
),

mapped as (
    select
        labels.raw_label,
        coalesce(crosswalk.request_type, labels.raw_label) as request_type,
        crosswalk.request_type is not null as spans_both_systems
    from labels
    left join {{ ref('request_type_crosswalk') }} as crosswalk
        on upper(labels.raw_label) = crosswalk.raw_label
)

select
    md5(request_type) as request_type_key,
    request_type,
    bool_or(spans_both_systems) as spans_both_systems,
    count(*) as raw_label_count
from mapped
group by request_type
