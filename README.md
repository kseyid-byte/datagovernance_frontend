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

## Files

- `index.html` - application shell and screens
- `styles.css` - layout and visual design
- `app.js` - dashboard state, request creation, filtering, and API calls
- `server.py` - local static server plus temporary SQLite API
- `governance_tool.sqlite` - local database created automatically when the server starts
- `schema.sql` - clean schema matching the current local app data model

## Next backend step

Replace the SQLite calls in `server.py` with Databricks SQL / Delta table calls.

## Temporary workflow behavior

- Master data is read from the local database through `/api/master-data`.
- The active domain list is currently locked to `Commercial`.
- New request emails must use the `@syngenta.com` format.
- Scope supports Global, regions, and countries tied to their parent region.
- Admin workflow data is read from `/api/requests/{request_id}/workflow`.
- Admins can see every stage, but a stage can be submitted only when previous stages are complete.
- Saving all required fields for the current stage automatically advances the product to the next stage.

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
- `data_product_requests`
- `request_stage_answers`
- `request_timeline`
