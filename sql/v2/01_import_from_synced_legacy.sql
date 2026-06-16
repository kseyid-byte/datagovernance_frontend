-- Import legacy products from the synced Lakebase table into governance_app_v2.
--
-- Expected source:
--   app_control_tables.data_product_requests_new_synced
--
-- Run after:
--   sql/v2/00_prepare_v2_schema.sql
--   sql/lakebase_schema.sql
--   sql/seed_master_data.sql

SET search_path TO governance_app_v2;

WITH source_rows AS (
  SELECT
    TO_JSONB(s) AS src,
    COALESCE(
      NULLIF(TO_JSONB(s)->>'request_id', ''),
      NULLIF(TO_JSONB(s)->>'data_product_id', ''),
      MD5(TO_JSONB(s)::TEXT)
    ) AS legacy_key,
    COALESCE(
      NULLIF(REGEXP_REPLACE(COALESCE(TO_JSONB(s)->>'business_request_id', TO_JSONB(s)->>'data_product_business_id', TO_JSONB(s)->>'request_number', TO_JSONB(s)->>'request_id', TO_JSONB(s)->>'data_product_id', ''), '\D', '', 'g'), ''),
      SUBSTRING(MD5(TO_JSONB(s)::TEXT), 1, 8)
    ) AS legacy_number_digits
  FROM app_control_tables.data_product_requests_new_synced s
),
mapped AS (
  SELECT
    CONCAT('legacy-', legacy_key) AS request_id,
    LPAD(RIGHT(legacy_number_digits, 8), 8, '0') AS request_number,
    LEFT(COALESCE(NULLIF(src->>'data_product_name', ''), NULLIF(src->>'title', ''), NULLIF(src->>'data_object', ''), CONCAT('Imported data product ', legacy_key)), 500) AS title,
    NULLIF(COALESCE(src->>'description', src->>'data_object'), '') AS description,
    CASE
      WHEN LOWER(COALESCE(src->>'data_structure_type', src->>'type', src->>'product_type_id', '')) LIKE '%unstructured%' THEN 'unstructured'
      WHEN LOWER(COALESCE(src->>'data_structure_type', src->>'type', src->>'product_type_id', '')) LIKE '%semi%' THEN 'mixed'
      WHEN LOWER(COALESCE(src->>'data_structure_type', src->>'type', src->>'product_type_id', '')) LIKE '%mixed%' THEN 'mixed'
      WHEN LOWER(COALESCE(src->>'product_type_id', '')) IN ('structured', 'unstructured', 'mixed') THEN LOWER(src->>'product_type_id')
      ELSE 'structured'
    END AS product_type_id,
    CASE
      WHEN LOWER(COALESCE(src->>'target_platform_id', '')) IN ('databricks', 'lynx', 'both') THEN LOWER(src->>'target_platform_id')
      WHEN LOWER(COALESCE(src->>'type', src->>'data_product_name', src->>'title', src->>'data_object', '')) LIKE '%lynx%' THEN 'lynx'
      WHEN LOWER(COALESCE(src->>'type', src->>'data_product_name', src->>'title', src->>'data_object', '')) LIKE '%ai%' THEN 'lynx'
      ELSE 'databricks'
    END AS target_platform_id,
    CASE
      WHEN LOWER(COALESCE(src->>'priority', src->>'priority_id', '')) IN ('p1', 'high', 'critical') THEN 'p1'
      WHEN LOWER(COALESCE(src->>'priority', src->>'priority_id', '')) IN ('p3', 'low') THEN 'p3'
      ELSE 'p2'
    END AS priority_id,
    COALESCE(NULLIF(src->>'lead_domain_id', ''), 'commercial') AS lead_domain_id,
    CASE
      WHEN LOWER(COALESCE(src->>'business_unit', src->>'business_unit_id', '')) IN ('cp', 'crop protection') THEN 'cp'
      WHEN LOWER(COALESCE(src->>'business_unit', src->>'business_unit_id', '')) = 'seeds' THEN 'seeds'
      WHEN LOWER(COALESCE(src->>'business_unit', src->>'business_unit_id', '')) = 'vegetables' THEN 'vegetables'
      ELSE NULL
    END AS business_unit_id,
    CASE
      WHEN LOWER(COALESCE(src->>'scope', src->>'region', src->>'scope_id', '')) IN ('global', 'worldwide') THEN 'global'
      WHEN LOWER(COALESCE(src->>'scope', src->>'region', src->>'scope_id', '')) IN ('europe', 'eu') THEN 'europe'
      WHEN LOWER(COALESCE(src->>'scope', src->>'region', src->>'scope_id', '')) IN ('latin america', 'latam', 'latam region') THEN 'latin_america'
      WHEN LOWER(COALESCE(src->>'scope', src->>'region', src->>'scope_id', '')) IN ('north america', 'na', 'narm') THEN 'north_america'
      WHEN LOWER(COALESCE(src->>'scope', src->>'region', src->>'scope_id', '')) = 'amea' THEN 'amea'
      WHEN LOWER(COALESCE(src->>'scope', src->>'region', src->>'scope_id', '')) = 'janz' THEN 'janz'
      ELSE 'global'
    END AS scope_id,
    NULLIF(COALESCE(src->>'requester_name', src->>'requestor'), '') AS requester_name,
    LOWER(NULLIF(COALESCE(src->>'requester_email', src->>'requested_by', src->>'requestor'), '')) AS requester_email,
    NULLIF(COALESCE(src->>'data_product_owner', src->>'data_owner'), '') AS data_product_owner,
    NULLIF(src->>'initiative', '') AS initiative,
    CASE
      WHEN COALESCE(src->>'product_classification_id', '') IN ('data_product', 'bi_dashboard_product', 'ai_lynx_product', 'semantic_layer', 'source_data_asset') THEN src->>'product_classification_id'
      WHEN LOWER(COALESCE(src->>'type', src->>'data_product_name', src->>'title', src->>'data_object', '')) LIKE '%dashboard%' THEN 'bi_dashboard_product'
      WHEN LOWER(COALESCE(src->>'type', src->>'data_product_name', src->>'title', src->>'data_object', '')) LIKE '%report%' THEN 'bi_dashboard_product'
      WHEN LOWER(COALESCE(src->>'type', src->>'data_product_name', src->>'title', src->>'data_object', '')) LIKE '%semantic%' THEN 'semantic_layer'
      WHEN LOWER(COALESCE(src->>'type', src->>'data_product_name', src->>'title', src->>'data_object', '')) LIKE '%lynx%' THEN 'ai_lynx_product'
      WHEN LOWER(COALESCE(src->>'type', src->>'data_product_name', src->>'title', src->>'data_object', '')) LIKE '%ai%' THEN 'ai_lynx_product'
      WHEN LOWER(COALESCE(src->>'type', src->>'data_product_name', src->>'title', src->>'data_object', '')) LIKE '%source%' THEN 'source_data_asset'
      ELSE 'data_product'
    END AS product_classification_id,
    CASE
      WHEN COALESCE(src->>'expected_output_id', '') IN ('table_dataset', 'dashboard', 'api', 'semantic_layer', 'lynx_knowledge_base', 'ai_search_feature', 'report', 'other') THEN src->>'expected_output_id'
      WHEN LOWER(COALESCE(src->>'type', src->>'data_product_name', src->>'title', src->>'data_object', '')) LIKE '%dashboard%' THEN 'dashboard'
      WHEN LOWER(COALESCE(src->>'type', src->>'data_product_name', src->>'title', src->>'data_object', '')) LIKE '%api%' THEN 'api'
      WHEN LOWER(COALESCE(src->>'type', src->>'data_product_name', src->>'title', src->>'data_object', '')) LIKE '%semantic%' THEN 'semantic_layer'
      WHEN LOWER(COALESCE(src->>'type', src->>'data_product_name', src->>'title', src->>'data_object', '')) LIKE '%lynx%' THEN 'lynx_knowledge_base'
      WHEN LOWER(COALESCE(src->>'type', src->>'data_product_name', src->>'title', src->>'data_object', '')) LIKE '%ai%' THEN 'ai_search_feature'
      WHEN LOWER(COALESCE(src->>'type', src->>'data_product_name', src->>'title', src->>'data_object', '')) LIKE '%report%' THEN 'report'
      ELSE 'table_dataset'
    END AS expected_output_id,
    NULLIF(src->>'business_value', '') AS business_value,
    NULLIF(COALESCE(src->>'expected_date', src->>'business_expected_date'), '') AS expected_date,
    NULLIF(src->>'delivery_date', '') AS delivery_date,
    NULLIF(COALESCE(src->>'delivery_lead', src->>'data_engineer'), '') AS delivery_lead,
    CASE WHEN COALESCE(src->>'effort', '') ~ '^\d+$' THEN (src->>'effort')::INTEGER ELSE NULL END AS effort,
    NULLIF(src->>'jira_epic_id', '') AS jira_epic_id,
    NULLIF(src->>'jira_link', '') AS jira_link,
    NULLIF(src->>'alation_link', '') AS alation_link,
    NULLIF(src->>'additional_comments', '') AS additional_comments,
    CASE
      WHEN COALESCE(src->>'current_stage_id', '') IN ('intake', 'reuse_domain', 'ownership', 'requirements', 'architecture_review', 'build_validate', 'publish', 'operate') THEN src->>'current_stage_id'
      WHEN LOWER(COALESCE(src->>'status', src->>'status_id', '')) IN ('completed', 'closed', 'operating') THEN 'operate'
      WHEN LOWER(COALESCE(src->>'status', src->>'status_id', '')) IN ('in progress', 'approved', 'in_progress') THEN 'build_validate'
      ELSE 'intake'
    END AS current_stage_id,
    CASE
      WHEN COALESCE(src->>'status_id', '') IN ('not_started', 'in_review', 'in_progress', 'blocked', 'ready', 'operating', 'completed', 'on_hold', 'cancelled', 'deprecated') THEN src->>'status_id'
      WHEN LOWER(COALESCE(src->>'status', '')) IN ('pending', 'open') THEN 'in_review'
      WHEN LOWER(COALESCE(src->>'status', '')) IN ('in progress', 'approved') THEN 'in_progress'
      WHEN LOWER(COALESCE(src->>'status', '')) IN ('completed', 'closed') THEN 'operating'
      WHEN LOWER(COALESCE(src->>'status', '')) = 'cancelled' THEN 'cancelled'
      WHEN LOWER(COALESCE(src->>'status', '')) = 'blocked' THEN 'blocked'
      ELSE 'in_review'
    END AS status_id,
    NULLIF(src->>'status_change_reason', '') AS status_change_reason,
    NULLIF(src->>'last_status_change_date', '') AS last_status_change_date,
    NULLIF(src->>'last_status_changed_by', '') AS last_status_changed_by,
    NULLIF(src->>'lead_subdomain_id', '') AS lead_subdomain_id,
    NULLIF(src->>'data_domain_owner_user_id', '') AS data_domain_owner_user_id,
    NULLIF(src->>'source_system_id', '') AS source_system_id,
    NULLIF(src->>'domain_delivery_lead_user_id', '') AS domain_delivery_lead_user_id,
    NULLIF(src->>'lynx_pm_user_id', '') AS lynx_pm_user_id,
    NULLIF(src->>'build_status_id', '') AS build_status_id,
    NULLIF(COALESCE(src->>'note', src->>'status_change_reason'), '') AS note,
    COALESCE(NULLIF(src->>'created_at', ''), NULLIF(src->>'requested_date', ''), NULLIF(src->>'last_status_change_date', ''), NOW()::TEXT) AS created_at,
    COALESCE(NULLIF(src->>'updated_at', ''), NULLIF(src->>'last_status_change_date', ''), NULLIF(src->>'requested_date', ''), NOW()::TEXT) AS updated_at
  FROM source_rows
)
INSERT INTO data_product_requests_new (
  request_id,
  request_number,
  title,
  description,
  product_type_id,
  target_platform_id,
  priority_id,
  lead_domain_id,
  business_unit_id,
  scope_id,
  requester_name,
  requester_email,
  data_product_owner,
  initiative,
  product_classification_id,
  expected_output_id,
  business_value,
  expected_date,
  delivery_date,
  delivery_lead,
  effort,
  jira_epic_id,
  jira_link,
  alation_link,
  additional_comments,
  current_stage_id,
  status_id,
  status_change_reason,
  last_status_change_date,
  last_status_changed_by,
  lead_subdomain_id,
  data_domain_owner_user_id,
  source_system_id,
  domain_delivery_lead_user_id,
  lynx_pm_user_id,
  build_status_id,
  note,
  created_at,
  updated_at
)
SELECT
  request_id,
  request_number,
  title,
  description,
  product_type_id,
  target_platform_id,
  priority_id,
  lead_domain_id,
  business_unit_id,
  scope_id,
  requester_name,
  requester_email,
  data_product_owner,
  initiative,
  product_classification_id,
  expected_output_id,
  business_value,
  expected_date,
  delivery_date,
  delivery_lead,
  effort,
  jira_epic_id,
  jira_link,
  alation_link,
  additional_comments,
  current_stage_id,
  status_id,
  status_change_reason,
  last_status_change_date,
  last_status_changed_by,
  lead_subdomain_id,
  data_domain_owner_user_id,
  source_system_id,
  domain_delivery_lead_user_id,
  lynx_pm_user_id,
  build_status_id,
  note,
  created_at,
  updated_at
