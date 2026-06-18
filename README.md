# Governance Input Tool

Browser-native Databricks application for capturing and tracking governed data product requests.

## Scope

- Overview dashboard and product pipeline table.
- New initiative request intake with optional governed products added later.
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
    value: governance_app_v3
  - name: GOVERNANCE_ADMIN_EMAILS
    value: kerem.seyid@syngenta.com,harish.krishnamoorthy@syngenta.com
  - name: GOVERNANCE_NOTIFICATION_TEST_RECIPIENT
    value: kerem.seyid@syngenta.com
  - name: DATABRICKS_POSTGRES_ENDPOINT
    valueFrom: governance-lakebase
```

Databricks must provide the Lakebase PostgreSQL environment variables for the app resource, including `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and `PGSSLMODE`. The app uses `DATABRICKS_POSTGRES_ENDPOINT` and `databricks-sdk` to request the short-lived Lakebase credential token.

## Database Migration

Use these files with the production migration process before deploying the app:

- `sql/lakebase_schema.sql` - Lakebase table DDL.
- `sql/seed_master_data.sql` - required baseline master data and workflow requirements.
- `sql/migrations/` - incremental migrations for existing Lakebase databases.
- `sql/v3/` - clean v3 initiative/product schema bootstrap, v2 initiative import, and verification scripts.

Run both with the application schema selected as the PostgreSQL `search_path`.

The app does not apply migrations at runtime. Existing Lakebase databases must be migrated before deploying code that introduces new tables, columns, or required master data.

For a clean v3 start, run `sql/v3/README.md` end to end first. The Databricks app is configured to use `governance_app_v3`.

## Files

- `index.html` - application shell and screens.
- `styles.css` - layout and visual design.
- `app.js` - dashboard state, request creation, filtering, workflow, and API calls.
- `app.py` - Databricks app entrypoint.
- `app.yaml` - Databricks app command and Lakebase environment.
- `server.py` - static server plus Lakebase API.
- `notification_sender.py` - Databricks job entrypoint for sending pending notification emails.
- `requirements.txt` - Python dependency manifest.
- `tests/smoke_test.py` - no-database sanity checks for trusted identity and validation helpers.

## Workflow

- All authenticated Syngenta users can open the app and submit requests.
- Admin access is granted by `GOVERNANCE_ADMIN_EMAILS` or by `md_users.role_key` in the admin role set.
- Intake captures the requester, business unit, initiative, expected date, region scope, and business context.
- Admins add one or more governed products under an initiative.
- Product Domain Ownership captures lead domain, lead subdomain, delivery lead, Data Domain Owner, Hub Owner, and optional Lynx PM input.
- Estimation captures delivery date, effort, Jira epic ID, Jira link, existing product reuse confirmation, and source system outputs.
- Later stages capture requirement confirmation, architecture review, build/validation status, publish confirmation, and operate confirmation.
- A stage can be submitted only when previous stages are complete.
- Completing all required fields for the current stage advances the product automatically.

## Email Notifications

The app writes notification records to `notification_outbox` when meaningful governance events occur:

- Product or initiative status changed.
- Product stage advanced.
- Product workflow completed.

During testing, all notification records are addressed only to `GOVERNANCE_NOTIFICATION_TEST_RECIPIENT`, currently `kerem.seyid@syngenta.com`. After testing, recipient resolution can be changed to requester, Data Product Owner, delivery lead, Hub Owner, Data Domain Owner, and optional Lynx PM.

Emails are sent asynchronously by running:

```bash
python notification_sender.py
```

Required sender environment variables:

```bash
GOVERNANCE_LAKEBASE_SCHEMA=governance_app_v3
DATABRICKS_POSTGRES_ENDPOINT=<Lakebase resource endpoint>
GOVERNANCE_SMTP_HOST=<smtp host>
GOVERNANCE_SMTP_PORT=587
GOVERNANCE_SMTP_USER=<smtp user>
GOVERNANCE_SMTP_PASSWORD=<secret>
GOVERNANCE_EMAIL_FROM=<from address>
```

For a Databricks Job, schedule `python notification_sender.py` every few minutes. Use `GOVERNANCE_EMAIL_DRY_RUN=true` to validate that pending notifications can be read and marked without sending SMTP email.

## Validation

Run:

```bash
node --check app.js
python3 -m py_compile app.py server.py notification_sender.py tests/smoke_test.py
python3 tests/smoke_test.py
```
