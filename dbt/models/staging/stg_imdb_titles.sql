with source as (

    select * from {{ source('raw_imdb', 'imdb_titles') }}

),

cleaned as (

    select
        {{ trim_strings('id') }}                               as id,
        {{ normalize_text('title') }}                          as title,
        {{ safe_cast('year', 'INTEGER') }}                     as year,
        {{ safe_cast('rating', 'DOUBLE') }}                    as rating,
        {{ safe_cast('votes', 'INTEGER') }}                    as votes,
        {{ trim_strings('genres') }}                           as genres,
        {{ trim_strings('type') }}                             as type,
        {{ trim_strings('url') }}                              as url,
        COALESCE(loaded_at, CURRENT_TIMESTAMP)                 as loaded_at

    from source
    where id is not null

)

select * from cleaned
