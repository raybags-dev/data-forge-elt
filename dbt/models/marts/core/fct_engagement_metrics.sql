with content as (

    select
        source_name,
        score,
        created_at,
        loaded_at
    from {{ ref('fct_content') }}

),

daily_metrics as (

    select
        source_name,
        CAST(created_at AS DATE)                                                    as activity_date,
        COUNT(*)                                                                    as content_count,
        ROUND(AVG(score), 2)                                                        as avg_score,
        MAX(score)                                                                  as max_score,
        MIN(score)                                                                  as min_score,
        SUM(score)                                                                  as total_score,
        MAX(loaded_at)                                                              as last_loaded_at

    from content
    where created_at is not null
    group by source_name, CAST(created_at AS DATE)

),

with_keys as (

    select
        {{ dbt_utils.generate_surrogate_key(['source_name', 'activity_date']) }}   as metric_key,
        source_name,
        activity_date,
        content_count,
        avg_score,
        max_score,
        min_score,
        total_score,
        last_loaded_at,
        CURRENT_TIMESTAMP                                                           as dbt_created_at

    from daily_metrics

)

select * from with_keys
