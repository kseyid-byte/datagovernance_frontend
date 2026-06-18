# v3 Lakebase Migration

v3 separates parent initiatives from governed child data products.

## Run Order

1. Run `sql/v3/00_prepare_v3_schema.sql`.
2. Run `sql/lakebase_schema.sql`.
3. Run `sql/seed_master_data.sql`.
4. For existing v3 schemas created before request-level platform/output, run `sql/v3/03_request_status_platform_output.sql`.
5. Run `sql/v3/01_import_v2_initiatives_only.sql`.
6. Run `sql/v3/02_verify_v3.sql`.
7. Grant the Databricks app service principal access to `governance_app_v3`.
8. Deploy the app branch configured with `GOVERNANCE_LAKEBASE_SCHEMA=governance_app_v3`.

The v2 import treats each v2 product/request row as one parent initiative. It does not create `data_products` rows.
