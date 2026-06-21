{% test positive_score(model, column_name) %}
/*
  Generic test: assert that {{ column_name }} contains no negative values.
  Fails if any row has {{ column_name }} < 0.

  Usage in schema.yml:
    columns:
      - name: score
        tests:
          - positive_score
*/
select
    {{ column_name }}
from {{ model }}
where {{ column_name }} < 0

{% endtest %}
