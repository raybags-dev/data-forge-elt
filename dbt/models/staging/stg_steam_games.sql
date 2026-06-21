with source as (

    select * from {{ source('raw_steam', 'steam_games') }}

),

cleaned as (

    select
        {{ safe_cast('app_id', 'VARCHAR') }}                   as app_id,
        {{ normalize_text('name') }}                           as name,
        {{ safe_cast('price', 'DOUBLE') }}                     as price,
        {{ trim_strings('rating') }}                           as rating,
        {{ trim_strings('genres') }}                           as genres,
        {{ trim_strings('developer') }}                        as developer,
        {{ safe_cast('release_date', 'DATE') }}                as release_date,
        COALESCE(loaded_at, CURRENT_TIMESTAMP)                 as loaded_at

    from source
    where app_id is not null

)

select * from cleaned
