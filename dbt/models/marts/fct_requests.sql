-- One row per service request.
select
    requests.request_id,
    types.request_type_key,
    requests.zip as neighborhood_key,
    requests.source_layer,
    requests.is_old_system,
    requests.created_at,
    requests.closed_at,
    requests.status_group,
    requests.is_duplicate,
    requests.priority,
    requests.municipality,
    requests.department,
    requests.method_received,
    requests.latitude,
    requests.longitude,
    -- Closed rows only. A close time before the create time is a source error.
    case
        when requests.status_group = 'closed' and requests.closed_at >= requests.created_at
        then date_diff('second', requests.created_at, requests.closed_at) / 86400.0
    end as days_to_close,
    -- Old-system layers no longer receive status updates, so their open rows are not real backlog.
    requests.status_group = 'open' and not requests.is_duplicate and not requests.is_old_system as is_backlog
from {{ ref('stg_requests') }} as requests
left join {{ ref('request_type_crosswalk') }} as crosswalk
    on upper(requests.raw_label) = crosswalk.raw_label
left join {{ ref('dim_request_type') }} as types
    on coalesce(crosswalk.request_type, requests.raw_label) = types.request_type
