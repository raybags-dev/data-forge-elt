{% macro clean_html(column_name) %}
    REGEXP_REPLACE({{ column_name }}, '<[^>]+>', '', 'g')
{% endmacro %}
