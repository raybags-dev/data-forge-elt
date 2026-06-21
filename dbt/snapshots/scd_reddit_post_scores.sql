{% snapshot scd_reddit_post_scores %}

{{
    config(
        target_schema = 'snapshots',
        unique_key    = 'id',
        strategy      = 'timestamp',
        updated_at    = 'loaded_at'
    )
}}

/*
  scd_reddit_post_scores
  -----------------------
  SCD Type 2 snapshot tracking score and comment count changes for Reddit posts.
  Scores change as users upvote/downvote over time; this snapshot preserves
  each observed state so engagement trends can be analysed historically.

  dbt adds automatically:
    dbt_scd_id      — surrogate key for the snapshot row
    dbt_updated_at  — when the row was last updated
    dbt_valid_from  — start of the validity window
    dbt_valid_to    — end of the validity window (NULL = current record)
    dbt_is_current  — boolean current-record flag (dbt >= 1.8)
*/

select
    id,
    title,
    author,
    subreddit,
    score,
    num_comments,
    url,
    created_at,
    loaded_at

from {{ ref('stg_reddit_posts') }}

{% endsnapshot %}
