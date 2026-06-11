-- Import legacy request CSV into the Governance Input Tool.
--
-- 1. Upload New_Query_2026_06_09_20_50_18.csv to a Unity Catalog volume.
-- 2. Replace the path below with the uploaded file path.
-- 3. Run this in Databricks SQL.
--
-- Target schema used by the Databricks App:
--   venus_forge_dev.app_control_tables

USE CATALOG venus_forge_dev;
USE SCHEMA app_control_tables;

-- Optional cleanup if a previous run parsed the CSV incorrectly.
-- Run this before rerunning the corrected import if you see shifted request IDs/columns.
-- It removes only legacy-style imported rows, not app-created REQ-001 style requests.
/*
DELETE FROM request_timeline
WHERE timeline_id LIKE 'legacy-import-%';

DELETE FROM data_product_requests_new
WHERE request_number RLIKE '^REQ-[0-9]{8}$'
   OR request_id NOT RLIKE '^[0-9]+$';
*/

CREATE OR REPLACE TEMP VIEW legacy_requests_csv AS
SELECT *
FROM read_files(
  '/Volumes/venus_forge_dev/app_control_tables/<volume_name>/New_Query_2026_06_09_20_50_18.csv',
  format => 'csv',
  header => true,
  inferSchema => false,
  multiLine => true,
  quote => '"',
  escape => '"',
  mode => 'FAILFAST'
);

-- Stop here and validate before running the MERGE statements.
-- Expected result for New_Query_2026_06_09_20_50_18.csv:
--   parsed_rows = 153
--   bad_request_id_rows = 0
--   bad_request_number_rows = 0
SELECT
  COUNT(*) AS parsed_rows,
  SUM(CASE WHEN request_id IS NULL OR NOT (request_id RLIKE '^[0-9]+$') THEN 1 ELSE 0 END) AS bad_request_id_rows,
  SUM(CASE WHEN business_request_id IS NULL OR NOT (business_request_id RLIKE '^REQ-[0-9]{8}$') THEN 1 ELSE 0 END) AS bad_request_number_rows
FROM legacy_requests_csv;

SELECT
  request_id,
  business_request_id,
  data_object,
  requestor,
  status,
  commercial_domain,
  created_at,
  updated_at
FROM legacy_requests_csv
ORDER BY CAST(request_id AS INT)
LIMIT 20;

