-- Add intake governance fields and Alation evidence link.
-- Run with search_path set to the application schema.

CREATE TABLE IF NOT EXISTS md_product_classifications (
  product_classification_id TEXT PRIMARY KEY,
  product_classification_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS md_expected_outputs (
  expected_output_id TEXT PRIMARY KEY,
  expected_output_name TEXT NOT NULL
);

ALTER TABLE data_product_requests_new ADD COLUMN IF NOT EXISTS data_product_owner TEXT;
ALTER TABLE data_product_requests_new ADD COLUMN IF NOT EXISTS product_classification_id TEXT;
ALTER TABLE data_product_requests_new ADD COLUMN IF NOT EXISTS expected_output_id TEXT;
ALTER TABLE data_product_requests_new ADD COLUMN IF NOT EXISTS business_value TEXT;
ALTER TABLE data_product_requests_new ADD COLUMN IF NOT EXISTS alation_link TEXT;

INSERT INTO md_product_classifications VALUES
  ('data_product', 'Data Product'),
  ('bi_dashboard_product', 'BI / Dashboard Product'),
  ('ai_lynx_product', 'AI / Lynx Product'),
  ('semantic_layer', 'Semantic Layer'),
  ('source_data_asset', 'Source Data Asset')
ON CONFLICT DO NOTHING;

INSERT INTO md_expected_outputs VALUES
  ('table_dataset', 'Table / dataset'),
  ('dashboard', 'Dashboard'),
  ('api', 'API'),
  ('semantic_layer', 'Semantic layer'),
  ('lynx_knowledge_base', 'Lynx knowledge base'),
  ('ai_search_feature', 'AI / search feature'),
  ('report', 'Report'),
  ('other', 'Other')
ON CONFLICT DO NOTHING;

INSERT INTO md_stage_requirements (
  requirement_id,
  stage_id,
  requirement_key,
  label,
  input_type,
  master_data_type,
  help_text,
  sort_order,
  is_required
)
VALUES
  ('intake_data_product_owner', 'intake', 'data_product_owner', 'Data Product Owner', 'text', NULL, 'Name the person accountable for the product end-to-end.', 1, 1),
  ('intake_product_classification_id', 'intake', 'product_classification_id', 'Product classification', 'select', 'productClassifications', 'Classify the governed product type.', 2, 1),
  ('intake_expected_output_id', 'intake', 'expected_output_id', 'Expected output', 'select', 'expectedOutputs', 'Select the expected product output.', 3, 1),
  ('intake_product_type_id', 'intake', 'product_type_id', 'Product type', 'select', 'productTypes', 'Select the data product type.', 4, 1),
  ('intake_target_platform_id', 'intake', 'target_platform_id', 'Target platform', 'select', 'platforms', 'Select the target delivery platform.', 5, 1),
  ('intake_priority_id', 'intake', 'priority_id', 'Priority', 'select', 'priorities', 'Select the request priority.', 6, 1),
  ('intake_scope_id', 'intake', 'scope_id', 'Scope', 'select', 'scopeOptions', 'Select the regional scope.', 7, 1),
  ('intake_business_decision', 'intake', 'business_decision', 'Business decision supported', 'textarea', NULL, 'Describe the decision this product supports.', 8, 1),
  ('intake_business_value', 'intake', 'business_value', 'Business value', 'textarea', NULL, 'Describe why this matters and the value expected.', 9, 1),
  ('intake_expected_date', 'intake', 'expected_date', 'Expected date', 'date', NULL, 'When is this product expected?', 10, 1),
  ('intake_additional_comments', 'intake', 'additional_comments', 'Additional comments', 'textarea', NULL, 'Any extra context for triage.', 11, 1),
  ('publish_alation_link', 'publish', 'alation_link', 'Alation link', 'text', NULL, 'Add the Alation catalog or documentation link.', 1, 1),
  ('publish_alation_documented', 'publish', 'alation_documented', 'Documented in Alation', 'checkbox', NULL, 'Confirm the product is documented in Alation.', 2, 1),
  ('publish_release_notes', 'publish', 'release_notes', 'Release notes', 'textarea', NULL, 'Add release notes or support context.', 3, 1)
ON CONFLICT (requirement_id)
DO UPDATE SET
  stage_id = EXCLUDED.stage_id,
  requirement_key = EXCLUDED.requirement_key,
  label = EXCLUDED.label,
  input_type = EXCLUDED.input_type,
  master_data_type = EXCLUDED.master_data_type,
  help_text = EXCLUDED.help_text,
  sort_order = EXCLUDED.sort_order,
  is_required = EXCLUDED.is_required;
