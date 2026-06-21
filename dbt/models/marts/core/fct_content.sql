with unified as (

    select * from {{ ref('int_content_unified') }}

),

sources as (

    select source_key, source_name
    from {{ ref('dim_sources') }}

),

fact as (

    select
        {{ dbt_utils.generate_surrogate_key(['u.content_id']) }} as content_key,
        u.content_id,
        s.source_key,
        u.source_name,
        u.natural_key,
        u.title,
        u.author,
        u.score,
        u.created_at,
        u.url,
        u.body,
        u.loaded_at,
        CURRENT_TIMESTAMP                                        as dbt_created_at

    from unified u
    inner join sources s on u.source_name = s.source_name

)

select * from fact
