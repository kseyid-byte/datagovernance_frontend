-- Governance Input Tool v3 Lakebase bootstrap.
-- Run first, then run sql/lakebase_schema.sql and sql/seed_master_data.sql in the same session.

CREATE SCHEMA IF NOT EXISTS governance_app_v3;

SET search_path TO governance_app_v3;

SELECT 'governance_app_v3 schema is selected. Run sql/lakebase_schema.sql, then sql/seed_master_data.sql.' AS next_step;
