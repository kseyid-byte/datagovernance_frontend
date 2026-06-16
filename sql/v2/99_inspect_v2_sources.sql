-- Inspect available source tables before running the v2 import.
-- Run this if the import script fails or if you want to confirm the source shape.

SELECT
  table_schema,
  table_name
FROM information_schema.tables
WHERE table_schema IN ('app_control_tables', 'governance_app', 'governance_app_v2')
ORDER BY table_schema, table_name;

SELECT
  table_schema,
  table_name,
  column_name,
  data_type,
  ordinal_position
FROM information_schema.columns
WHERE (table_schema = 'app_control_tables' AND table_name = 'data_product_requests_new_synced')
   OR (table_schema = 'governance_app' AND table_name IN ('data_product_requests_new', 'request_stage_answers', 'request_timeline'))
   OR (table_schema = 'governance_app_v2' AND table_name IN ('data_product_requests_new', 'request_stage_answers', 'request_timeline'))
ORDER BY table_schema, table_name, ordinal_position;

SELECT
  'app_control_tables.data_product_requests_new_synced' AS source_table,
  COUNT(*) AS row_count
FROM app_control_tables.data_product_requests_new_synced;
