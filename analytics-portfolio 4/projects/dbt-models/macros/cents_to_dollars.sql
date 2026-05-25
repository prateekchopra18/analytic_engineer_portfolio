{% macro cents_to_dollars(column_name, scale=2) %}
    ({{ column_name }} / 100.0)::DECIMAL(18, {{ scale }})
{% endmacro %}


{% macro dollars_to_cents(column_name) %}
    ROUND({{ column_name }} * 100)::BIGINT
{% endmacro %}