FROM mapped
ON CONFLICT (request_id) DO UPDATE SET
  request_number = EXCLUDED.request_number,
  title = EXCLUDED.title,
  description = EXCLUDED.description,
  product_type_id = EXCLUDED.product_type_id,
  target_platform_id = EXCLUDED.target_platform_id,
  priority_id = EXCLUDED.priority_id,
  lead_domain_id = EXCLUDED.lead_domain_id,
  business_unit_id = EXCLUDED.business_unit_id,
  scope_id = EXCLUDED.scope_id,
  requester_name = EXCLUDED.requester_name,
  requester_email = EXCLUDED.requester_email,
  data_product_owner = EXCLUDED.data_product_owner,
  initiative = EXCLUDED.initiative,
  product_classification_id = EXCLUDED.product_classification_id,
  expected_output_id = EXCLUDED.expected_output_id,
  expected_date = EXCLUDED.expected_date,
  delivery_date = EXCLUDED.delivery_date,
  delivery_lead = EXCLUDED.delivery_lead,
  effort = EXCLUDED.effort,
  jira_epic_id = EXCLUDED.jira_epic_id,
  jira_link = EXCLUDED.jira_link,
  current_stage_id = EXCLUDED.current_stage_id,
  status_id = EXCLUDED.status_id,
  status_change_reason = EXCLUDED.status_change_reason,
  last_status_change_date = EXCLUDED.last_status_change_date,
  last_status_changed_by = EXCLUDED.last_status_changed_by,
  note = EXCLUDED.note,
  updated_at = EXCLUDED.updated_at;

INSERT INTO request_timeline (
  timeline_id,
  request_id,
  event_type,
  stage_id,
  from_stage_id,
  to_stage_id,
  status_id,
  event_label,
  event_detail,
  created_by,
  created_at
)
SELECT
  CONCAT('legacy-import-', request_id),
  request_id,
  'created',
  current_stage_id,
  NULL,
  current_stage_id,
  status_id,
  'Imported into v2',
  'Imported from app_control_tables.data_product_requests_new_synced',
  'migration',
  created_at
FROM data_product_requests_new
WHERE request_id LIKE 'legacy-%'
ON CONFLICT DO NOTHING;

SELECT
  COUNT(*) AS imported_requests
FROM data_product_requests_new
WHERE request_id LIKE 'legacy-%';
