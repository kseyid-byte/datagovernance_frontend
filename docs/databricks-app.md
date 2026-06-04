# Databricks App Readiness

This repository is ready to deploy as a Databricks App in demo mode.

## Runtime files

- `app.yaml` defines the Databricks App command.
- `app.py` is the stable Python entrypoint.
- `requirements.txt` is intentionally present even though the demo build uses only the Python standard library.
- `server.py` reads `DATABRICKS_APP_PORT`, so Databricks can assign the runtime port.

Databricks Apps requires `app.yaml` at the repository root when a custom command or environment values are needed. Databricks substitutes `DATABRICKS_APP_PORT` at runtime and installs dependencies from `requirements.txt`.

## Current backend mode

The committed `app.yaml` uses:

```yaml
GOVERNANCE_BACKEND: sqlite
GOVERNANCE_SQLITE_PATH: /tmp/governance_tool.sqlite
```

This is for same-day demo deployment. The data is not intended to be durable in Databricks App compute. Use it to validate the UI, workflow, roles, and process movement.

## Production backend switch

After you create the Unity Catalog schema:

1. Run `sql/databricks_schema.sql` after replacing `${catalog}.${schema}`.
2. Seed the master data from the values in `server.py`.
3. Add `databricks-sql-connector>=4.0.0,<5.0.0` to `requirements.txt`.
4. Implement a Databricks SQL repository behind the same API functions used by `server.py`.
5. Change `app.yaml`:

```yaml
env:
  - name: GOVERNANCE_BACKEND
    value: databricks_sql
  - name: GOVERNANCE_CATALOG
    value: your_catalog
  - name: GOVERNANCE_SCHEMA
    value: your_schema
  - name: DATABRICKS_WAREHOUSE_ID
    valueFrom: sql_warehouse
```

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
