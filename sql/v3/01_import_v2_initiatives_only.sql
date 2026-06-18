-- Import each v2 product/request row as one v3 parent initiative/request.
-- This intentionally creates no child data_products rows.
--
-- In v2, the "product" row represented the business initiative/request.
-- In v3, explicit governed data products will be added later under these initiatives.
--
-- Run after sql/lakebase_schema.sql and sql/seed_master_data.sql with v3 search_path.

SET search_path TO governance_app_v3;

WITH source_rows AS (
  SELECT
    TO_JSONB(s) AS src,
    ROW_NUMBER() OVER (
      ORDER BY
        COALESCE(TO_JSONB(s)->>'request_number', TO_JSONB(s)->>'data_product_business_id', TO_JSONB(s)->>'request_id', TO_JSONB(s)->>'created_at', TO_JSONB(s)::TEXT)
    ) AS migration_number,
    COALESCE(
      NULLIF(TO_JSONB(s)->>'request_id', ''),
      NULLIF(TO_JSONB(s)->>'data_product_id', ''),
      MD5(TO_JSONB(s)::TEXT)
    ) AS legacy_key,
    COALESCE(
      NULLIF(TRIM(TO_JSONB(s)->>'title'), ''),
      NULLIF(TRIM(TO_JSONB(s)->>'data_product_name'), ''),
      NULLIF(TRIM(TO_JSONB(s)->>'data_object'), ''),
      NULLIF(TRIM(TO_JSONB(s)->>'initiative'), ''),
      CONCAT('Imported initiative ', ROW_NUMBER() OVER (ORDER BY TO_JSONB(s)::TEXT))
    ) AS initiative_name
  FROM governance_app_v2.data_product_requests_new s
),
mapped AS (
  SELECT
    CONCAT('v2-request-', legacy_key) AS request_id,
    LPAD(CAST(migration_number AS TEXT), 8, '0') AS request_number,
    initiative_name,
    COALESCE(src->>'description', src->>'data_object', '') AS business_decision,
    COALESCE(src->>'business_value', '') AS business_value,
    COALESCE(src->>'business_unit_id', src->>'business_unit', 'cp') AS business_unit_raw,
    COALESCE(src->>'scope_id', src->>'scope', src->>'region', 'global') AS scope_raw,
    COALESCE(src->>'priority_id', src->>'priority', 'p2') AS priority_raw,
    COALESCE(src->>'requester_name', src->>'requestor', '') AS requester_name,
    LOWER(COALESCE(src->>'requester_email', src->>'requested_by', src->>'requestor', '')) AS requester_email,
    COALESCE(src->>'expected_date', src->>'business_expected_date', '') AS expected_date,
    COALESCE(src->>'additional_comments', '') AS additional_comments,
    COALESCE(src->>'created_at', src->>'requested_date', src->>'last_status_change_date', NOW()::TEXT) AS created_at
  FROM source_rows
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
  request_id,
  request_number,
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
  'Imported from v2 request/product row. Products will be added later.',
  created_at,
  created_at
FROM mapped
ON CONFLICT (request_id) DO UPDATE SET
  initiative = EXCLUDED.initiative,
  business_decision = EXCLUDED.business_decision,
  business_value = EXCLUDED.business_value,
  priority_id = EXCLUDED.priority_id,
  business_unit_id = EXCLUDED.business_unit_id,
  scope_id = EXCLUDED.scope_id,
  requester_name = EXCLUDED.requester_name,
  requester_email = EXCLUDED.requester_email,
  expected_date = EXCLUDED.expected_date,
  additional_comments = EXCLUDED.additional_comments,
  updated_at = EXCLUDED.updated_at;

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
  CONCAT('v2-request-import-', request_id),
  'request',
  request_id,
  NULL,
  'created',
  'Initiative imported',
  'Imported from v2 request/product row. Products will be added later.',
  'migration',
  created_at
FROM governance_requests
WHERE request_id LIKE 'v2-request-%'
ON CONFLICT DO NOTHING;

SELECT
  COUNT(*) AS imported_initiatives,
  (SELECT COUNT(*) FROM data_products) AS imported_products
FROM governance_requests
WHERE request_id LIKE 'v2-request-%';
