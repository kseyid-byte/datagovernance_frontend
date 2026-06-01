-- Governance Input Tool clean schema.
-- This matches the local SQLite-backed app and can be adapted to Databricks SQL.

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
  domain_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS md_users (
  user_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  email TEXT NOT NULL,
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

CREATE TABLE IF NOT EXISTS data_product_requests (
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
  expected_date TEXT,
  additional_comments TEXT,
  current_stage_id TEXT NOT NULL,
  status_id TEXT NOT NULL,
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

INSERT OR REPLACE INTO md_domains VALUES
  ('commercial', 'Commercial'),
  ('dummy_domain', 'Dummy Domain');

INSERT OR REPLACE INTO md_subdomains VALUES
  ('non_transactional_customers', 'Non Transactional Customers', 'commercial'),
  ('pricing_conditions', 'Pricing and Conditions', 'commercial'),
  ('product_market_performance', 'Product & Market Performance', 'commercial'),
  ('sales_commercial_transactions', 'Sales & Commercial Transactions', 'commercial'),
  ('marketing_engagement', 'Marketing & Engagement', 'commercial'),
  ('digital_agronomy_solutions', 'Digital & Agronomy Solutions', 'commercial'),
  ('dummy_subdomain', 'Dummy Subdomain', 'dummy_domain');

INSERT OR REPLACE INTO md_business_units VALUES
  ('cp', 'CP'),
  ('seeds', 'Seeds'),
  ('vegetables', 'Vegetables');

INSERT OR REPLACE INTO md_priorities VALUES
  ('p1', 'P1'),
  ('p2', 'P2'),
  ('p3', 'P3');

INSERT OR REPLACE INTO md_stages VALUES
  ('intake', 'Intake', 1),
  ('reuse_domain', 'Reuse / Domain', 2),
  ('ownership', 'Ownership', 3),
  ('requirements', 'Requirements', 4),
  ('architecture_review', 'Architecture Review', 5),
  ('build_validate', 'Build / Validate', 6),
  ('publish', 'Publish', 7),
  ('operate', 'Operate', 8);

INSERT OR REPLACE INTO md_scope_options VALUES
  ('global', 'Global', 'Global', NULL),
  ('europe', 'Europe', 'Region', NULL),
  ('latin_america', 'Latin America', 'Region', NULL),
  ('north_america', 'North America', 'Region', NULL),
  ('amea', 'AMEA', 'Region', NULL),
  ('janz', 'JANZ', 'Region', NULL),
  ('france', 'France', 'Country', 'europe'),
  ('germany', 'Germany', 'Country', 'europe'),
  ('brazil', 'Brazil', 'Country', 'latin_america'),
  ('mexico', 'Mexico', 'Country', 'latin_america'),
  ('usa', 'United States', 'Country', 'north_america'),
  ('canada', 'Canada', 'Country', 'north_america'),
  ('india', 'India', 'Country', 'amea'),
  ('south_africa', 'South Africa', 'Country', 'amea'),
  ('australia', 'Australia', 'Country', 'janz'),
  ('new_zealand', 'New Zealand', 'Country', 'janz');

INSERT OR REPLACE INTO md_users VALUES
  ('admin_demo', 'Demo Admin', 'demo.admin@syngenta.com', 'admin');
