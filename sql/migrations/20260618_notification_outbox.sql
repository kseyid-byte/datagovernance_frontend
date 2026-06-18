-- Run with search_path set to the application schema, for example:
--   SET search_path TO governance_app_v3;

CREATE TABLE IF NOT EXISTS notification_outbox (
  notification_id TEXT PRIMARY KEY,
  timeline_id TEXT REFERENCES governance_timeline(timeline_id),
  entity_type TEXT NOT NULL,
  request_id TEXT,
  data_product_id TEXT,
  event_type TEXT NOT NULL,
  recipient_email TEXT NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  created_at TEXT NOT NULL,
  sent_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_notification_outbox_status_created
  ON notification_outbox(status, created_at);
