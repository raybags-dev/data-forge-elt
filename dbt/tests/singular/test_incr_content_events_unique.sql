/*
  Singular test: event_id uniqueness for incr_content_events.
  Duplicate event_ids indicate the surrogate key strategy has collisions.
  Returns duplicate event_ids; test passes when 0 rows returned.
*/

select
    event_id,
    COUNT(*) as occurrence_count
from {{ ref('incr_content_events') }}
group by event_id
having COUNT(*) > 1
