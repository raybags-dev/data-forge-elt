with source as (

    select * from {{ source('raw_reddit', 'reddit_posts') }}

),

cleaned as (

    select
        id,
        {{ normalize_text('title') }}                          as title,
        {{ trim_strings('author') }}                           as author,
        {{ trim_strings('subreddit') }}                        as subreddit,
        {{ safe_cast('score', 'INTEGER') }}                    as score,
        {{ safe_cast('num_comments', 'INTEGER') }}             as num_comments,
        {{ trim_strings('url') }}                              as url,
        CAST(created_utc AS TIMESTAMP)                         as created_at,
        {{ clean_html('text') }}                               as body,
        COALESCE(loaded_at, CURRENT_TIMESTAMP)                 as loaded_at

    from source
    where id is not null

)

select * from cleaned
