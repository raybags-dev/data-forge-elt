/*
  Singular test: referential integrity for fct_content.
  Every row in fct_content must have a matching source in dim_sources.
  Returns rows that violate this constraint; test passes when 0 rows returned.
*/

select
    fct.content_id,
    fct.source_name
from {{ ref('fct_content') }} fct
left join {{ ref('dim_sources') }} dim
    on fct.source_name = dim.source_name
where dim.source_name is null
