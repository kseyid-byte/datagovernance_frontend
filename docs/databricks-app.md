# Databricks App Readiness

This repository is ready to deploy as a Databricks App backed by Databricks SQL.

## Runtime files

- `app.yaml` defines the Databricks App command.
- `app.py` is the stable Python entrypoint.
- `requirements.txt` includes the Databricks SQL connector and SDK.
- `server.py` reads `DATABRICKS_APP_PORT`, so Databricks can assign the runtime port.

Databricks Apps requires `app.yaml` at the repository root when a custom command or environment values are needed. The command starts `python app.py $DATABRICKS_APP_PORT`; `server.py` also falls back to the `DATABRICKS_APP_PORT` runtime environment variable if the command argument is not numeric.

## Current backend mode

The committed `app.yaml` uses:

```yaml
GOVERNANCE_BACKEND: databricks_sql
GOVERNANCE_CATALOG: venus_forge_dev
GOVERNANCE_SCHEMA: app_product_details
DATABRICKS_WAREHOUSE_ID:
  valueFrom: sql_warehouse
```

This stores requests, workflow answers, master data, and timeline events in Unity Catalog Delta tables.

For local testing, keep using SQLite by running:

```bash
GOVERNANCE_BACKEND=sqlite DATABRICKS_APP_PORT=8502 python3 app.py
```

## Databricks SQL setup

Before deploying the SQL-backed app:

1. Run `sql/databricks_schema.sql` after replacing `${catalog}.${schema}` with `venus_forge_dev.app_product_details`.
2. Run `sql/seed_master_data.sql` with the same replacement.
3. Add a Databricks App SQL warehouse resource using resource key `sql_warehouse`.
4. Grant the app service principal `USE CATALOG`, `USE SCHEMA`, and table read/write permissions on `venus_forge_dev.app_product_details`.

Use a Databricks App resource for the SQL warehouse instead of hardcoding sensitive or environment-specific values.

## Deploy from Git

1. Create a custom Databricks App.
2. Configure Git source:
   - Repository: `https://github.com/kseyid-byte/datagovernance_frontend`
   - Branch: `main`
   - Source path: repository root
3. Deploy.

## Deploy from CLI

```bash
databricks sync --watch . /Workspace/Users/<you>/datagovernance_frontend
databricks apps deploy <app-name> \
  --source-code-path /Workspace/Users/<you>/datagovernance_frontend
```

## What you need from Databricks today

- Permission to create/manage Databricks Apps.
- Access to the GitHub repo from Databricks, or a workspace folder deploy.
- A SQL warehouse for the future durable backend.
- A Unity Catalog catalog and schema name for the governance tables.
- App service principal permissions on the source folder and, later, on the SQL warehouse and Unity Catalog tables.
