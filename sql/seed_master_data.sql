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
  ('completed', 'Completed'),
  ('on_hold', 'On hold'),
  ('cancelled', 'Cancelled'),
  ('deprecated', 'Deprecated');

INSERT INTO ${catalog}.${schema}.md_stages VALUES
  ('intake', 'Intake', 1),
  ('domain_ownership', 'Domain Ownership', 2),
  ('requirements', 'Requirements', 3),
  ('architecture_review', 'Architecture Review', 4),
  ('build_validate', 'Build / Validate', 5),
  ('publish', 'Publish', 6),
  ('operate', 'Operate', 7);

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
  ('intake_product_type_id', 'intake', 'product_type_id', 'Product type', 'select', 'productTypes', 'Select the data product type.', 1, 1),
  ('intake_target_platform_id', 'intake', 'target_platform_id', 'Target platform', 'select', 'platforms', 'Select the target delivery platform.', 2, 1),
  ('intake_priority_id', 'intake', 'priority_id', 'Priority', 'select', 'priorities', 'Select the request priority.', 3, 1),
  ('intake_scope_id', 'intake', 'scope_id', 'Scope', 'select', 'scopeOptions', 'Select the regional scope.', 4, 1),
  ('intake_business_decision', 'intake', 'business_decision', 'Business decision supported', 'textarea', NULL, 'Describe the decision this product supports.', 5, 1),
  ('intake_expected_date', 'intake', 'expected_date', 'Expected date', 'date', NULL, 'When is this product expected?', 6, 1),
  ('intake_additional_comments', 'intake', 'additional_comments', 'Additional comments', 'textarea', NULL, 'Any extra context for triage.', 7, 1),
  ('domain_ownership_lead_domain_id', 'domain_ownership', 'lead_domain_id', 'Lead domain', 'select', 'domains', 'Select the accountable data domain.', 1, 1),
  ('domain_ownership_lead_subdomain_id', 'domain_ownership', 'lead_subdomain_id', 'Lead subdomain', 'select', 'subdomains', 'Assign the accountable subdomain for the selected domain.', 2, 1),
  ('domain_ownership_delivery_date', 'domain_ownership', 'delivery_date', 'Delivery date', 'date', NULL, 'Set the planned delivery date.', 3, 1),
  ('domain_ownership_delivery_lead', 'domain_ownership', 'delivery_lead', 'Delivery lead', 'select', 'domainDeliveryLeads', 'Select from the same master data as Domain Delivery Lead.', 4, 1),
  ('domain_ownership_effort', 'domain_ownership', 'effort', 'Effort', 'number', NULL, 'Estimate delivery effort in days.', 5, 1),
  ('domain_ownership_jira_epic_id', 'domain_ownership', 'jira_epic_id', 'Jira epic ID', 'text', NULL, 'Add the Jira epic or delivery tracking ID.', 6, 1),
  ('domain_ownership_jira_link', 'domain_ownership', 'jira_link', 'Jira link', 'text', NULL, 'Add the Jira epic or story link.', 7, 1),
  ('domain_ownership_reuse_checked', 'domain_ownership', 'reuse_checked', 'Existing product reuse checked', 'checkbox', NULL, 'Confirm existing data products were checked first.', 8, 1),
  ('domain_ownership_data_domain_owner_user_id', 'domain_ownership', 'data_domain_owner_user_id', 'Data Domain Owner', 'select', 'dataDomainOwners', 'Select from master data.', 9, 1),
  ('domain_ownership_source_system_id', 'domain_ownership', 'source_system_id', 'Source System', 'select', 'sourceSystems', 'Select the approved source system.', 10, 1),
  ('domain_ownership_domain_delivery_lead_user_id', 'domain_ownership', 'domain_delivery_lead_user_id', 'Domain Delivery Lead', 'select', 'domainDeliveryLeads', 'Select from master data.', 11, 1),
  ('domain_ownership_lynx_pm_user_id', 'domain_ownership', 'lynx_pm_user_id', 'Lynx PM input', 'select', 'lynxPms', 'Select the Lynx PM accountable for input.', 12, 1),
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
