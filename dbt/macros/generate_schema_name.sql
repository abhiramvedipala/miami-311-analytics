{# Use "staging" and "mart" as written, without dbt's default prefix. #}
{% macro generate_schema_name(custom_schema_name, node) %}
  {{ custom_schema_name if custom_schema_name else target.schema }}
{% endmacro %}
