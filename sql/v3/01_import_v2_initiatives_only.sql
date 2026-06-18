-- Import one initiative/request per v2 initiative value.
-- This intentionally creates no child data_products rows.
--
-- Run after sql/lakebase_schema.sql and sql/seed_master_data.sql with v3 search_path.

SET search_path TO governance_app_v3;

WITH source_rows AS (
  SELECT
    TO_JSONB(s) AS src,
    NULLIF(TRIM(TO_JSONB(s)->>'initiative'), '') AS initiative_name
  FROM governance_app_v2.data_product_requests_new s
),
initiative_groups AS (
  SELECT
    initiative_name,
    MIN(COALESCE(src->>'requester_name', src->>'requestor', '')) AS requester_name,
    MIN(LOWER(COALESCE(src->>'requester_email', src->>'requested_by', src->>'requestor', ''))) AS requester_email,
    MIN(COALESCE(src->>'business_unit_id', src->>'business_unit', 'cp')) AS business_unit_raw,
    MIN(COALESCE(src->>'scope_id', src->>'scope', src->>'region', 'global')) AS scope_raw,
    MIN(COALESCE(src->>'priority_id', src->>'priority', 'p2')) AS priority_raw,
    MIN(COALESCE(src->>'expected_date', src->>'business_expected_date', '')) AS expected_date,
    MIN(COALESCE(src->>'description', src->>'data_object', '')) AS business_decision,
    MIN(COALESCE(src->>'business_value', '')) AS business_value,
    MIN(COALESCE(src->>'additional_comments', '')) AS additional_comments,
    MIN(COALESCE(src->>'created_at', src->>'requested_date', src->>'last_status_change_date', NOW()::TEXT)) AS created_at,
    MIN(MD5(initiative_name)) AS initiative_hash
  FROM source_rows
  WHERE initiative_name IS NOT NULL
  GROUP BY initiative_name
)
INSERT INTO governance_requests (
  request_id,
  request_number,
  initiative,
  business_decision,
  business_value,
  priority_id,
  business_unit_id,
  scope_id,
  requester_name,
  requester_email,
  expected_date,
  additional_comments,
  status_id,
  note,
  created_at,
  updated_at
)
SELECT
  CONCAT('v2-initiative-', initiative_hash),
  LPAD(CAST(ROW_NUMBER() OVER (ORDER BY initiative_name) AS TEXT), 8, '0'),
  initiative_name,
  NULLIF(business_decision, ''),
  NULLIF(business_value, ''),
  CASE
    WHEN LOWER(priority_raw) IN ('p1', 'high', 'critical') THEN 'p1'
    WHEN LOWER(priority_raw) IN ('p3', 'low') THEN 'p3'
    ELSE 'p2'
  END,
  CASE
    WHEN LOWER(business_unit_raw) IN ('cp', 'crop protection') THEN 'cp'
    WHEN LOWER(business_unit_raw) = 'seeds' THEN 'seeds'
    WHEN LOWER(business_unit_raw) = 'vegetables' THEN 'vegetables'
    ELSE 'cp'
  END,
  CASE
    WHEN LOWER(scope_raw) IN ('global', 'worldwide') THEN 'global'
    WHEN LOWER(scope_raw) IN ('europe', 'eu') THEN 'europe'
    WHEN LOWER(scope_raw) IN ('latin america', 'latam', 'latin_america') THEN 'latin_america'
    WHEN LOWER(scope_raw) IN ('north america', 'na', 'north_america') THEN 'north_america'
    WHEN LOWER(scope_raw) = 'amea' THEN 'amea'
    WHEN LOWER(scope_raw) = 'janz' THEN 'janz'
    ELSE 'global'
  END,
  NULLIF(requester_name, ''),
  NULLIF(requester_email, ''),
  NULLIF(expected_date, ''),
  NULLIF(additional_comments, ''),
  'in_review',
  'Imported from v2 initiative values. No child products created.',
  created_at,
  created_at
FROM initiative_groups
ON CONFLICT (request_id) DO NOTHING;

INSERT INTO governance_timeline (
  timeline_id,
  entity_type,
  request_id,
  data_product_id,
  event_type,
  event_label,
  event_detail,
  created_by,
  created_at
)
SELECT
  CONCAT('v2-initiative-import-', request_id),
  'request',
  request_id,
  NULL,
  'created',
  'Initiative imported',
  'Imported from v2 initiative values. Products will be added later.',
  'migration',
  created_at
FROM governance_requests
WHERE request_id LIKE 'v2-initiative-%'
ON CONFLICT DO NOTHING;

SELECT
  COUNT(*) AS imported_initiatives,
  (SELECT COUNT(*) FROM data_products) AS imported_products
FROM governance_requests
WHERE request_id LIKE 'v2-initiative-%';
