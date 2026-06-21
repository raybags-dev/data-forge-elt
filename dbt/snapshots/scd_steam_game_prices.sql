{% snapshot scd_steam_game_prices %}

{{
    config(
        target_schema = 'snapshots',
        unique_key    = 'app_id',
        strategy      = 'timestamp',
        updated_at    = 'loaded_at'
    )
}}

/*
  scd_steam_game_prices
  ----------------------
  SCD Type 2 snapshot tracking price and rating changes for Steam games.
  Each row represents a point-in-time state of a game's price.

  dbt adds automatically:
    dbt_scd_id      — surrogate key for the snapshot row
    dbt_updated_at  — when the row was last updated
    dbt_valid_from  — start of the validity window
    dbt_valid_to    — end of the validity window (NULL = current record)
    dbt_is_current  — boolean current-record flag (dbt >= 1.8)
*/

select
    app_id,
    name,
    price,
    rating,
    developer,
    genres,
    loaded_at

from {{ ref('stg_steam_games') }}

{% endsnapshot %}
