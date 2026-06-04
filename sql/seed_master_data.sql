-- Seed master data for the Governance Input Tool.
-- Replace ${catalog}.${schema} before running.

INSERT INTO ${catalog}.${schema}.md_domains VALUES
  ('commercial', 'Commercial'),
  ('dummy_domain', 'Dummy Domain');

INSERT INTO ${catalog}.${schema}.md_business_units VALUES
  ('cp', 'CP'),
  ('seeds', 'Seeds'),
  ('vegetables', 'Vegetables');

INSERT INTO ${catalog}.${schema}.md_product_types VALUES
  ('structured', 'Structured'),
  ('unstructured', 'Unstructured'),
  ('mixed', 'Mixed');

INSERT INTO ${catalog}.${schema}.md_platforms VALUES
  ('databricks', 'Databricks'),
  ('lynx', 'Lynx'),
  ('both', 'Both');

INSERT INTO ${catalog}.${schema}.md_priorities VALUES
  ('p1', 'P1'),
  ('p2', 'P2'),
  ('p3', 'P3');

INSERT INTO ${catalog}.${schema}.md_statuses VALUES
  ('not_started', 'Not started'),
  ('in_review', 'In review'),
  ('in_progress', 'In progress'),
  ('blocked', 'Blocked'),
  ('ready', 'Ready'),
  ('operating', 'Operating'),
  ('completed', 'Completed');

INSERT INTO ${catalog}.${schema}.md_stages VALUES
  ('intake', 'Intake', 1),
  ('reuse_domain', 'Reuse / Domain', 2),
  ('ownership', 'Ownership', 3),
  ('requirements', 'Requirements', 4),
  ('architecture_review', 'Architecture Review', 5),
  ('build_validate', 'Build / Validate', 6),
  ('publish', 'Publish', 7),
  ('operate', 'Operate', 8);

INSERT INTO ${catalog}.${schema}.md_subdomains VALUES
  ('non_transactional_customers', 'Non Transactional Customers', 'commercial'),
  ('pricing_conditions', 'Pricing and Conditions', 'commercial'),
  ('product_market_performance', 'Product & Market Performance', 'commercial'),
  ('sales_commercial_transactions', 'Sales & Commercial Transactions', 'commercial'),
  ('marketing_engagement', 'Marketing & Engagement', 'commercial'),
  ('digital_agronomy_solutions', 'Digital & Agronomy Solutions', 'commercial'),
  ('dummy_subdomain', 'Dummy Subdomain', 'dummy_domain');

INSERT INTO ${catalog}.${schema}.md_users VALUES
  ('admin_demo', 'Demo Admin', 'demo.admin@syngenta.com', 'admin'),
  ('admin_kerem', 'Kerem Seyid', 'kerem.seyid@syngenta.com', 'admin'),
  ('admin_harish', 'Harish Krishnamoorthy', 'harish.krishnamoorthy@syngenta.com', 'admin'),
  ('udo_anna', 'Anna Khan', 'anna.khan@syngenta.com', 'data_domain_owner'),
  ('udo_maria', 'Maria Rossi', 'maria.rossi@syngenta.com', 'data_domain_owner'),
  ('ddl_james', 'James Silva', 'james.silva@syngenta.com', 'domain_delivery_lead'),
  ('ddl_nina', 'Nina Brown', 'nina.brown@syngenta.com', 'domain_delivery_lead'),
  ('pm_lynx_maya', 'Maya Patel', 'maya.patel@syngenta.com', 'lynx_pm'),
  ('pm_lynx_sam', 'Sam Martin', 'sam.martin@syngenta.com', 'lynx_pm');

INSERT INTO ${catalog}.${schema}.md_source_systems VALUES
  ('sap', 'SAP'),
  ('salesforce', 'Salesforce'),
  ('sharepoint', 'SharePoint'),
  ('databricks', 'Databricks'),
  ('manual_upload', 'Manual upload');

INSERT INTO ${catalog}.${schema}.md_scope_options VALUES
  ('global', 'Global', 'Global', NULL),
  ('europe', 'Europe', 'Region', NULL),
  ('latin_america', 'Latin America', 'Region', NULL),
  ('north_america', 'North America', 'Region', NULL),
  ('amea', 'AMEA', 'Region', NULL),
  ('janz', 'JANZ', 'Region', NULL);

INSERT INTO ${catalog}.${schema}.md_build_statuses VALUES
  ('not_started', 'Not started'),
  ('in_build', 'In build'),
  ('testing', 'Testing'),
  ('in_uat', 'In UAT'),
  ('built', 'Built'),
  ('blocked', 'Blocked');

