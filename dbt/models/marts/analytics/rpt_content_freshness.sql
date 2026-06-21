/*
  rpt_content_freshness
  ----------------------
  Pipeline health report: how fresh is each source?
  Calculates hours since last load and assigns a freshness status label.
*/

with content as (

    select
        source_name,
        loaded_at,
        created_at
    from {{ ref('fct_content') }}

),

aggregated as (

    select
        source_name,
        MAX(loaded_at)                                                  as latest_loaded_at,
        COUNT(*)                                                        as total_records,
        COUNT(
            case
                when loaded_at >= (CURRENT_TIMESTAMP - INTERVAL '24 hours')
                then 1
            end
        )                                                               as records_last_24h

    from content
    group by source_name

),

with_freshness as (

    select
        source_name,
        latest_loaded_at,
        ROUND(
            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - latest_loaded_at)) / 3600,
            1
        )                                                               as hours_since_last_load,
        total_records,
        records_last_24h,

        -- Freshness status based on hours since last load
        case
            when latest_loaded_at is null                                                 then 'no_data'
            when EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - latest_loaded_at)) / 3600 <= 6  then 'fresh'
            when EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - latest_loaded_at)) / 3600 <= 24 then 'stale'
            else                                                                               'critical'
        end                                                             as freshness_status,

        CURRENT_TIMESTAMP                                               as report_generated_at

    from aggregated

)

select * from with_freshness
order by hours_since_last_load desc
