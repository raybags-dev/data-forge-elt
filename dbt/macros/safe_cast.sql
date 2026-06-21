{% macro safe_cast(expression, type) %}
    TRY_CAST({{ expression }} AS {{ type }})
{% endmacro %}
