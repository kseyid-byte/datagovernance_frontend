-- Verify the v2 Lakebase schema before switching app.yaml to governance_app_v2.

SET search_path TO governance_app_v2;

SELECT 'md_domains' AS table_name, COUNT(*) AS row_count FROM md_domains
UNION ALL SELECT 'md_business_units', COUNT(*) FROM md_business_units
UNION ALL SELECT 'md_product_types', COUNT(*) FROM md_product_types
UNION ALL SELECT 'md_product_classifications', COUNT(*) FROM md_product_classifications
UNION ALL SELECT 'md_expected_outputs', COUNT(*) FROM md_expected_outputs
UNION ALL SELECT 'md_platforms', COUNT(*) FROM md_platforms
UNION ALL SELECT 'md_priorities', COUNT(*) FROM md_priorities
UNION ALL SELECT 'md_stages', COUNT(*) FROM md_stages
UNION ALL SELECT 'md_statuses', COUNT(*) FROM md_statuses
UNION ALL SELECT 'md_subdomains', COUNT(*) FROM md_subdomains
UNION ALL SELECT 'md_users', COUNT(*) FROM md_users
UNION ALL SELECT 'md_source_systems', COUNT(*) FROM md_source_systems
UNION ALL SELECT 'md_scope_options', COUNT(*) FROM md_scope_options
UNION ALL SELECT 'md_build_statuses', COUNT(*) FROM md_build_statuses
UNION ALL SELECT 'md_stage_requirements', COUNT(*) FROM md_stage_requirements
UNION ALL SELECT 'data_product_requests_new', COUNT(*) FROM data_product_requests_new
UNION ALL SELECT 'request_stage_answers', COUNT(*) FROM request_stage_answers
UNION ALL SELECT 'request_timeline', COUNT(*) FROM request_timeline
ORDER BY table_name;

SELECT
  current_stage_id,
  status_id,
  COUNT(*) AS products
FROM data_product_requests_new
GROUP BY current_stage_id, status_id
ORDER BY current_stage_id, status_id;

SELECT
  request_id,
  request_number,
  title
FROM data_product_requests_new
WHERE request_number IS NULL
   OR request_number = ''
   OR title IS NULL
   OR title = ''
   OR current_stage_id NOT IN (SELECT stage_id FROM md_stages)
   OR status_id NOT IN (SELECT status_id FROM md_statuses)
ORDER BY request_id
LIMIT 50;
