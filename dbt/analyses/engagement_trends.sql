/*
  engagement_trends.sql
  ----------------------
  Exploratory analysis: how does engagement evolve over time?
  Not materialized — compile and execute from target/compiled/.

  Sections:
    1. Week-over-week score growth per source
    2. Top authors by average score
    3. Engagement velocity (content + score acceleration)
*/

-- 1. Week-over-week average score growth per source
with weekly as (

    select
        source_name,
        DATE_TRUNC('week', created_at)                      as week_start,
        ROUND(AVG(score), 2)                                as avg_score,
        COUNT(*)                                            as item_count

    from {{ ref('fct_content') }}
    where created_at is not null
    group by source_name, DATE_TRUNC('week', created_at)

),

with_growth as (

    select
        source_name,
        week_start,
        avg_score,
        item_count,
        LAG(avg_score) OVER (
            PARTITION BY source_name ORDER BY week_start
        )                                                   as prev_week_score,
        LAG(item_count) OVER (
            PARTITION BY source_name ORDER BY week_start
        )                                                   as prev_week_count

    from weekly

)

select
    source_name,
    week_start,
    avg_score,
    item_count,
    prev_week_score,
    -- reuse calculate_growth macro logic inline
    CASE
        WHEN prev_week_score = 0 OR prev_week_score IS NULL THEN NULL
        ELSE ROUND((avg_score - prev_week_score) * 100.0 / prev_week_score, 2)
    END                                                     as score_growth_pct,
    CASE
        WHEN prev_week_count = 0 OR prev_week_count IS NULL THEN NULL
        ELSE ROUND((item_count - prev_week_count) * 100.0 / prev_week_count, 2)
    END                                                     as volume_growth_pct

from with_growth
order by source_name, week_start desc;


-- 2. Top 20 authors by average score (min 3 items)
select
    source_name,
    author,
    COUNT(*)                                                as item_count,
    ROUND(AVG(score), 2)                                    as avg_score,
    MAX(score)                                              as best_score
from {{ ref('fct_content') }}
where author is not null
group by source_name, author
having COUNT(*) >= 3
order by avg_score desc
limit 20;


-- 3. Daily engagement velocity: items + score momentum
select
    CAST(created_at AS DATE)                                as day,
    source_name,
    COUNT(*)                                                as items,
    SUM(score)                                              as total_score,
    LAG(SUM(score)) OVER (
        PARTITION BY source_name ORDER BY CAST(created_at AS DATE)
    )                                                       as prev_day_total_score,
    SUM(score) - LAG(SUM(score)) OVER (
        PARTITION BY source_name ORDER BY CAST(created_at AS DATE)
    )                                                       as score_delta
from {{ ref('fct_content') }}
where created_at is not null
group by CAST(created_at AS DATE), source_name
order by day desc, source_name;
