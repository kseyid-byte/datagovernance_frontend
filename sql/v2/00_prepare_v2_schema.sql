-- Governance Input Tool v2 clean Lakebase schema bootstrap.
--
-- Run this first in Lakebase/PostgreSQL.
-- Then run:
--   1. sql/lakebase_schema.sql
--   2. sql/seed_master_data.sql
--   3. one import script from this folder
--
-- Keep the app on the old schema until verification passes.

CREATE SCHEMA IF NOT EXISTS governance_app_v2;

SET search_path TO governance_app_v2;

SELECT
  'governance_app_v2 schema is selected. Now run sql/lakebase_schema.sql and sql/seed_master_data.sql in the same session.' AS next_step;
