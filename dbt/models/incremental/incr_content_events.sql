{{
    config(
        materialized = 'incremental',
        unique_key   = 'event_id',
        on_schema_change = 'sync_all_columns'
    )
}}

/*
  incr_content_events
  --------------------
  Append-only event log. On each incremental run, only rows with a
  loaded_at timestamp later than the current table maximum are processed.
  Use `dbt run --full-refresh` to rebuild the full history.
*/

with source as (

    select
        content_id,
        source_name,
        natural_key,
        title,
        score,
        created_at,
        loaded_at
    from {{ ref('int_content_unified') }}

    {% if is_incremental() %}
        -- Only process records newer than the latest event already stored
        where loaded_at > (
            select MAX(loaded_at)
            from {{ this }}
        )
    {% endif %}

),

events as (

    select
        {{ dbt_utils.generate_surrogate_key(['content_id', 'loaded_at']) }} as event_id,
        content_id,
        source_name,
        natural_key,
        title,
        score,
        created_at,
        loaded_at,
        CAST(loaded_at AS DATE)                                              as event_date,
        CURRENT_TIMESTAMP                                                    as dbt_run_at

    from source

)

select * from events
