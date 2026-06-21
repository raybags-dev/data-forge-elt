/*
  int_content_unified
  -------------------
  Unions all staging content sources into a single, normalised schema.
  Produces one row per piece of content with a deterministic surrogate key.

  Sources:
    - stg_reddit_posts  (id as natural key)
    - stg_steam_games   (app_id as natural key)
    - stg_imdb_titles   (id as natural key)
    - stg_news_articles (url as natural key)
*/

with reddit as (

    select
        {{ dbt_utils.generate_surrogate_key(['\'reddit\'', 'id']) }} as content_id,
        'reddit'        as source_name,
        id              as natural_key,
        title,
        author,
        CAST(score AS DOUBLE)                                        as score,
        created_at,
        url,
        body,
        loaded_at
    from {{ ref('stg_reddit_posts') }}

),

steam as (

    select
        {{ dbt_utils.generate_surrogate_key(['\'steam\'', 'app_id']) }} as content_id,
        'steam'         as source_name,
        app_id          as natural_key,
        name            as title,
        developer       as author,
        CAST(price AS DOUBLE)                                           as score,
        CAST(release_date AS TIMESTAMP)                                 as created_at,
        NULL            as url,
        genres          as body,
        loaded_at
    from {{ ref('stg_steam_games') }}

),

imdb as (

    select
        {{ dbt_utils.generate_surrogate_key(['\'imdb\'', 'id']) }} as content_id,
        'imdb'          as source_name,
        id              as natural_key,
        title,
        NULL            as author,
        CAST(rating AS DOUBLE)                                     as score,
        CAST(CONCAT(CAST(year AS VARCHAR), '-01-01') AS TIMESTAMP) as created_at,
        url,
        genres          as body,
        loaded_at
    from {{ ref('stg_imdb_titles') }}

),

news as (

    select
        {{ dbt_utils.generate_surrogate_key(['\'news\'', 'url']) }} as content_id,
        'news'          as source_name,
        url             as natural_key,
        title,
        author,
        CAST(score AS DOUBLE)                                       as score,
        published_at    as created_at,
        url,
        body,
        loaded_at
    from {{ ref('stg_news_articles') }}

),

unified as (

    select * from reddit
    union all
    select * from steam
    union all
    select * from imdb
    union all
    select * from news

)

select * from unified