INSERT INTO ${catalog}.${schema}.md_stage_requirements VALUES
  ('intake_business_decision', 'intake', 'business_decision', 'Business decision supported', 'textarea', NULL, 'Describe the decision this product supports.', 1, 1),
  ('intake_expected_date', 'intake', 'expected_date', 'Expected date', 'date', NULL, 'When is this product expected?', 2, 1),
  ('intake_additional_comments', 'intake', 'additional_comments', 'Additional comments', 'textarea', NULL, 'Any extra context for triage.', 3, 1),
  ('reuse_domain_lead_domain_id', 'reuse_domain', 'lead_domain_id', 'Lead domain', 'select', 'domains', 'Select the accountable data domain.', 1, 1),
  ('reuse_domain_lead_subdomain_id', 'reuse_domain', 'lead_subdomain_id', 'Lead subdomain', 'select', 'subdomains', 'Assign the accountable subdomain for the selected domain.', 2, 1),
  ('reuse_domain_delivery_date', 'reuse_domain', 'delivery_date', 'Delivery date', 'date', NULL, 'Set the planned delivery date.', 3, 1),
  ('reuse_domain_delivery_lead', 'reuse_domain', 'delivery_lead', 'Delivery lead', 'text', NULL, 'Name the delivery lead accountable for execution.', 4, 1),
  ('reuse_domain_effort', 'reuse_domain', 'effort', 'Effort', 'number', NULL, 'Estimate delivery effort in days.', 5, 1),
  ('reuse_domain_jira_epic_id', 'reuse_domain', 'jira_epic_id', 'Jira epic ID', 'text', NULL, 'Add the Jira epic or delivery tracking ID.', 6, 1),
  ('reuse_domain_jira_link', 'reuse_domain', 'jira_link', 'Jira link', 'text', NULL, 'Add the Jira epic or story link.', 7, 1),
  ('reuse_domain_reuse_checked', 'reuse_domain', 'reuse_checked', 'Existing product reuse checked', 'checkbox', NULL, 'Confirm existing data products were checked first.', 8, 1),
  ('ownership_data_domain_owner_user_id', 'ownership', 'data_domain_owner_user_id', 'Data Domain Owner', 'select', 'dataDomainOwners', 'Select from master data.', 1, 1),
  ('ownership_source_system_id', 'ownership', 'source_system_id', 'Source System', 'select', 'sourceSystems', 'Select the approved source system.', 2, 1),
  ('ownership_domain_delivery_lead_user_id', 'ownership', 'domain_delivery_lead_user_id', 'Domain Delivery Lead', 'select', 'domainDeliveryLeads', 'Select from master data.', 3, 1),
  ('ownership_lynx_pm_user_id', 'ownership', 'lynx_pm_user_id', 'Lynx PM input', 'select', 'lynxPms', 'Select the Lynx PM accountable for input.', 4, 1),
  ('requirements_kpis_defined', 'requirements', 'kpis_defined', 'KPIs defined', 'checkbox', NULL, 'Confirm KPIs are documented.', 1, 1),
  ('requirements_definitions_defined', 'requirements', 'definitions_defined', 'Definitions defined', 'checkbox', NULL, 'Confirm business definitions are documented.', 2, 1),
  ('requirements_grain_defined', 'requirements', 'grain_defined', 'Grains defined', 'checkbox', NULL, 'Confirm product grains are documented.', 3, 1),
  ('requirements_sources_defined', 'requirements', 'sources_defined', 'Sources defined', 'checkbox', NULL, 'Confirm source mapping is documented.', 4, 1),
  ('requirements_cde_defined', 'requirements', 'cde_defined', 'CDE defined', 'checkbox', NULL, 'Confirm critical data elements are documented.', 5, 1),
  ('requirements_dq_rules_defined', 'requirements', 'dq_rules_defined', 'Data Quality rules defined', 'checkbox', NULL, 'Confirm quality rules are documented.', 6, 1),
  ('architecture_review_architecture_review_complete', 'architecture_review', 'architecture_review_complete', 'Architecture review complete', 'checkbox', NULL, 'Confirm design review is complete.', 1, 1),
  ('architecture_review_security_pattern_confirmed', 'architecture_review', 'security_pattern_confirmed', 'Security pattern confirmed', 'checkbox', NULL, 'Confirm access and security design is approved.', 2, 1),
  ('architecture_review_tooling_confirmed', 'architecture_review', 'tooling_confirmed', 'Databricks / Lynx tooling confirmed', 'checkbox', NULL, 'Confirm target tooling is approved.', 3, 1),
  ('build_validate_build_status_id', 'build_validate', 'build_status_id', 'Build status', 'select', 'buildStatuses', 'Select the current build status.', 1, 1),
  ('build_validate_build_evidence', 'build_validate', 'build_evidence', 'Build / test notes', 'textarea', NULL, 'Add evidence, blockers, UAT notes, or test summary.', 2, 1),
  ('publish_alation_documented', 'publish', 'alation_documented', 'Documented in Alation', 'checkbox', NULL, 'Confirm the product is documented in Alation.', 1, 1),
  ('publish_release_notes', 'publish', 'release_notes', 'Release notes', 'textarea', NULL, 'Add release notes or support context.', 2, 1),
  ('operate_support_model_confirmed', 'operate', 'support_model_confirmed', 'Support model confirmed', 'checkbox', NULL, 'Confirm owner, refresh, and support model.', 1, 1),
  ('operate_review_cycle_confirmed', 'operate', 'review_cycle_confirmed', 'Review cycle confirmed', 'checkbox', NULL, 'Confirm value and quality review cadence.', 2, 1);
