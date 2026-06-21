/*
  rpt_daily_ingestion_summary
  ----------------------------
  Pivots fct_engagement_metrics to show one row per calendar date
  with per-source content counts and the dominant source for that day.
*/

with metrics as (

    select
        activity_date,
        source_name,
        content_count,
        avg_score,
        total_score

    from {{ ref('fct_engagement_metrics') }}

),

pivoted as (

    select
        activity_date,
        SUM(content_count)                                              as total_content,
        SUM(case when source_name = 'reddit' then content_count else 0 end) as reddit_count,
        SUM(case when source_name = 'steam'  then content_count else 0 end) as steam_count,
        SUM(case when source_name = 'imdb'   then content_count else 0 end) as imdb_count,
        SUM(case when source_name = 'news'   then content_count else 0 end) as news_count,
        ROUND(
            SUM(total_score) / NULLIF(SUM(content_count), 0),
            2
        )                                                               as avg_score_all

    from metrics
    group by activity_date

),

with_dominant as (

    select
        p.activity_date,
        p.total_content,
        p.reddit_count,
        p.steam_count,
        p.imdb_count,
        p.news_count,
        p.avg_score_all,

        -- Dominant source: source with the most content for this day
        (
            select m2.source_name
            from metrics m2
            where m2.activity_date = p.activity_date
            order by m2.content_count desc
            limit 1
        ) as dominant_source,

        CURRENT_TIMESTAMP as report_generated_at

    from pivoted p

)

select * from with_dominant
order by activity_date desc
