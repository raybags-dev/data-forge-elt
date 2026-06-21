with steam as (

    select * from {{ ref('stg_steam_games') }}

),

categories as (

    select source_name, category, subcategory
    from {{ ref('content_categories') }}
    where source_name = 'steam'

),

enriched as (

    select
        s.app_id,
        s.name,
        s.price,
        s.rating,
        s.genres,
        s.developer,
        s.release_date,
        s.loaded_at,

        -- Price classification
        case
            when s.price is null or s.price = 0   then 'free'
            when s.price < 10                      then 'budget'
            when s.price < 30                      then 'mid'
            else                                        'premium'
        end as price_tier,

        -- Free-to-play flag
        (s.price is null or s.price = 0) as is_free,

        -- Category from seeds
        c.category,
        c.subcategory

    from steam s
    left join categories c on c.source_name = 'steam'

)

select * from enriched
