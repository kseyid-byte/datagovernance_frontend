-- Add request-level status defaults plus initiative expected output and platform.
-- Run with search_path set to governance_app_v3.

SET search_path TO governance_app_v3;

ALTER TABLE governance_requests ADD COLUMN IF NOT EXISTS expected_output_id TEXT;
ALTER TABLE governance_requests ADD COLUMN IF NOT EXISTS target_platform_id TEXT;

INSERT INTO md_statuses VALUES ('new', 'New')
ON CONFLICT DO NOTHING;

UPDATE governance_requests
SET status_id = 'new'
WHERE status_id IS NULL
   OR status_id = ''
   OR status_id = 'in_review';

UPDATE governance_requests
SET expected_output_id = 'table_dataset'
WHERE expected_output_id IS NULL
   OR expected_output_id = '';

UPDATE governance_requests
SET target_platform_id = 'databricks'
WHERE target_platform_id IS NULL
   OR target_platform_id = '';
