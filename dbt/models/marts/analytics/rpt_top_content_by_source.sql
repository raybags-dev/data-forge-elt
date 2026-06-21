/*
  rpt_top_content_by_source
  -------------------------
  Top 10 content items within each source, ranked by score descending.
  Null scores are ranked last via NULLS LAST.
*/

with content as (

    select
        content_id,
        source_name,
        natural_key,
        title,
        author,
        score,
        created_at,
        url
    from {{ ref('fct_content') }}

),

ranked as (

    select
        content_id,
        source_name,
        natural_key,
        title,
        author,
        score,
        created_at,
        url,
        ROW_NUMBER() OVER (
            PARTITION BY source_name
            ORDER BY score DESC NULLS LAST
        ) as rank_within_source

    from content

),

top_10 as (

    select * from ranked
    where rank_within_source <= 10

)

select * from top_10
order by source_name, rank_within_source
