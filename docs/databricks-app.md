# Databricks App Readiness

This branch is configured to run as a Databricks App backed by Lakebase/PostgreSQL.

## Runtime files

- `app.yaml` defines the Databricks App command and Lakebase backend mode.
- `app.py` is the stable Python entrypoint.
- `requirements.txt` includes `psycopg[binary]` for Lakebase/PostgreSQL, plus the existing Databricks libraries.
- `server.py` reads `DATABRICKS_APP_PORT`, so Databricks can assign the runtime port.
- `sql/lakebase_schema.sql` is applied automatically on startup when `GOVERNANCE_BACKEND=lakebase`.

Databricks Apps requires `app.yaml` at the repository root when a custom command or environment values are needed. The command starts `python app.py $DATABRICKS_APP_PORT`; `server.py` also falls back to the `DATABRICKS_APP_PORT` runtime environment variable if the command argument is not numeric.

## Current backend mode

The Lakebase branch uses:

```yaml
GOVERNANCE_BACKEND: lakebase
GOVERNANCE_LAKEBASE_SCHEMA: public
GOVERNANCE_SEED_DEMO_DATA: "false"
```

The expected Lakebase app resource is:

```yaml
resources:
  - name: governance-lakebase
    database:
      databaseName: governance_app_dev
      instanceName: governance-lakebase-dev
      permission: CAN_CONNECT_AND_CREATE
```

For local testing, keep using SQLite by running:

```bash
GOVERNANCE_BACKEND=sqlite DATABRICKS_APP_PORT=8502 python3 app.py
```

## Lakebase UI setup

1. Open the Databricks workspace.
2. Open the Lakebase app from the apps switcher.
3. Create or select the Lakebase database setup using these names:
   - Instance/project: `governance-lakebase-dev`
   - Database: `governance_app_dev`
4. Open the Databricks App configuration.
5. Add a resource:
   - Type: Database / Lakebase
   - Resource key: `governance-lakebase`
   - Permission: `Can connect and create`
6. Deploy from Git:
   - Repository: `https://github.com/kseyid-byte/datagovernance_frontend`
   - Branch: `codex/lakebase-backend`
   - Source path: repository root

When the database resource is attached, Databricks injects standard PostgreSQL environment variables for the first database resource, including `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and `PGSSLMODE`. The app uses those values through `psycopg`.

## Startup behavior

On startup in Lakebase mode, the app:

1. Connects to Lakebase using the Databricks-provided PostgreSQL environment variables.
2. Creates the configured PostgreSQL schema if needed.
3. Creates all app tables from `sql/lakebase_schema.sql` if they do not exist.
4. Seeds master data and workflow stage requirements.
5. Does not seed demo product requests because `GOVERNANCE_SEED_DEMO_DATA=false` in `app.yaml`.

## Validation

After deployment, open:

```text
/api/health
```

Expected response shape:

```json
{
  "ok": true,
  "backend": "lakebase",
  "database": "governance_app_dev/public"
}
```

Then validate through the UI:

1. Create a request as a normal Syngenta user.
2. Confirm it appears on the overview table immediately.
3. Sign in as an admin email stored in `md_users`.
4. Open the admin workflow and save a stage.
5. Confirm the stage, dashboard counts, and timeline update without waiting on a SQL warehouse.

## Existing Databricks SQL mode

The Databricks SQL backend is still available in `server.py` for fallback or comparison testing, but this branch no longer uses it by default. To use it, set:

```yaml
GOVERNANCE_BACKEND: databricks_sql
GOVERNANCE_CATALOG: venus_forge_dev
GOVERNANCE_SCHEMA: app_control_tables
DATABRICKS_WAREHOUSE_ID:
  valueFrom: sql-warehouse
```

For that mode, use `sql/databricks_schema.sql` and `sql/seed_master_data.sql`.
