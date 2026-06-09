# Governance Input Tool

Browser-native UI prototype for capturing and tracking governed data product requests.

The current scope is intentionally focused:

- Overview dashboard
- Governance process rail
- Product pipeline table
- Attention list for blocked or in-review products
- New request form
- Admin workflow screen for completing stage requirements
- Master-data driven dropdowns for domain, BU, priority, region/country scope, subdomain, source system, role assignments, status, and build status
- Timeline capture for request creation, stage saves, status changes, and automatic movement
- Role-based local access using a Syngenta email: requesters see their own requests; admins see workflow and master-data maintenance.
- Admin master-data maintenance for adding/removing lookup values.
- Temporary SQLite persistence through `server.py`

There is no Streamlit dependency. The UI is plain HTML, CSS, and JavaScript so the layout is fully controlled. A small Python backend is included for local API testing.

## Run locally

```bash
python3 server.py 8502
```

Open:

```text
http://localhost:8502
```

The Databricks entrypoint also works locally:

```bash
DATABRICKS_APP_PORT=8502 python3 app.py
```

## Files

- `index.html` - application shell and screens
- `styles.css` - layout and visual design
- `app.js` - dashboard state, request creation, filtering, and API calls
- `app.py` - Databricks App entrypoint
- `app.yaml` - Databricks App runtime command and demo environment
- `server.py` - local static server plus temporary SQLite API
- `requirements.txt` - Python dependency manifest for Databricks Apps
- `governance_tool.sqlite` - local database created automatically when the server starts
- `schema.sql` - clean schema matching the current local app data model
- `sql/databricks_schema.sql` - Unity Catalog / Delta table DDL template
- `sql/seed_master_data.sql` - Databricks SQL seed data for master data and stage requirements
- `docs/databricks-app.md` - Databricks deployment checklist and backend switch notes

## Databricks App deployment

The repository can be used as a custom Databricks App source today.

Current `app.yaml` runs the app in demo mode with SQLite stored at `/tmp/governance_tool.sqlite`. This is suitable for validating the UI and workflow in Databricks App compute, but it is not the durable production backend.

To deploy from Git:

1. Create a custom Databricks App.
2. Use Git source `https://github.com/kseyid-byte/datagovernance_frontend`.
3. Use branch `main` and source path `/`.
4. Deploy.

For the durable backend, create a Unity Catalog schema, run `sql/databricks_schema.sql`, run `sql/seed_master_data.sql`, then switch the backend from SQLite to a Databricks SQL adapter.

See `docs/databricks-app.md` for the exact checklist.

## Temporary workflow behavior

- Master data is read from the local database through `/api/master-data`.
- Domains are read from master data in the intake form.
- New request emails must use the `@syngenta.com` format.
- Scope supports Global and regional scope. Countries can be added later if needed.
- Domains are master data. Subdomains are tied to a parent domain so new domains and their own subdomains can be added later.
- Commercial is seeded with: Non Transactional Customers, Pricing and Conditions, Product & Market Performance, Sales & Commercial Transactions, Marketing & Engagement, Digital & Agronomy Solutions.
- Dummy Domain and Dummy Subdomain are seeded for testing domain changes.
- Admin workflow data is read from `/api/requests/{request_id}/workflow`.
- Admins can see every stage, but a stage can be submitted only when previous stages are complete.
- Saving all required fields for the current stage automatically advances the product to the next stage.
- Admin-only write APIs require `X-User-Email` with an admin email configured in `md_users`.
- Demo admin email: `demo.admin@syngenta.com`.

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

The current temporary app database is `governance_tool.sqlite`.

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
