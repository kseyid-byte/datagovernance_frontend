# Governance Input Tool

Browser-native UI prototype for capturing and tracking governed data product requests.

The current scope is intentionally focused:

- Overview dashboard
- Governance process rail
- Product pipeline table
- New request form
- Admin workflow screen for completing stage requirements
- Master-data driven dropdowns for domain, BU, priority, regional scope, subdomain, source system, role assignments, status, and build status
- Timeline capture for request creation, stage saves, status changes, and automatic movement
- Role-based access using Databricks identity headers: all authenticated Syngenta users can create requests; configured admins see workflow and master-data maintenance.
- Admin master-data maintenance for adding/removing lookup values.
- Databricks SQL persistence with SQLite available for local backup testing.

There is no Streamlit dependency. The UI is plain HTML, CSS, and JavaScript so the layout is fully controlled. A small Python backend is included for local API testing.

## Run locally

```bash
GOVERNANCE_BACKEND=sqlite DATABRICKS_APP_PORT=8502 python3 app.py
```

Open `http://localhost:8502`.

Local browser sessions still need a Databricks-style identity header to load `/api/session`. For API smoke testing, use `X-Forwarded-Email`. For development-only fallback identity, set `GOVERNANCE_ALLOW_IDENTITY_FALLBACK=true` and pass `?email=name@syngenta.com`.

## Files

- `index.html` - application shell and screens
- `styles.css` - layout and visual design
- `app.js` - dashboard state, request creation, filtering, and API calls
- `app.py` - Databricks App entrypoint
- `app.yaml` - Databricks App runtime command and SQL environment
- `server.py` - static server plus SQLite/Databricks SQL API
- `requirements.txt` - Python dependency manifest for Databricks Apps
- `governance_tool.sqlite` - local database created automatically when the server starts
- `schema.sql` - clean schema matching the current local app data model
- `sql/databricks_schema.sql` - Unity Catalog / Delta table DDL template
- `sql/seed_master_data.sql` - Databricks SQL seed data for master data and stage requirements
- `docs/databricks-app.md` - Databricks deployment checklist and backend switch notes
- `tests/smoke_test.py` - local smoke coverage for identity, request creation, workflow movement, and validation

## Databricks App deployment

The repository can be used as a custom Databricks App source today.

Current `app.yaml` runs the app with the Databricks SQL backend:

- Catalog: `venus_forge_dev`
- Schema: `app_control_tables`
- SQL warehouse resource key: `sql-warehouse`

To deploy from Git:

1. Create a custom Databricks App.
2. Use Git source `https://github.com/kseyid-byte/datagovernance_frontend`.
3. Use branch `main` and source path `/`.
4. Deploy.

For the durable backend, create the Unity Catalog schema, run `sql/databricks_schema.sql`, run `sql/seed_master_data.sql`, and grant the app service principal read/write access to the tables.

See `docs/databricks-app.md` for the exact checklist.

## Workflow behavior

- Master data is read through `/api/master-data`.
- Domains are read from master data in the intake form.
- New request emails must use the `@syngenta.com` format.
- Scope supports Global and regional scope. Countries can be added later if needed.
- Domains are master data. Subdomains are tied to a parent domain so new domains and their own subdomains can be added later.
- Commercial is seeded with: Non Transactional Customers, Pricing and Conditions, Product & Market Performance, Sales & Commercial Transactions, Marketing & Engagement, Digital & Agronomy Solutions.
- Dummy Domain and Dummy Subdomain are seeded for testing domain changes.
- Admin workflow data is read from `/api/requests/{request_id}/workflow`.
- Admins can see every stage, but a stage can be submitted only when previous stages are complete.
- Saving all required fields for the current stage automatically advances the product to the next stage.
- Admin-only write APIs require a trusted Databricks identity header resolving to an admin email configured in `md_users`.
- Current seeded admin emails include `kerem.seyid@syngenta.com` and `harish.krishnamoorthy@syngenta.com`.

## Validation

Run:

```bash
node --check app.js
python3 -m py_compile app.py server.py tests/smoke_test.py
python3 tests/smoke_test.py
```

## Approval actions design

The next implementation should add a `request_approvals` table and an approval panel in Admin Workflow.

Recommended actions:

- `Approve` - records approver, stage, timestamp, and advances when all approvals are complete.
- `Request changes` - keeps the product in the current stage and captures required rework.
- `Reject` - closes or parks the request with a reason.
- `Exception approved` - allows movement with risk owner, expiry date, and reason.

Each approval event should also write to `request_timeline`.

## Reporting design

Recommended reporting panels:

- Stage aging: count and average days by current stage.
- Blocked products: count by blocker reason/status owner.
- Throughput: requests created, advanced, published by week.
- Ownership load: products by Data Domain Owner, Delivery Lead, Lynx PM.
- Scope view: products by business unit, region, and country.
- SLA risk: products over target days in stage.

## Local database

The local backup database is `governance_tool.sqlite`.

It contains only the local app tables currently used by the UI and API:

- `md_domains`
- `md_business_units`
- `md_product_types`
- `md_platforms`
- `md_priorities`
- `md_stages`
- `md_statuses`
- `md_subdomains`
- `md_users`
- `md_source_systems`
- `md_scope_options`
- `md_build_statuses`
- `md_stage_requirements`
- `data_product_requests_new`
- `request_stage_answers`
- `request_timeline`
