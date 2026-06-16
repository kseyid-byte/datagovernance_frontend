-- Optional import from the current application schema into governance_app_v2.
--
-- Use this if the current governance_app Lakebase schema contains requests
-- created or edited in the app that are newer than the synced legacy source.
--
-- Run after:
--   sql/v2/00_prepare_v2_schema.sql
--   sql/lakebase_schema.sql
--   sql/seed_master_data.sql

SET search_path TO governance_app_v2;

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
  CASE
    WHEN request_number ~ '^\d+$' THEN LPAD(RIGHT(request_number, 8), 8, '0')
    ELSE request_number
  END AS request_number,
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
  NULL AS data_product_owner,
  initiative,
  NULL AS product_classification_id,
  NULL AS expected_output_id,
  NULL AS business_value,
  expected_date,
  delivery_date,
  delivery_lead,
  effort,
  jira_epic_id,
  jira_link,
  NULL AS alation_link,
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
FROM governance_app.data_product_requests_new
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
  data_product_owner = COALESCE(data_product_requests_new.data_product_owner, EXCLUDED.data_product_owner),
  initiative = EXCLUDED.initiative,
  product_classification_id = COALESCE(data_product_requests_new.product_classification_id, EXCLUDED.product_classification_id),
  expected_output_id = COALESCE(data_product_requests_new.expected_output_id, EXCLUDED.expected_output_id),
  business_value = COALESCE(data_product_requests_new.business_value, EXCLUDED.business_value),
  expected_date = EXCLUDED.expected_date,
  delivery_date = EXCLUDED.delivery_date,
  delivery_lead = EXCLUDED.delivery_lead,
  effort = EXCLUDED.effort,
  jira_epic_id = EXCLUDED.jira_epic_id,
  jira_link = EXCLUDED.jira_link,
  alation_link = COALESCE(data_product_requests_new.alation_link, EXCLUDED.alation_link),
  additional_comments = EXCLUDED.additional_comments,
  current_stage_id = EXCLUDED.current_stage_id,
  status_id = EXCLUDED.status_id,
  status_change_reason = EXCLUDED.status_change_reason,
  last_status_change_date = EXCLUDED.last_status_change_date,
  last_status_changed_by = EXCLUDED.last_status_changed_by,
  lead_subdomain_id = EXCLUDED.lead_subdomain_id,
  data_domain_owner_user_id = EXCLUDED.data_domain_owner_user_id,
  source_system_id = EXCLUDED.source_system_id,
  domain_delivery_lead_user_id = EXCLUDED.domain_delivery_lead_user_id,
  lynx_pm_user_id = EXCLUDED.lynx_pm_user_id,
  build_status_id = EXCLUDED.build_status_id,
  note = EXCLUDED.note,
  updated_at = EXCLUDED.updated_at;

INSERT INTO request_stage_answers (
  answer_id,
  request_id,
  requirement_id,
  answer_value,
  updated_at
)
SELECT
  answer_id,
  request_id,
  requirement_id,
  answer_value,
  updated_at
FROM governance_app.request_stage_answers
ON CONFLICT (request_id, requirement_id) DO UPDATE SET
  answer_value = EXCLUDED.answer_value,
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
FROM governance_app.request_timeline
ON CONFLICT DO NOTHING;

SELECT
  COUNT(*) AS v2_requests
FROM data_product_requests_new;
