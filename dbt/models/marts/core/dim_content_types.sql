/*
  dim_content_types
  -----------------
  Maps each data source to its canonical content type label and
  category classification. Sourced from seed reference data.
*/

with categories as (

    select
        source_name,
        category,
        subcategory,
        is_active
    from {{ ref('content_categories') }}

),

typed as (

    select
        {{ dbt_utils.generate_surrogate_key(['source_name']) }} as content_type_key,
        source_name,

        -- Human-readable content type per source
        case source_name
            when 'reddit' then 'Post'
            when 'steam'  then 'Game'
            when 'imdb'   then 'Title'
            when 'news'   then 'Article'
            else               'Unknown'
        end as content_type,

        category,
        subcategory,
        is_active,
        CURRENT_TIMESTAMP as dbt_created_at

    from categories

)

select * from typed