CREATE OR REPLACE TEMP VIEW legacy_requests_normalized AS
SELECT
  CAST(request_id AS STRING) AS request_id,
  COALESCE(NULLIF(TRIM(business_request_id), ''), CONCAT('REQ-', LPAD(CAST(request_id AS STRING), 8, '0'))) AS request_number,
  COALESCE(NULLIF(TRIM(data_object), ''), COALESCE(NULLIF(TRIM(business_request_id), ''), CONCAT('Legacy request ', CAST(request_id AS STRING)))) AS title,
  NULLIF(TRIM(comments), '') AS description,
  CASE
    WHEN LOWER(COALESCE(data_structure_type, '')) LIKE '%unstructured%' THEN 'unstructured'
    WHEN LOWER(COALESCE(data_structure_type, '')) LIKE '%structured%' THEN 'structured'
    ELSE 'mixed'
  END AS product_type_id,
  'databricks' AS target_platform_id,
  CASE
    WHEN LOWER(TRIM(priority)) = 'p0' THEN 'p0'
    WHEN LOWER(TRIM(priority)) = 'p1' THEN 'p1'
    WHEN LOWER(TRIM(priority)) = 'p2' THEN 'p2'
    WHEN LOWER(TRIM(priority)) = 'p3' THEN 'p3'
    ELSE 'p2'
  END AS priority_id,
  'commercial' AS lead_domain_id,
  CASE
    WHEN business_unit IS NULL OR TRIM(business_unit) = '' OR LOWER(TRIM(business_unit)) = 'null' THEN NULL
    ELSE LOWER(REGEXP_REPLACE(TRIM(business_unit), '[^A-Za-z0-9]+', '_'))
  END AS business_unit_id,
  CASE
    WHEN scope IS NULL OR TRIM(scope) = '' OR LOWER(TRIM(scope)) = 'null' THEN NULL
    ELSE LOWER(REGEXP_REPLACE(TRIM(scope), '[^A-Za-z0-9]+', '_'))
  END AS scope_id,
  SPLIT_PART(LOWER(COALESCE(NULLIF(TRIM(requestor), ''), NULLIF(TRIM(created_by), ''), 'unknown@syngenta.com')), '@', 1) AS requester_name,
  LOWER(COALESCE(NULLIF(TRIM(requestor), ''), NULLIF(TRIM(created_by), ''), 'unknown@syngenta.com')) AS requester_email,
  NULLIF(TRIM(initiative), '') AS initiative,
  NULLIF(TRIM(business_expected_date), '') AS expected_date,
  NULLIF(TRIM(delivery_date), '') AS delivery_date,
  CAST(NULL AS STRING) AS delivery_lead,
  CAST(NULL AS INT) AS effort,
  CAST(NULL AS STRING) AS jira_epic_id,
  CAST(NULL AS STRING) AS jira_link,
  NULLIF(TRIM(comments), '') AS additional_comments,
  CASE
    WHEN LOWER(TRIM(status)) = 'completed' THEN 'operate'
    WHEN LOWER(TRIM(status)) = 'in progress' THEN 'build_validate'
    WHEN LOWER(TRIM(status)) = 'approved' THEN 'domain_ownership'
    WHEN LOWER(TRIM(status)) = 'blocked' THEN 'domain_ownership'
    ELSE 'intake'
  END AS current_stage_id,
  CASE
    WHEN status IS NULL OR TRIM(status) = '' THEN 'open'
    ELSE LOWER(REGEXP_REPLACE(TRIM(status), '[^A-Za-z0-9]+', '_'))
  END AS status_id,
  NULLIF(TRIM(status_change_reason), '') AS status_change_reason,
  NULLIF(TRIM(last_status_change_date), '') AS last_status_change_date,
  LOWER(NULLIF(TRIM(last_status_changed_by), '')) AS last_status_changed_by,
  CASE
    WHEN UPPER(TRIM(commercial_domain)) = 'SALES & COMMERCIAL TRANSACTIONS' THEN 'sales_commercial_transactions'
    WHEN UPPER(TRIM(commercial_domain)) = 'MARKETING AND ENGAGEMENT' THEN 'marketing_engagement'
    WHEN UPPER(TRIM(commercial_domain)) = 'PRICING AND CONDITIONS' THEN 'pricing_conditions'
    WHEN UPPER(TRIM(commercial_domain)) = 'PRODUCT & MARKET PERFORMANCE' THEN 'product_market_performance'
    WHEN UPPER(TRIM(commercial_domain)) = 'CUSTOMER AND CRM CORE' THEN 'non_transactional_customers'
    WHEN UPPER(TRIM(commercial_domain)) = 'DIGITAL & AGRONOMY SOLUTIONS' THEN 'digital_agronomy_solutions'
    ELSE NULL
  END AS lead_subdomain_id,
  CAST(NULL AS STRING) AS data_domain_owner_user_id,
  CAST(NULL AS STRING) AS source_system_id,
  CAST(NULL AS STRING) AS domain_delivery_lead_user_id,
  CAST(NULL AS STRING) AS lynx_pm_user_id,
  CAST(NULL AS STRING) AS build_status_id,
  CONCAT_WS(
    ' | ',
    CASE WHEN hub IS NOT NULL AND TRIM(hub) <> '' AND LOWER(TRIM(hub)) <> 'null' THEN CONCAT('Hub: ', TRIM(hub)) END,
    CASE WHEN data_owner IS NOT NULL AND TRIM(data_owner) <> '' AND LOWER(TRIM(data_owner)) <> 'null' THEN CONCAT('Data owner: ', TRIM(data_owner)) END,
    CASE WHEN data_engineer IS NOT NULL AND TRIM(data_engineer) <> '' AND LOWER(TRIM(data_engineer)) <> 'null' THEN CONCAT('Data engineer: ', TRIM(data_engineer)) END,
    CASE WHEN status_change_reason IS NOT NULL AND TRIM(status_change_reason) <> '' THEN CONCAT('Status reason: ', TRIM(status_change_reason)) END
  ) AS note,
  COALESCE(NULLIF(TRIM(created_at), ''), CAST(CURRENT_TIMESTAMP() AS STRING)) AS created_at,
  COALESCE(NULLIF(TRIM(updated_at), ''), NULLIF(TRIM(created_at), ''), CAST(CURRENT_TIMESTAMP() AS STRING)) AS updated_at
