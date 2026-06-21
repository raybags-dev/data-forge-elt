{% test not_future_date(model, column_name) %}
/*
  Generic test: assert that {{ column_name }} does not contain future timestamps.
  A buffer of 1 hour is allowed for clock-skew between services.
  Fails if any row has {{ column_name }} more than 1 hour ahead of CURRENT_TIMESTAMP.

  Usage in schema.yml:
    columns:
      - name: created_at
        tests:
          - not_future_date
*/
select
    {{ column_name }}
from {{ model }}
where {{ column_name }} > (CURRENT_TIMESTAMP + INTERVAL '1 hour')

{% endtest %}
