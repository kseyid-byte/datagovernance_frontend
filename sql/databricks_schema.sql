-- Unity Catalog schema template for the Governance Input Tool.
-- Replace ${catalog}.${schema} before running.

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.md_domains (
  domain_id STRING NOT NULL,
  domain_name STRING NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.md_business_units (
  business_unit_id STRING NOT NULL,
  business_unit_name STRING NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.md_product_types (
  product_type_id STRING NOT NULL,
  product_type_name STRING NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.md_platforms (
  platform_id STRING NOT NULL,
  platform_name STRING NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.md_priorities (
  priority_id STRING NOT NULL,
  priority_name STRING NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.md_stages (
  stage_id STRING NOT NULL,
  stage_name STRING NOT NULL,
  stage_number INT NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.md_statuses (
  status_id STRING NOT NULL,
  status_name STRING NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.md_subdomains (
  subdomain_id STRING NOT NULL,
  subdomain_name STRING NOT NULL,
  domain_id STRING NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.md_users (
  user_id STRING NOT NULL,
  display_name STRING NOT NULL,
  email STRING NOT NULL,
  role_key STRING NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.md_source_systems (
  source_system_id STRING NOT NULL,
  source_system_name STRING NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.md_scope_options (
  scope_id STRING NOT NULL,
  scope_name STRING NOT NULL,
  scope_type STRING NOT NULL,
  parent_scope_id STRING
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.md_build_statuses (
  build_status_id STRING NOT NULL,
  build_status_name STRING NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.md_stage_requirements (
  requirement_id STRING NOT NULL,
  stage_id STRING NOT NULL,
  requirement_key STRING NOT NULL,
  label STRING NOT NULL,
  input_type STRING NOT NULL,
  master_data_type STRING,
  help_text STRING NOT NULL,
  sort_order INT NOT NULL,
  is_required INT NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.data_product_requests (
  request_id STRING NOT NULL,
  request_number STRING NOT NULL,
  title STRING NOT NULL,
  description STRING,
  product_type_id STRING NOT NULL,
  target_platform_id STRING NOT NULL,
  priority_id STRING NOT NULL,
  lead_domain_id STRING NOT NULL,
  business_unit_id STRING,
  scope_id STRING,
  requester_name STRING,
  requester_email STRING,
  initiative STRING,
  expected_date STRING,
  delivery_date STRING,
  delivery_lead STRING,
  effort INT,
  jira_epic_id STRING,
  jira_link STRING,
  additional_comments STRING,
  current_stage_id STRING NOT NULL,
  status_id STRING NOT NULL,
  status_change_reason STRING,
  last_status_change_date STRING,
  last_status_changed_by STRING,
  lead_subdomain_id STRING,
  data_domain_owner_user_id STRING,
  source_system_id STRING,
  domain_delivery_lead_user_id STRING,
  lynx_pm_user_id STRING,
  build_status_id STRING,
  note STRING,
  created_at STRING NOT NULL,
  updated_at STRING NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.request_stage_answers (
  answer_id STRING NOT NULL,
  request_id STRING NOT NULL,
  requirement_id STRING NOT NULL,
  answer_value STRING NOT NULL,
  updated_at STRING NOT NULL
)
USING DELTA;

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.request_timeline (
  timeline_id STRING NOT NULL,
  request_id STRING NOT NULL,
  event_type STRING NOT NULL,
  stage_id STRING,
  from_stage_id STRING,
  to_stage_id STRING,
  status_id STRING,
  event_label STRING NOT NULL,
  event_detail STRING,
  created_by STRING,
  created_at STRING NOT NULL
)
USING DELTA;
