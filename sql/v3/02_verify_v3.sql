-- Verify v3 after schema/seed/import.

SET search_path TO governance_app_v3;

SELECT 'governance_requests' AS table_name, COUNT(*) AS row_count FROM governance_requests
UNION ALL SELECT 'data_products', COUNT(*) FROM data_products
UNION ALL SELECT 'product_stage_answers', COUNT(*) FROM product_stage_answers
UNION ALL SELECT 'governance_timeline', COUNT(*) FROM governance_timeline
UNION ALL SELECT 'md_stages', COUNT(*) FROM md_stages
UNION ALL SELECT 'md_stage_requirements', COUNT(*) FROM md_stage_requirements
ORDER BY table_name;

SELECT
  p.data_product_id,
  p.title
FROM data_products p
LEFT JOIN governance_requests r ON r.request_id = p.request_id
WHERE r.request_id IS NULL
LIMIT 50;

SELECT
  COUNT(*) AS products_after_initiative_only_import
FROM data_products;
