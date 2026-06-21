{% macro generate_surrogate_key(field_list) %}
    {# Generate a deterministic surrogate key from one or more columns #}
    {# Falls back to MD5 concat when dbt_utils is not available #}
    {% if execute %}
        {{ dbt_utils.generate_surrogate_key(field_list) }}
    {% else %}
        MD5(
            CONCAT_WS('|',
                {% for field in field_list %}
                    COALESCE(CAST({{ field }} AS VARCHAR), '_null_')
                    {%- if not loop.last %},{% endif %}
                {% endfor %}
            )
        )
    {% endif %}
{% endmacro %}
