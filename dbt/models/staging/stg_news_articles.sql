with source as (

    select * from {{ source('raw_news', 'news_articles') }}

),

cleaned as (

    select
        {{ trim_strings('url') }}                              as url,
        {{ normalize_text('title') }}                          as title,
        {{ trim_strings('author') }}                           as author,
        {{ trim_strings('source') }}                           as source,
        {{ safe_cast('score', 'INTEGER') }}                    as score,
        CAST(published_at AS TIMESTAMP)                        as published_at,
        {{ clean_html('body') }}                               as body,
        COALESCE(loaded_at, CURRENT_TIMESTAMP)                 as loaded_at

    from source
    where url is not null

)

select * from cleaned
