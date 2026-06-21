/*
  content_distribution.sql
  -------------------------
  Exploratory analysis: how is content distributed across sources?
  This file is compiled by dbt but NOT materialized — run with:
    dbt compile --select analyses/content_distribution
  Then execute the compiled SQL from target/compiled/...

  Sections:
    1. Overall distribution by source
    2. Score percentile bands
    3. Content volume over time (monthly)
*/

-- 1. Content count and share by source
select
    source_name,
    COUNT(*)                                           as content_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
        2
    )                                                  as pct_of_total,
    ROUND(AVG(score), 2)                               as avg_score,
    ROUND(MEDIAN(score), 2)                            as median_score,
    MAX(score)                                         as max_score,
    MIN(score)                                         as min_score
from {{ ref('fct_content') }}
group by source_name
order by content_count desc;


-- 2. Score percentile distribution (all sources)
select
    source_name,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY score) as p25,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY score) as p50,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY score) as p75,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY score) as p90,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY score) as p99
from {{ ref('fct_content') }}
where score is not null
group by source_name
order by source_name;


-- 3. Monthly content volume trend
select
    DATE_TRUNC('month', created_at)                    as month,
    source_name,
    COUNT(*)                                           as items_published,
    ROUND(AVG(score), 2)                               as avg_score
from {{ ref('fct_content') }}
where created_at is not null
group by DATE_TRUNC('month', created_at), source_name
order by month desc, source_name;
