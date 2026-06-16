# Governance Input Tool

Browser-native Databricks application for capturing and tracking governed data product requests.

## Scope

- Overview dashboard and product pipeline table.
- New request intake.
- Admin workflow screen with stage requirements and automatic stage movement.
- Master-data maintenance for domains, subdomains, users, statuses, source systems, regions, and delivery metadata.
- Timeline capture for request creation, stage saves, status changes, and automatic movement.
- Role-based admin access from Databricks identity headers.
- Lakebase/PostgreSQL persistence.

There is no Streamlit dependency. The UI is plain HTML, CSS, and JavaScript, served by a small Python API.

## Runtime Contract

The app expects an existing Lakebase schema. It validates required tables and master data at startup, but it does not create tables, seed data, import Unity Catalog data, or run database migrations.

Required app configuration:

```yaml
env:
  - name: GOVERNANCE_LAKEBASE_SCHEMA
    value: governance_app_v2
  - name: GOVERNANCE_ADMIN_EMAILS
    value: kerem.seyid@syngenta.com,harish.krishnamoorthy@syngenta.com
  - name: DATABRICKS_POSTGRES_ENDPOINT
    valueFrom: governance-lakebase
```

Databricks must provide the Lakebase PostgreSQL environment variables for the app resource, including `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and `PGSSLMODE`. The app uses `DATABRICKS_POSTGRES_ENDPOINT` and `databricks-sdk` to request the short-lived Lakebase credential token.

## Database Migration

Use these files with the production migration process before deploying the app:

- `sql/lakebase_schema.sql` - Lakebase table DDL.
- `sql/seed_master_data.sql` - required baseline master data and workflow requirements.
- `sql/migrations/` - incremental migrations for existing Lakebase databases.
- `sql/v2/` - clean v2 schema bootstrap, legacy import, current-schema copy, and verification scripts.

Run both with the application schema selected as the PostgreSQL `search_path`.

The app does not apply migrations at runtime. Existing Lakebase databases must be migrated before deploying code that introduces new tables, columns, or required master data.

For a clean v2 start, run `sql/v2/README.md` end to end first. The Databricks app is configured to use `governance_app_v2`.

## Files

- `index.html` - application shell and screens.
- `styles.css` - layout and visual design.
- `app.js` - dashboard state, request creation, filtering, workflow, and API calls.
- `app.py` - Databricks app entrypoint.
- `app.yaml` - Databricks app command and Lakebase environment.
- `server.py` - static server plus Lakebase API.
- `requirements.txt` - Python dependency manifest.
- `tests/smoke_test.py` - no-database sanity checks for trusted identity and validation helpers.

## Workflow

- All authenticated Syngenta users can open the app and submit requests.
- Admin access is granted by `GOVERNANCE_ADMIN_EMAILS` or by `md_users.role_key` in the admin role set.
- Intake captures the requester, business unit, initiative, expected date, region scope, and business context.
- Domain Ownership captures lead domain, lead subdomain, delivery lead, Data Domain Owner, Domain Delivery Lead, and Lynx PM input.
- Estimation captures delivery date, effort, Jira epic ID, Jira link, existing product reuse confirmation, and source system outputs.
- Later stages capture requirement confirmation, architecture review, build/validation status, publish confirmation, and operate confirmation.
- A stage can be submitted only when previous stages are complete.
- Completing all required fields for the current stage advances the product automatically.

## Validation

Run:

```bash
node --check app.js
python3 -m py_compile app.py server.py tests/smoke_test.py
python3 tests/smoke_test.py
```
