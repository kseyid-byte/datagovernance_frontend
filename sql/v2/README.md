# Governance App v2 Lakebase Migration

This folder is for a clean v2 start. The app should stay on the existing schema until these scripts pass verification.

## Target

- New Lakebase schema: `governance_app_v2`
- Clean master data from `sql/seed_master_data.sql`
- Clean app tables from `sql/lakebase_schema.sql`
- One-time import from old sources

## Run Order

1. Run `sql/v2/00_prepare_v2_schema.sql`.
2. In the same SQL session, run `sql/lakebase_schema.sql`.
3. In the same SQL session, run `sql/seed_master_data.sql`.
4. Import source data:
   - Preferred historical import: run `sql/v2/01_import_from_synced_legacy.sql`.
   - Optional current app copy: run `sql/v2/02_import_from_current_app_schema.sql` if `governance_app` has newer app-created records.
5. Run `sql/v2/03_verify_v2.sql`.
6. Only after verification, switch `GOVERNANCE_LAKEBASE_SCHEMA` in `app.yaml` from `governance_app` to `governance_app_v2`.

If the source import fails, run `sql/v2/99_inspect_v2_sources.sql` and compare the source columns with the import assumptions below.

## Source Assumptions

`01_import_from_synced_legacy.sql` reads:

```sql
app_control_tables.data_product_requests_new_synced
```

It imports into:

```sql
governance_app_v2.data_product_requests_new
```

The import keeps the source unchanged. Product IDs are deterministic with `legacy-` request IDs, request numbers are normalized to 8 digits where possible, and missing classification/output fields are derived from the legacy type/name text.

## Cutover Rule

Do not change `app.yaml` until `03_verify_v2.sql` shows:

- all master tables have rows,
- `md_stages` has 8 rows,
- `md_stage_requirements` has the expected workflow rows,
- imported requests are present,
- the final quality query returns no rows.