FROM legacy_requests_csv;

-- Preserve source business-unit labels so imported rows can be displayed.
MERGE INTO md_business_units AS target
USING (
  SELECT DISTINCT
    CASE
      WHEN business_unit IS NULL OR TRIM(business_unit) = '' OR LOWER(TRIM(business_unit)) = 'null' THEN NULL
      ELSE LOWER(REGEXP_REPLACE(TRIM(business_unit), '[^A-Za-z0-9]+', '_'))
    END AS business_unit_id,
    TRIM(business_unit) AS business_unit_name
  FROM legacy_requests_csv
  WHERE business_unit IS NOT NULL AND TRIM(business_unit) <> '' AND LOWER(TRIM(business_unit)) <> 'null'
) AS source
ON target.business_unit_id = source.business_unit_id
WHEN NOT MATCHED THEN INSERT (business_unit_id, business_unit_name)
VALUES (source.business_unit_id, source.business_unit_name);

-- Preserve source scope labels so imported rows can be displayed exactly.
MERGE INTO md_scope_options AS target
USING (
  SELECT DISTINCT
    LOWER(REGEXP_REPLACE(TRIM(scope), '[^A-Za-z0-9]+', '_')) AS scope_id,
    TRIM(scope) AS scope_name,
    CASE
      WHEN UPPER(TRIM(scope)) = 'GLOBAL' THEN 'Global'
      WHEN TRIM(scope) IN ('Europe', 'Latin America', 'North America', 'AMEA', 'JANZ') THEN 'Region'
      ELSE 'Imported'
    END AS scope_type,
    CAST(NULL AS STRING) AS parent_scope_id
  FROM legacy_requests_csv
  WHERE scope IS NOT NULL AND TRIM(scope) <> '' AND LOWER(TRIM(scope)) <> 'null'
) AS source
ON target.scope_id = source.scope_id
WHEN NOT MATCHED THEN INSERT (scope_id, scope_name, scope_type, parent_scope_id)
VALUES (source.scope_id, source.scope_name, source.scope_type, source.parent_scope_id);

-- Preserve old request statuses such as Open, Approved, Rejected, and Abandoned.
MERGE INTO md_statuses AS target
USING (
  SELECT DISTINCT
    CASE
      WHEN status IS NULL OR TRIM(status) = '' THEN 'open'
      ELSE LOWER(REGEXP_REPLACE(TRIM(status), '[^A-Za-z0-9]+', '_'))
    END AS status_id,
    COALESCE(NULLIF(TRIM(status), ''), 'Open') AS status_name
  FROM legacy_requests_csv
) AS source
ON target.status_id = source.status_id
WHEN NOT MATCHED THEN INSERT (status_id, status_name)
VALUES (source.status_id, source.status_name);

-- Preserve P0 because it exists in the legacy extract.
MERGE INTO md_priorities AS target
USING (
  SELECT DISTINCT LOWER(TRIM(priority)) AS priority_id, UPPER(TRIM(priority)) AS priority_name
  FROM legacy_requests_csv
  WHERE LOWER(TRIM(priority)) IN ('p0', 'p1', 'p2', 'p3')
) AS source
ON target.priority_id = source.priority_id
WHEN NOT MATCHED THEN INSERT (priority_id, priority_name)
VALUES (source.priority_id, source.priority_name);

