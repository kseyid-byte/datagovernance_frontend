-- Removes Product Classification from the active Intake workflow and makes Lynx PM optional.
-- Run with search_path set to the application schema, for example:
--   SET search_path TO governance_app_v2;

DELETE FROM md_stage_requirements
WHERE requirement_id = 'intake_product_classification_id';

UPDATE md_stage_requirements
SET sort_order = sort_order - 1
WHERE stage_id = 'intake'
  AND sort_order > 2;

UPDATE md_stage_requirements
SET is_required = 0,
    help_text = 'Select the Lynx PM accountable for input when the product is moving to Lynx.'
WHERE requirement_id = 'reuse_domain_lynx_pm_user_id';
