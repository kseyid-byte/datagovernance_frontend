-- Run with search_path set to the application schema, for example:
--   SET search_path TO governance_app_v3;

UPDATE md_stage_requirements
SET
  label = 'Hub Owner',
  master_data_type = 'hubOwners',
  help_text = 'Select the hub owner accountable for the hub alignment.'
WHERE requirement_key = 'domain_delivery_lead_user_id';

UPDATE md_stage_requirements
SET help_text = 'Select from delivery lead master data.'
WHERE requirement_key = 'delivery_lead';
