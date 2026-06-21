with reddit as (

    select * from {{ ref('stg_reddit_posts') }}

),

categories as (

    select source_name, category, subcategory
    from {{ ref('content_categories') }}
    where source_name = 'reddit'

),

enriched as (

    select
        r.id,
        r.title,
        r.author,
        r.subreddit,
        r.score,
        r.num_comments,
        r.url,
        r.created_at,
        r.body,
        r.loaded_at,

        -- Engagement tier derived from score
        case
            when r.score >= 10000 then 'viral'
            when r.score >= 1000  then 'high'
            when r.score >= 100   then 'medium'
            else                       'low'
        end as engagement_tier,

        -- Popularity flag
        r.score >= 1000 as is_popular,

        -- Growth placeholder: ratio of comments to score
        {{ calculate_growth('r.num_comments', 'r.score') }} as comment_to_score_pct,

        -- Category from seeds
        c.category,
        c.subcategory

    from reddit r
    left join categories c on c.source_name = 'reddit'

)

select * from enriched
