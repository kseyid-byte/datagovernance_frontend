-- Lakebase/PostgreSQL schema for the Governance Input Tool.
-- Run this through the production migration process with search_path set to
-- the application schema.

CREATE TABLE IF NOT EXISTS md_domains (
  domain_id TEXT PRIMARY KEY,
  domain_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS md_business_units (
  business_unit_id TEXT PRIMARY KEY,
  business_unit_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS md_product_types (
  product_type_id TEXT PRIMARY KEY,
  product_type_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS md_product_classifications (
  product_classification_id TEXT PRIMARY KEY,
  product_classification_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS md_expected_outputs (
  expected_output_id TEXT PRIMARY KEY,
  expected_output_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS md_platforms (
  platform_id TEXT PRIMARY KEY,
  platform_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS md_priorities (
  priority_id TEXT PRIMARY KEY,
  priority_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS md_stages (
  stage_id TEXT PRIMARY KEY,
  stage_name TEXT NOT NULL UNIQUE,
  stage_number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS md_statuses (
  status_id TEXT PRIMARY KEY,
  status_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS md_subdomains (
  subdomain_id TEXT PRIMARY KEY,
  subdomain_name TEXT NOT NULL,
  domain_id TEXT NOT NULL,
  UNIQUE(domain_id, subdomain_name)
);

CREATE TABLE IF NOT EXISTS md_users (
  user_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  role_key TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS md_source_systems (
  source_system_id TEXT PRIMARY KEY,
  source_system_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS md_scope_options (
  scope_id TEXT PRIMARY KEY,
  scope_name TEXT NOT NULL,
  scope_type TEXT NOT NULL,
  parent_scope_id TEXT
);

CREATE TABLE IF NOT EXISTS md_build_statuses (
  build_status_id TEXT PRIMARY KEY,
  build_status_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS data_product_requests_new (
  request_id TEXT PRIMARY KEY,
  request_number TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT,
  product_type_id TEXT NOT NULL,
  target_platform_id TEXT NOT NULL,
  priority_id TEXT NOT NULL,
  lead_domain_id TEXT NOT NULL,
  business_unit_id TEXT,
  scope_id TEXT,
  requester_name TEXT,
  requester_email TEXT,
  data_product_owner TEXT,
  initiative TEXT,
  product_classification_id TEXT,
  expected_output_id TEXT,
  business_value TEXT,
  expected_date TEXT,
  delivery_date TEXT,
  delivery_lead TEXT,
  effort INTEGER,
  jira_epic_id TEXT,
  jira_link TEXT,
  alation_link TEXT,
  additional_comments TEXT,
  current_stage_id TEXT NOT NULL,
  status_id TEXT NOT NULL,
  status_change_reason TEXT,
  last_status_change_date TEXT,
  last_status_changed_by TEXT,
  lead_subdomain_id TEXT,
  data_domain_owner_user_id TEXT,
  source_system_id TEXT,
  domain_delivery_lead_user_id TEXT,
  lynx_pm_user_id TEXT,
  build_status_id TEXT,
  note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS md_stage_requirements (
  requirement_id TEXT PRIMARY KEY,
  stage_id TEXT NOT NULL,
  requirement_key TEXT NOT NULL,
  label TEXT NOT NULL,
  input_type TEXT NOT NULL,
  master_data_type TEXT,
  help_text TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  is_required INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS request_stage_answers (
  answer_id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL,
  requirement_id TEXT NOT NULL,
  answer_value TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(request_id, requirement_id)
);

CREATE TABLE IF NOT EXISTS request_timeline (
  timeline_id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  stage_id TEXT,
  from_stage_id TEXT,
  to_stage_id TEXT,
  status_id TEXT,
  event_label TEXT NOT NULL,
  event_detail TEXT,
  created_by TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_requests_stage ON data_product_requests_new(current_stage_id);
CREATE INDEX IF NOT EXISTS idx_requests_status ON data_product_requests_new(status_id);
CREATE INDEX IF NOT EXISTS idx_requests_created ON data_product_requests_new(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_stage_answers_request ON request_stage_answers(request_id);
CREATE INDEX IF NOT EXISTS idx_timeline_request_created ON request_timeline(request_id, created_at DESC);
