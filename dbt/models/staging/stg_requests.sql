-- One row per request, with both source schemas (before and after the 2024-08-11
-- system change) renamed to shared columns. Times become local Miami time.
with parsed as (
    select
        request_id,
        source_layer,
        created_ms,
        modified_ms,
        attributes ->> '$.ticket_id' is not null as is_old_system,
        trim(coalesce(attributes ->> '$.Subject', attributes ->> '$.issue_type')) as raw_label,
        coalesce(attributes ->> '$.Department', attributes ->> '$.case_owner_description') as department,
        trim(coalesce(attributes ->> '$.Status', attributes ->> '$.ticket_status')) as raw_status,
        upper(coalesce(attributes ->> '$.Priority', attributes ->> '$.sr_priority')) as raw_priority,
        coalesce(attributes ->> '$.Municipality', attributes ->> '$.location_city') as raw_municipality,
        try_cast(coalesce(attributes ->> '$.Zip_Code', attributes ->> '$.zip_code') as double)::bigint as zip,
        coalesce(attributes ->> '$.Method_Received', attributes ->> '$.method_received') as method_received,
        try_cast(coalesce(attributes ->> '$.Closed_Date', attributes ->> '$.ticket_closed_date_time') as bigint) as closed_ms,
        try_cast(coalesce(attributes ->> '$.Latitude', attributes ->> '$.latitude') as double) as latitude,
        try_cast(coalesce(attributes ->> '$.Longitude', attributes ->> '$.longitude') as double) as longitude
    from {{ source('raw', 'service_requests') }}
    where created_ms is not null
    qualify row_number() over (partition by request_id order by modified_ms desc nulls last, source_layer desc) = 1
)

select
    request_id,
    source_layer,
    is_old_system,
    timezone('America/New_York', to_timestamp(created_ms / 1000)) as created_at,
    timezone('America/New_York', to_timestamp(closed_ms / 1000)) as closed_at,
    raw_label,
    department,
    raw_status,
    case
        when upper(raw_status) in ('OPEN', 'WIP', 'PENDNG', 'LIEN', 'OPEN (DUPLICATE)') then 'open'
        when upper(raw_status) in ('CLOSED', 'LOCKED', 'DUP', 'CLOSED (DUPLICATE)', 'CLOSED(DUPLICATE)',
                                   'CLOSED(DUPLICATE) (DUPLICATE)', 'CLOSED (TRANSFERRED)') then 'closed'
        when upper(raw_status) = 'CANCEL' then 'cancelled'
        else 'unknown'
    end as status_group,
    upper(raw_status) = 'DUP' or upper(raw_status) like '%DUPLICATE%' as is_duplicate,
    case raw_priority
        when 'STANDARD' then 'Standard'
        when 'HIGH' then 'High'
        when 'EMERGNCY' then 'High'
        when 'URGENT' then 'High'
        when 'COMMISSIONER' then 'Commissioner'
        when 'COMMSNR' then 'Commissioner'
        when 'MAYOR' then 'Mayor'
        else 'unknown'
    end as priority,
    case
        when raw_municipality is null then 'UNKNOWN'
        when upper(raw_municipality) = 'MIAMI_DADE_COUNTY' then 'UNINCORPORATED MIAMI-DADE'
        else upper(replace(regexp_replace(raw_municipality, '^(City|Town|Village)_of_', ''), '_', ' '))
    end as municipality,
    case when zip between 33000 and 33299 then zip end as zip,
    method_received,
    latitude,
    longitude
from parsed
