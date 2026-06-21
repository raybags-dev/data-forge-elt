with source_meta as (

    select * from {{ ref('source_metadata') }}

),

categories as (

    select
        source_name,
        category,
        subcategory,
        is_active
    from {{ ref('content_categories') }}

),

joined as (

    select
        {{ dbt_utils.generate_surrogate_key(['sm.source_name']) }} as source_key,
        sm.source_name,
        sm.display_name,
        sm.base_url,
        sm.crawl_frequency_hours,
        sm.is_active,
        c.category,
        c.subcategory,
        CURRENT_TIMESTAMP as dbt_created_at,
        CURRENT_TIMESTAMP as dbt_updated_at

    from source_meta sm
    left join categories c on sm.source_name = c.source_name

)

select * from joined
