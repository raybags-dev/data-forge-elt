{% macro trim_strings(column_name) %}
    TRIM({{ column_name }})
{% endmacro %}
