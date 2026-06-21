{% macro calculate_growth(current_col, previous_col) %}
    CASE
        WHEN {{ previous_col }} = 0 OR {{ previous_col }} IS NULL THEN NULL
        ELSE ROUND(
            ({{ current_col }} - {{ previous_col }}) * 100.0 / {{ previous_col }},
            2
        )
    END
{% endmacro %}