MERGE INTO data_product_requests_new AS target
USING legacy_requests_normalized AS source
ON target.request_id = source.request_id
WHEN MATCHED THEN UPDATE SET
  target.request_number = source.request_number,
  target.title = source.title,
  target.description = source.description,
  target.product_type_id = source.product_type_id,
  target.target_platform_id = source.target_platform_id,
  target.priority_id = source.priority_id,
  target.lead_domain_id = source.lead_domain_id,
  target.business_unit_id = source.business_unit_id,
  target.scope_id = source.scope_id,
  target.requester_name = source.requester_name,
  target.requester_email = source.requester_email,
  target.initiative = source.initiative,
  target.expected_date = source.expected_date,
  target.delivery_date = source.delivery_date,
  target.delivery_lead = source.delivery_lead,
  target.effort = source.effort,
  target.jira_epic_id = source.jira_epic_id,
  target.jira_link = source.jira_link,
  target.additional_comments = source.additional_comments,
  target.current_stage_id = source.current_stage_id,
  target.status_id = source.status_id,
  target.status_change_reason = source.status_change_reason,
  target.last_status_change_date = source.last_status_change_date,
  target.last_status_changed_by = source.last_status_changed_by,
  target.lead_subdomain_id = source.lead_subdomain_id,
  target.data_domain_owner_user_id = source.data_domain_owner_user_id,
  target.source_system_id = source.source_system_id,
  target.domain_delivery_lead_user_id = source.domain_delivery_lead_user_id,
  target.lynx_pm_user_id = source.lynx_pm_user_id,
  target.build_status_id = source.build_status_id,
  target.note = source.note,
  target.created_at = source.created_at,
  target.updated_at = source.updated_at
WHEN NOT MATCHED THEN INSERT (
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
  initiative,
  expected_date,
  delivery_date,
  delivery_lead,
  effort,
  jira_epic_id,
  jira_link,
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
) VALUES (
  source.request_id,
  source.request_number,
  source.title,
  source.description,
  source.product_type_id,
  source.target_platform_id,
  source.priority_id,
  source.lead_domain_id,
  source.business_unit_id,
  source.scope_id,
  source.requester_name,
  source.requester_email,
  source.initiative,
  source.expected_date,
  source.delivery_date,
  source.delivery_lead,
  source.effort,
  source.jira_epic_id,
  source.jira_link,
  source.additional_comments,
  source.current_stage_id,
  source.status_id,
  source.status_change_reason,
  source.last_status_change_date,
  source.last_status_changed_by,
  source.lead_subdomain_id,
  source.data_domain_owner_user_id,
  source.source_system_id,
  source.domain_delivery_lead_user_id,
  source.lynx_pm_user_id,
  source.build_status_id,
  source.note,
  source.created_at,
  source.updated_at
);

MERGE INTO request_timeline AS target
USING (
  SELECT
    CONCAT('legacy-import-', request_id) AS timeline_id,
    request_id,
    'imported' AS event_type,
    current_stage_id AS stage_id,
    CAST(NULL AS STRING) AS from_stage_id,
    current_stage_id AS to_stage_id,
    status_id,
    'Legacy request imported' AS event_label,
    CONCAT('Imported from legacy request ', request_number, '.') AS event_detail,
    requester_email AS created_by,
    created_at
  FROM legacy_requests_normalized
) AS source
ON target.timeline_id = source.timeline_id
WHEN NOT MATCHED THEN INSERT (
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
) VALUES (
  source.timeline_id,
  source.request_id,
  source.event_type,
  source.stage_id,
  source.from_stage_id,
  source.to_stage_id,
  source.status_id,
  source.event_label,
  source.event_detail,
  source.created_by,
  source.created_at
);

SELECT
  COUNT(*) AS imported_rows,
  MIN(request_number) AS first_request_number,
  MAX(request_number) AS last_request_number
FROM data_product_requests_new;
