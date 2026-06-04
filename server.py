from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
APP_BACKEND = os.getenv("GOVERNANCE_BACKEND", "sqlite").strip().lower()
DB_PATH = Path(os.getenv("GOVERNANCE_SQLITE_PATH", ROOT / "governance_tool.sqlite"))
ADMIN_ROLE_KEYS = {"admin", "data_domain_owner", "domain_delivery_lead", "lynx_pm"}

MASTER_DATA_CONFIG = {
    "domains": {
        "table": "md_domains",
        "id": "domain_id",
        "name": "domain_name",
        "fields": [("name", "domain_name")],
    },
    "businessUnits": {
        "table": "md_business_units",
        "id": "business_unit_id",
        "name": "business_unit_name",
        "fields": [("name", "business_unit_name")],
    },
    "productTypes": {
        "table": "md_product_types",
        "id": "product_type_id",
        "name": "product_type_name",
        "fields": [("name", "product_type_name")],
    },
    "platforms": {
        "table": "md_platforms",
        "id": "platform_id",
        "name": "platform_name",
        "fields": [("name", "platform_name")],
    },
    "priorities": {
        "table": "md_priorities",
        "id": "priority_id",
        "name": "priority_name",
        "fields": [("name", "priority_name")],
    },
    "statuses": {
        "table": "md_statuses",
        "id": "status_id",
        "name": "status_name",
        "fields": [("name", "status_name")],
    },
    "subdomains": {
        "table": "md_subdomains",
        "id": "subdomain_id",
        "name": "subdomain_name",
        "fields": [("name", "subdomain_name"), ("domainId", "domain_id")],
    },
    "sourceSystems": {
        "table": "md_source_systems",
        "id": "source_system_id",
        "name": "source_system_name",
        "fields": [("name", "source_system_name")],
    },
    "scopeOptions": {
        "table": "md_scope_options",
        "id": "scope_id",
        "name": "scope_name",
        "fields": [("name", "scope_name"), ("type", "scope_type"), ("parentId", "parent_scope_id")],
    },
    "buildStatuses": {
        "table": "md_build_statuses",
        "id": "build_status_id",
        "name": "build_status_name",
        "fields": [("name", "build_status_name")],
    },
    "users": {
        "table": "md_users",
        "id": "user_id",
        "name": "display_name",
        "fields": [("name", "display_name"), ("email", "email"), ("roleKey", "role_key")],
    },
}

STAGES = [
    ("intake", "Intake", 1),
    ("reuse_domain", "Reuse / Domain", 2),
    ("ownership", "Ownership", 3),
    ("requirements", "Requirements", 4),
    ("architecture_review", "Architecture Review", 5),
    ("build_validate", "Build / Validate", 6),
    ("publish", "Publish", 7),
    ("operate", "Operate", 8),
]

STAGE_REQUIREMENTS = {
    "intake": [
        ("business_decision", "Business decision supported", "textarea", None, "Describe the decision this product supports."),
        ("expected_date", "Expected date", "date", None, "When is this product expected?"),
        ("additional_comments", "Additional comments", "textarea", None, "Any extra context for triage."),
    ],
    "reuse_domain": [
        ("lead_domain_id", "Lead domain", "select", "domains", "Select the accountable data domain."),
        ("lead_subdomain_id", "Lead subdomain", "select", "subdomains", "Assign the accountable subdomain for the selected domain."),
        ("reuse_checked", "Existing product reuse checked", "checkbox", None, "Confirm existing data products were checked first."),
    ],
    "ownership": [
        ("data_domain_owner_user_id", "Data Domain Owner", "select", "dataDomainOwners", "Select from master data."),
        ("source_system_id", "Source System", "select", "sourceSystems", "Select the approved source system."),
        ("domain_delivery_lead_user_id", "Domain Delivery Lead", "select", "domainDeliveryLeads", "Select from master data."),
        ("lynx_pm_user_id", "Lynx PM input", "select", "lynxPms", "Select the Lynx PM accountable for input."),
    ],
    "requirements": [
        ("kpis_defined", "KPIs defined", "checkbox", None, "Confirm KPIs are documented."),
        ("definitions_defined", "Definitions defined", "checkbox", None, "Confirm business definitions are documented."),
        ("grain_defined", "Grains defined", "checkbox", None, "Confirm product grains are documented."),
        ("sources_defined", "Sources defined", "checkbox", None, "Confirm source mapping is documented."),
        ("cde_defined", "CDE defined", "checkbox", None, "Confirm critical data elements are documented."),
        ("dq_rules_defined", "Data Quality rules defined", "checkbox", None, "Confirm quality rules are documented."),
    ],
    "architecture_review": [
        ("architecture_review_complete", "Architecture review complete", "checkbox", None, "Confirm design review is complete."),
        ("security_pattern_confirmed", "Security pattern confirmed", "checkbox", None, "Confirm access and security design is approved."),
        ("tooling_confirmed", "Databricks / Lynx tooling confirmed", "checkbox", None, "Confirm target tooling is approved."),
    ],
    "build_validate": [
        ("build_status_id", "Build status", "select", "buildStatuses", "Select the current build status."),
        ("build_evidence", "Build / test notes", "textarea", None, "Add evidence, blockers, UAT notes, or test summary."),
    ],
    "publish": [
        ("alation_documented", "Documented in Alation", "checkbox", None, "Confirm the product is documented in Alation."),
        ("release_notes", "Release notes", "textarea", None, "Add release notes or support context."),
    ],
    "operate": [
        ("support_model_confirmed", "Support model confirmed", "checkbox", None, "Confirm owner, refresh, and support model."),
        ("review_cycle_confirmed", "Review cycle confirmed", "checkbox", None, "Confirm value and quality review cadence."),
    ],
}

SEED_PRODUCTS = [
    ("REQ-001", "Revenue KPI rebuild", "structured", "databricks", "architecture_review", "blocked", "Waiting on approved source and DQ rules"),
    ("REQ-002", "Policy document search", "unstructured", "lynx", "build_validate", "in_progress", "Lynx content traceability under review"),
    ("REQ-003", "Customer 360 dataset", "mixed", "both", "ownership", "in_review", "Need named owner and source system"),
    ("REQ-004", "Marketing dashboard v2", "structured", "databricks", "operate", "operating", "Monthly review completed"),
    ("REQ-005", "Supplier knowledge base", "unstructured", "lynx", "requirements", "in_review", "Missing CDE and quality rules"),
    ("REQ-006", "Returns analytics layer", "structured", "databricks", "publish", "ready", "Awaiting Alation documentation"),
    ("REQ-007", "Pricing conditions master", "structured", "databricks", "reuse_domain", "in_review", "Domain assignment pending triage"),
    ("REQ-008", "Field trial outcomes report", "structured", "databricks", "requirements", "blocked", "Source system not yet confirmed"),
    ("REQ-009", "Grower loyalty index", "mixed", "both", "build_validate", "in_progress", "UAT in progress with commercial team"),
    ("REQ-010", "Digital agronomy event log", "unstructured", "lynx", "intake", "not_started", "New request submitted for triage"),
    ("REQ-011", "Seeds volume forecast", "structured", "databricks", "ownership", "in_review", "Awaiting domain delivery lead assignment"),
    ("REQ-012", "Trade terms compliance tracker", "structured", "databricks", "architecture_review", "in_review", "Security pattern under review"),
    ("REQ-013", "Crop protection market share", "structured", "databricks", "operate", "operating", "Stable, quarterly review scheduled"),
    ("REQ-014", "Channel partner scorecard", "mixed", "both", "publish", "ready", "Release notes drafted, Alation pending"),
    ("REQ-015", "SAP order discrepancy log", "structured", "databricks", "build_validate", "blocked", "Blocked on SAP integration access"),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    if APP_BACKEND != "sqlite":
        raise RuntimeError(
            "Only the sqlite backend is active in this build. Set GOVERNANCE_BACKEND=sqlite "
            "or wire the Databricks SQL adapter after creating the Unity Catalog schema."
        )
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def dict_rows(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def init_db() -> None:
    if APP_BACKEND != "sqlite":
        return
    with connect() as db:
        db.execute("PRAGMA foreign_keys = OFF")
        create_master_tables(db)
        migrate_request_table(db)
        create_workflow_tables(db)
        seed_master_data(db)
        seed_stage_requirements(db)
        seed_requests(db)
        backfill_demo_stage_answers(db)
        seed_missing_timelines(db)
        db.commit()


def create_master_tables(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS md_domains (
          domain_id TEXT PRIMARY KEY,
          domain_name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS md_business_units (
          business_unit_id TEXT PRIMARY KEY,
          business_unit_name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS md_product_types (
          product_type_id TEXT PRIMARY KEY,
          product_type_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS md_platforms (
          platform_id TEXT PRIMARY KEY,
          platform_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS md_priorities (
          priority_id TEXT PRIMARY KEY,
          priority_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS md_stages (
          stage_id TEXT PRIMARY KEY,
          stage_name TEXT NOT NULL UNIQUE,
          stage_number INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS md_statuses (
          status_id TEXT PRIMARY KEY,
          status_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS md_subdomains (
          subdomain_id TEXT PRIMARY KEY,
          subdomain_name TEXT NOT NULL,
          domain_id TEXT NOT NULL DEFAULT 'commercial'
        );
        CREATE TABLE IF NOT EXISTS md_users (
          user_id TEXT PRIMARY KEY,
          display_name TEXT NOT NULL,
          email TEXT NOT NULL,
          role_key TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS md_source_systems (
          source_system_id TEXT PRIMARY KEY,
          source_system_name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS md_scope_options (
          scope_id TEXT PRIMARY KEY,
          scope_name TEXT NOT NULL,
          scope_type TEXT NOT NULL,
          parent_scope_id TEXT
        );
        CREATE TABLE IF NOT EXISTS md_build_statuses (
          build_status_id TEXT PRIMARY KEY,
          build_status_name TEXT NOT NULL
        );
        """
    )
    ensure_column(db, "md_scope_options", "parent_scope_id", "TEXT")
    migrate_subdomains_table(db)


def migrate_subdomains_table(db: sqlite3.Connection) -> None:
    exists = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'md_subdomains'"
    ).fetchone()
    if not exists:
        return
    table_sql = db.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'md_subdomains'"
    ).fetchone()["sql"]
    columns = {row["name"] for row in db.execute("PRAGMA table_info(md_subdomains)").fetchall()}
    if "domain_id" in columns and "subdomain_name TEXT NOT NULL UNIQUE" not in table_sql:
        return

    db.execute("ALTER TABLE md_subdomains RENAME TO md_subdomains_old")
    db.execute(
        """
        CREATE TABLE md_subdomains (
          subdomain_id TEXT PRIMARY KEY,
          subdomain_name TEXT NOT NULL,
          domain_id TEXT NOT NULL DEFAULT 'commercial',
          UNIQUE(domain_id, subdomain_name)
        )
        """
    )
    old_columns = {row["name"] for row in db.execute("PRAGMA table_info(md_subdomains_old)").fetchall()}
    domain_expr = "domain_id" if "domain_id" in old_columns else "'commercial'"
    db.execute(
        f"""
        INSERT OR IGNORE INTO md_subdomains (subdomain_id, subdomain_name, domain_id)
        SELECT subdomain_id, subdomain_name, {domain_expr}
        FROM md_subdomains_old
        """
    )
    db.execute("DROP TABLE md_subdomains_old")


def ensure_column(db: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate_request_table(db: sqlite3.Connection) -> None:
    old_exists = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'data_product_requests'"
    ).fetchone()
    if old_exists:
        db.execute("ALTER TABLE data_product_requests RENAME TO data_product_requests_old")

    db.execute(
        """
        CREATE TABLE data_product_requests (
          request_id TEXT PRIMARY KEY,
          request_number TEXT NOT NULL UNIQUE,
          title TEXT NOT NULL,
          description TEXT,
          product_type_id TEXT NOT NULL,
          target_platform_id TEXT NOT NULL,
          priority_id TEXT NOT NULL,
          lead_domain_id TEXT NOT NULL,
          business_unit_id TEXT,
          scope_id TEXT,
          requester_name TEXT,
          requester_email TEXT,
          expected_date TEXT,
          additional_comments TEXT,
          current_stage_id TEXT NOT NULL,
          status_id TEXT NOT NULL,
          lead_subdomain_id TEXT,
          data_domain_owner_user_id TEXT,
          source_system_id TEXT,
          domain_delivery_lead_user_id TEXT,
          lynx_pm_user_id TEXT,
          build_status_id TEXT,
          note TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )

    if old_exists:
        old_columns = {row["name"] for row in db.execute("PRAGMA table_info(data_product_requests_old)").fetchall()}

        def col(name: str, fallback: str) -> str:
            return name if name in old_columns else fallback

        db.execute(
            f"""
            INSERT OR IGNORE INTO data_product_requests (
              request_id, request_number, title, description, product_type_id, target_platform_id,
              priority_id, lead_domain_id, business_unit_id, scope_id, requester_name,
              requester_email, expected_date, additional_comments, current_stage_id, status_id,
              lead_subdomain_id, data_domain_owner_user_id, source_system_id,
              domain_delivery_lead_user_id, lynx_pm_user_id, build_status_id, note, created_at, updated_at
            )
            SELECT
              request_id,
              request_number,
              title,
              {col('description', "''")},
              product_type_id,
              target_platform_id,
              CASE WHEN priority_id IN ('p1', 'p2', 'p3') THEN priority_id ELSE 'p2' END,
              'commercial',
              {col('business_unit_id', "NULL")},
              {col('scope_id', "NULL")},
              COALESCE({col('requester_name', col('requestor_name', "''"))}, ''),
              {col('requester_email', "''")},
              COALESCE({col('expected_date', "NULL")}, NULL),
              {col('additional_comments', "''")},
              CASE WHEN current_stage_id = 'governance_review' THEN 'architecture_review' ELSE current_stage_id END,
              CASE WHEN status_id IN ('not_started', 'in_review', 'in_progress', 'blocked', 'ready', 'operating', 'on_hold', 'cancelled', 'deprecated') THEN status_id ELSE 'in_review' END,
              {col('lead_subdomain_id', "NULL")},
              {col('data_domain_owner_user_id', "NULL")},
              {col('source_system_id', "NULL")},
              {col('domain_delivery_lead_user_id', "NULL")},
              {col('lynx_pm_user_id', "NULL")},
              {col('build_status_id', "NULL")},
              {col('note', "''")},
              created_at,
              updated_at
            FROM data_product_requests_old
            """
        )
        db.execute("DROP TABLE data_product_requests_old")


def create_workflow_tables(db: sqlite3.Connection) -> None:
    db.execute("DROP TABLE IF EXISTS md_stage_requirements")
    db.executescript(
        """
        CREATE TABLE md_stage_requirements (
          requirement_id TEXT PRIMARY KEY,
          stage_id TEXT NOT NULL,
          requirement_key TEXT NOT NULL,
          label TEXT NOT NULL,
          input_type TEXT NOT NULL,
          master_data_type TEXT,
          help_text TEXT NOT NULL,
          sort_order INTEGER NOT NULL,
          is_required INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS request_stage_answers (
          answer_id TEXT PRIMARY KEY,
          request_id TEXT NOT NULL,
          requirement_id TEXT NOT NULL,
          answer_value TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(request_id, requirement_id)
        );
        CREATE TABLE IF NOT EXISTS request_timeline (
          timeline_id TEXT PRIMARY KEY,
          request_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          stage_id TEXT,
          from_stage_id TEXT,
          to_stage_id TEXT,
          status_id TEXT,
          event_label TEXT NOT NULL,
          event_detail TEXT,
          created_by TEXT,
          created_at TEXT NOT NULL
        );
        """
    )


def seed_master_data(db: sqlite3.Connection) -> None:
    db.execute("INSERT OR IGNORE INTO md_domains VALUES ('commercial', 'Commercial')")
    db.execute("INSERT OR IGNORE INTO md_domains VALUES ('dummy_domain', 'Dummy Domain')")
    insert_missing(db, "md_business_units", [("cp", "CP"), ("seeds", "Seeds"), ("vegetables", "Vegetables")])
    insert_missing(db, "md_product_types", [("structured", "Structured"), ("unstructured", "Unstructured"), ("mixed", "Mixed")])
    insert_missing(db, "md_platforms", [("databricks", "Databricks"), ("lynx", "Lynx"), ("both", "Both")])
    insert_missing(db, "md_priorities", [("p1", "P1"), ("p2", "P2"), ("p3", "P3")])
    insert_missing(
        db,
        "md_statuses",
        [
            ("not_started", "Not started"),
            ("in_review", "In review"),
            ("in_progress", "In progress"),
            ("blocked", "Blocked"),
            ("ready", "Ready"),
            ("operating", "Operating"),
            ("on_hold", "On hold"),
            ("cancelled", "Cancelled"),
            ("deprecated", "Deprecated"),
        ],
    )
    insert_missing(db, "md_stages", STAGES)
    seed_commercial_subdomains(db)
    insert_missing(db, "md_subdomains", [("dummy_subdomain", "Dummy Subdomain", "dummy_domain")])
    insert_missing(
        db,
        "md_users",
        [
            ("admin_demo", "Demo Admin", "demo.admin@syngenta.com", "admin"),
            ("udo_anna", "Anna Khan", "anna.khan@syngenta.com", "data_domain_owner"),
            ("udo_maria", "Maria Rossi", "maria.rossi@syngenta.com", "data_domain_owner"),
            ("ddl_james", "James Silva", "james.silva@syngenta.com", "domain_delivery_lead"),
            ("ddl_nina", "Nina Brown", "nina.brown@syngenta.com", "domain_delivery_lead"),
            ("pm_lynx_maya", "Maya Patel", "maya.patel@syngenta.com", "lynx_pm"),
            ("pm_lynx_sam", "Sam Martin", "sam.martin@syngenta.com", "lynx_pm"),
        ],
    )
    insert_missing(
        db,
        "md_source_systems",
        [
            ("sap", "SAP"),
            ("salesforce", "Salesforce"),
            ("sharepoint", "SharePoint"),
            ("databricks", "Databricks"),
            ("manual_upload", "Manual upload"),
        ],
    )
    insert_missing(
        db,
        "md_scope_options",
        [
            ("global", "Global", "Global", None),
            ("europe", "Europe", "Region", None),
            ("latin_america", "Latin America", "Region", None),
            ("north_america", "North America", "Region", None),
            ("amea", "AMEA", "Region", None),
            ("janz", "JANZ", "Region", None),
            ("france", "France", "Country", "europe"),
            ("germany", "Germany", "Country", "europe"),
            ("brazil", "Brazil", "Country", "latin_america"),
            ("mexico", "Mexico", "Country", "latin_america"),
            ("usa", "United States", "Country", "north_america"),
            ("canada", "Canada", "Country", "north_america"),
            ("india", "India", "Country", "amea"),
            ("south_africa", "South Africa", "Country", "amea"),
            ("australia", "Australia", "Country", "janz"),
            ("new_zealand", "New Zealand", "Country", "janz"),
        ],
    )
    insert_missing(
        db,
        "md_build_statuses",
        [
            ("not_started", "Not started"),
            ("in_build", "In build"),
            ("testing", "Testing"),
            ("in_uat", "In UAT"),
            ("built", "Built"),
            ("blocked", "Blocked"),
        ],
    )


def insert_missing(db: sqlite3.Connection, table: str, rows: list[tuple]) -> None:
    placeholders = ", ".join(["?"] * len(rows[0]))
    db.executemany(f"INSERT OR IGNORE INTO {table} VALUES ({placeholders})", rows)


def seed_commercial_subdomains(db: sqlite3.Connection) -> None:
    commercial_subdomains = [
        ("non_transactional_customers", "Non Transactional Customers", "commercial"),
        ("pricing_conditions", "Pricing and Conditions", "commercial"),
        ("product_market_performance", "Product & Market Performance", "commercial"),
        ("sales_commercial_transactions", "Sales & Commercial Transactions", "commercial"),
        ("marketing_engagement", "Marketing & Engagement", "commercial"),
        ("digital_agronomy_solutions", "Digital & Agronomy Solutions", "commercial"),
    ]
    insert_missing(db, "md_subdomains", commercial_subdomains)
    replacements = {
        "customer": "non_transactional_customers",
        "sales": "sales_commercial_transactions",
        "marketing": "marketing_engagement",
        "finance": "pricing_conditions",
        "supply_chain": "product_market_performance",
    }
    for old_id, new_id in replacements.items():
        db.execute(
            "UPDATE data_product_requests SET lead_subdomain_id = ? WHERE lead_subdomain_id = ?",
            (new_id, old_id),
        )
        db.execute(
            """
            UPDATE request_stage_answers
            SET answer_value = ?
            WHERE answer_value = ?
              AND requirement_id LIKE 'reuse_domain_%'
            """,
            (new_id, old_id),
        )
    db.execute(
        """
        DELETE FROM md_subdomains
        WHERE domain_id = 'commercial'
          AND subdomain_id IN ('customer', 'sales', 'marketing', 'finance', 'supply_chain')
        """
    )


def seed_stage_requirements(db: sqlite3.Connection) -> None:
    db.execute("DELETE FROM md_stage_requirements")
    for stage_id, requirements in STAGE_REQUIREMENTS.items():
        for index, (key, label, input_type, master_type, help_text) in enumerate(requirements, start=1):
            db.execute(
                """
                INSERT INTO md_stage_requirements (
                  requirement_id, stage_id, requirement_key, label, input_type,
                  master_data_type, help_text, sort_order, is_required
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (f"{stage_id}_{key}", stage_id, key, label, input_type, master_type, help_text, index),
            )
    db.execute(
        """
        DELETE FROM request_stage_answers
        WHERE requirement_id NOT IN (SELECT requirement_id FROM md_stage_requirements)
        """
    )


def seed_requests(db: sqlite3.Connection) -> None:
    existing = db.execute("SELECT COUNT(*) AS count FROM data_product_requests").fetchone()["count"]
    if existing:
        return

    timestamp = now()
    for request_number, title, product_type, platform, stage, status, note in SEED_PRODUCTS:
        insert_request(
            db,
            {
                "request_number": request_number,
                "title": title,
                "description": note,
                "domain": "commercial",
                "businessUnit": "cp",
                "productType": product_type,
                "platform": platform,
                "priority": "p2",
                "scope": "global",
                "requester": "Demo Requester",
                "requesterEmail": "demo.requester@syngenta.com",
                "expectedDate": timestamp[:10],
                "additionalComments": note,
                "stage": stage,
                "status": status,
                "note": note,
            },
            timestamp,
        )


def seed_missing_timelines(db: sqlite3.Connection) -> None:
    rows = db.execute(
        """
        SELECT request_id, created_at
        FROM data_product_requests r
        WHERE NOT EXISTS (
          SELECT 1 FROM request_timeline t WHERE t.request_id = r.request_id
        )
        """
    ).fetchall()
    for row in rows:
        add_timeline(db, row["request_id"], "created", "Request created", "Existing request loaded into the clean schema.", created_at=row["created_at"])


def backfill_demo_stage_answers(db: sqlite3.Connection) -> None:
    demo_rows = db.execute(
        """
        SELECT request_id, request_number, current_stage_id, stage_number
        FROM data_product_requests r
        JOIN md_stages s ON s.stage_id = r.current_stage_id
        WHERE request_number BETWEEN 'REQ-001' AND 'REQ-006'
        """
    ).fetchall()
    timestamp = now()
    for row in demo_rows:
        requirements = db.execute(
            """
            SELECT req.*
            FROM md_stage_requirements req
            JOIN md_stages s ON s.stage_id = req.stage_id
            WHERE s.stage_number < ?
            ORDER BY s.stage_number, req.sort_order
            """,
            (row["stage_number"],),
        ).fetchall()
        for requirement in requirements:
            existing = db.execute(
                """
                SELECT 1 FROM request_stage_answers
                WHERE request_id = ? AND requirement_id = ?
                """,
                (row["request_id"], requirement["requirement_id"]),
            ).fetchone()
            if existing:
                continue
            value = demo_answer(requirement)
            db.execute(
                """
                INSERT INTO request_stage_answers (answer_id, request_id, requirement_id, answer_value, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), row["request_id"], requirement["requirement_id"], value, timestamp),
            )
            update_structured_field(db, row["request_id"], requirement["requirement_key"], value)


def demo_answer(requirement: sqlite3.Row) -> str:
    if requirement["input_type"] == "checkbox":
        return "true"
    if requirement["input_type"] == "date":
        return now()[:10]
    if requirement["master_data_type"] == "subdomains":
        return "sales_commercial_transactions"
    if requirement["master_data_type"] == "dataDomainOwners":
        return "udo_anna"
    if requirement["master_data_type"] == "sourceSystems":
        return "sap"
    if requirement["master_data_type"] == "domainDeliveryLeads":
        return "ddl_james"
    if requirement["master_data_type"] == "lynxPms":
        return "pm_lynx_maya"
    if requirement["master_data_type"] == "buildStatuses":
        return "testing"
    return f"Demo {requirement['label'].lower()} completed."


def next_request_number(db: sqlite3.Connection) -> str:
    count = db.execute("SELECT COUNT(*) AS count FROM data_product_requests").fetchone()["count"]
    return f"REQ-{count + 1:03d}"


def validate_payload(payload: dict) -> str | None:
    if not payload.get("title", "").strip():
        return "title is required"
    email = payload.get("requesterEmail", "").strip().lower()
    if not re.match(r"^[^@\s]+@syngenta\.com$", email):
        return "requester email must use syngenta.com"
    return None


def resolve_domain_id(db: sqlite3.Connection, domain_id: str | None) -> str:
    clean_domain_id = slug_id(domain_id or "commercial")
    exists = db.execute("SELECT 1 FROM md_domains WHERE domain_id = ?", (clean_domain_id,)).fetchone()
    if not exists:
        raise ValueError("domain is not valid")
    return clean_domain_id


def insert_request(db: sqlite3.Connection, payload: dict, timestamp: str | None = None) -> dict:
    timestamp = timestamp or now()
    request_id = str(uuid.uuid4())
    request_number = payload.get("request_number") or next_request_number(db)
    stage_id = payload.get("stage", "intake")
    status_id = payload.get("status", "in_review")
    domain_id = resolve_domain_id(db, payload.get("domain"))
    db.execute(
        """
        INSERT INTO data_product_requests (
          request_id, request_number, title, description, product_type_id, target_platform_id,
          priority_id, lead_domain_id, business_unit_id, scope_id, requester_name,
          requester_email, expected_date, additional_comments, current_stage_id, status_id,
          note, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request_id,
            request_number,
            payload.get("title", "").strip(),
            payload.get("description", "").strip(),
            payload.get("productType", "structured"),
            payload.get("platform", "databricks"),
            payload.get("priority", "p2"),
            domain_id,
            payload.get("businessUnit", "cp"),
            payload.get("scope", "global"),
            payload.get("requester", "").strip(),
            payload.get("requesterEmail", "").strip().lower(),
            payload.get("expectedDate", "").strip(),
            payload.get("additionalComments", "").strip(),
            stage_id,
            status_id,
            payload.get("note", "New request submitted for triage"),
            timestamp,
            timestamp,
        ),
    )
    add_timeline(db, request_id, "created", "Request created", "New request submitted.", stage_id=stage_id, status_id=status_id, created_by=payload.get("requesterEmail", ""), created_at=timestamp)
    return get_request_by_id(db, request_id)


def get_requests(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute(request_select_sql() + " ORDER BY r.created_at DESC").fetchall()
    return [serialize_request(row) for row in rows]


def get_requests_for_user(db: sqlite3.Connection, email: str) -> list[dict]:
    return get_requests(db)


def get_session(db: sqlite3.Connection, email: str) -> dict:
    clean_email = email.strip().lower()
    if not re.match(r"^[^@\s]+@syngenta\.com$", clean_email):
        return {"email": clean_email, "role": "requester", "canAdmin": False, "name": "Requester"}
    user = db.execute(
        """
        SELECT display_name, role_key
        FROM md_users
        WHERE LOWER(email) = ?
        """,
        (clean_email,),
    ).fetchone()
    can_admin = bool(user and user["role_key"] in ADMIN_ROLE_KEYS)
    can_delete_master_data = bool(user and user["role_key"] == "admin")
    return {
        "email": clean_email,
        "role": "admin" if can_admin else "requester",
        "canAdmin": can_admin,
        "canDeleteMasterData": can_delete_master_data,
        "name": user["display_name"] if user else clean_email.split("@")[0],
    }


def require_admin(db: sqlite3.Connection, email: str | None) -> None:
    if not get_session(db, email or "")["canAdmin"]:
        raise PermissionError("Admin access is required")


def get_master_data(db: sqlite3.Connection) -> dict:
    users = dict_rows(db.execute("SELECT user_id AS id, display_name AS name, email, role_key FROM md_users ORDER BY display_name").fetchall())
    return {
        "domains": dict_rows(db.execute("SELECT domain_id AS id, domain_name AS name FROM md_domains ORDER BY domain_name").fetchall()),
        "businessUnits": dict_rows(db.execute("SELECT business_unit_id AS id, business_unit_name AS name FROM md_business_units ORDER BY business_unit_name").fetchall()),
        "productTypes": dict_rows(db.execute("SELECT product_type_id AS id, product_type_name AS name FROM md_product_types ORDER BY product_type_name").fetchall()),
        "platforms": dict_rows(db.execute("SELECT platform_id AS id, platform_name AS name FROM md_platforms ORDER BY platform_name").fetchall()),
        "priorities": dict_rows(db.execute("SELECT priority_id AS id, priority_name AS name FROM md_priorities ORDER BY priority_name").fetchall()),
        "stages": dict_rows(db.execute("SELECT stage_id AS id, stage_name AS name, stage_number AS number FROM md_stages ORDER BY stage_number").fetchall()),
        "statuses": dict_rows(db.execute("SELECT status_id AS id, status_name AS name FROM md_statuses ORDER BY status_name").fetchall()),
        "subdomains": dict_rows(
            db.execute(
                """
                SELECT
                  s.subdomain_id AS id,
                  s.subdomain_name AS name,
                  s.domain_id AS domainId,
                  d.domain_name AS domainName
                FROM md_subdomains s
                JOIN md_domains d ON d.domain_id = s.domain_id
                ORDER BY d.domain_name, s.subdomain_name
                """
            ).fetchall()
        ),
        "sourceSystems": dict_rows(db.execute("SELECT source_system_id AS id, source_system_name AS name FROM md_source_systems ORDER BY source_system_name").fetchall()),
        "scopeOptions": dict_rows(db.execute("SELECT scope_id AS id, scope_name AS name, scope_type AS type, parent_scope_id AS parentId FROM md_scope_options ORDER BY CASE scope_type WHEN 'Global' THEN 0 WHEN 'Region' THEN 1 ELSE 2 END, scope_name").fetchall()),
        "buildStatuses": dict_rows(db.execute("SELECT build_status_id AS id, build_status_name AS name FROM md_build_statuses ORDER BY build_status_name").fetchall()),
        "dataDomainOwners": [user for user in users if user["role_key"] == "data_domain_owner"],
        "domainDeliveryLeads": [user for user in users if user["role_key"] == "domain_delivery_lead"],
        "lynxPms": [user for user in users if user["role_key"] == "lynx_pm"],
        "users": users,
    }


def upsert_master_data_item(db: sqlite3.Connection, collection: str, payload: dict) -> dict:
    config = MASTER_DATA_CONFIG.get(collection)
    if not config:
        raise ValueError("Unsupported master data collection")
    item_id = slug_id(payload.get("id") or payload.get("name") or payload.get("email") or "")
    if not item_id:
        raise ValueError("id or name is required")
    columns = [config["id"]]
    values = [item_id]
    for payload_key, column in config["fields"]:
        value = payload.get(payload_key, "")
        if payload_key == "email":
            value = str(value).strip().lower()
            if value and not re.match(r"^[^@\s]+@syngenta\.com$", value):
                raise ValueError("user email must use syngenta.com")
        elif payload_key == "roleKey":
            value = slug_id(value or "requester")
        elif payload_key == "type":
            value = value or "Region"
        elif payload_key == "parentId":
            value = value or None
        elif payload_key == "domainId":
            value = slug_id(value or "commercial")
            domain_exists = db.execute("SELECT 1 FROM md_domains WHERE domain_id = ?", (value,)).fetchone()
            if not domain_exists:
                raise ValueError("domainId is not valid")
        else:
            value = str(value).strip()
        if payload_key != "parentId" and not value:
            raise ValueError(f"{payload_key} is required")
        columns.append(column)
        values.append(value)
    placeholders = ", ".join(["?"] * len(values))
    assignments = ", ".join([f"{column} = excluded.{column}" for column in columns[1:]])
    db.execute(
        f"""
        INSERT INTO {config['table']} ({", ".join(columns)})
        VALUES ({placeholders})
        ON CONFLICT({config['id']})
        DO UPDATE SET {assignments}
        """,
        values,
    )
    return {"id": item_id, **payload}


def delete_master_data_item(db: sqlite3.Connection, collection: str, item_id: str) -> dict:
    config = MASTER_DATA_CONFIG.get(collection)
    if not config:
        raise ValueError("Unsupported master data collection")
    protected = {
        "businessUnits": {"cp", "seeds", "vegetables"},
        "domains": {"commercial"},
        "stages": {stage[0] for stage in STAGES},
    }
    if item_id in protected.get(collection, set()):
        raise ValueError("This master data item is protected")
    db.execute(f"DELETE FROM {config['table']} WHERE {config['id']} = ?", (item_id,))
    return {"deleted": item_id}


def slug_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def request_select_sql() -> str:
    return """
        SELECT
          r.*,
          d.domain_name,
          bu.business_unit_name,
          pt.product_type_name,
          p.platform_name,
          pr.priority_name,
          s.stage_name,
          s.stage_number,
          st.status_name,
          scope.scope_name,
          sub.subdomain_name,
          sub.domain_id AS subdomain_domain_id,
          ddo.display_name AS data_domain_owner_name,
          ddo.email AS data_domain_owner_email,
          src.source_system_name,
          ddl.display_name AS domain_delivery_lead_name,
          lpm.display_name AS lynx_pm_name,
          bs.build_status_name
          ,
          COALESCE(
            (
              SELECT MAX(t.created_at)
              FROM request_timeline t
              WHERE t.request_id = r.request_id
                AND t.event_type = 'stage_advanced'
                AND t.to_stage_id = r.current_stage_id
            ),
            (
              SELECT MAX(t.created_at)
              FROM request_timeline t
              WHERE t.request_id = r.request_id
                AND t.stage_id = r.current_stage_id
            ),
            r.created_at
          ) AS current_stage_entered_at
        FROM data_product_requests r
        JOIN md_domains d ON d.domain_id = r.lead_domain_id
        LEFT JOIN md_business_units bu ON bu.business_unit_id = r.business_unit_id
        JOIN md_product_types pt ON pt.product_type_id = r.product_type_id
        JOIN md_platforms p ON p.platform_id = r.target_platform_id
        JOIN md_priorities pr ON pr.priority_id = r.priority_id
        JOIN md_stages s ON s.stage_id = r.current_stage_id
        JOIN md_statuses st ON st.status_id = r.status_id
        LEFT JOIN md_scope_options scope ON scope.scope_id = r.scope_id
        LEFT JOIN md_subdomains sub ON sub.subdomain_id = r.lead_subdomain_id
        LEFT JOIN md_users ddo ON ddo.user_id = r.data_domain_owner_user_id
        LEFT JOIN md_source_systems src ON src.source_system_id = r.source_system_id
        LEFT JOIN md_users ddl ON ddl.user_id = r.domain_delivery_lead_user_id
        LEFT JOIN md_users lpm ON lpm.user_id = r.lynx_pm_user_id
        LEFT JOIN md_build_statuses bs ON bs.build_status_id = r.build_status_id
    """


def get_request_by_id(db: sqlite3.Connection, request_id: str) -> dict:
    row = db.execute(request_select_sql() + " WHERE r.request_id = ?", (request_id,)).fetchone()
    if not row:
        raise ValueError("request not found")
    return serialize_request(row)


def get_workflow(db: sqlite3.Connection, request_id: str) -> dict:
    request = get_request_by_id(db, request_id)
    stages = db.execute("SELECT stage_id, stage_name, stage_number FROM md_stages ORDER BY stage_number").fetchall()
    workflow_stages = []
    previous_complete = True
    for stage in stages:
        requirements = get_stage_requirements(db, request_id, stage["stage_id"])
        complete = all(is_answer_complete(item) for item in requirements)
        workflow_stages.append(
            {
                "stageId": stage["stage_id"],
                "name": stage["stage_name"],
                "number": stage["stage_number"],
                "requirements": requirements,
                "complete": complete,
                "canSubmit": previous_complete,
                "isCurrent": stage["stage_id"] == request["stageId"],
            }
        )
        previous_complete = previous_complete and complete
    timeline = dict_rows(
        db.execute(
            """
            SELECT t.*, s.stage_name, st.status_name
            FROM request_timeline t
            LEFT JOIN md_stages s ON s.stage_id = t.stage_id
            LEFT JOIN md_statuses st ON st.status_id = t.status_id
            WHERE t.request_id = ?
            ORDER BY t.created_at DESC
            """,
            (request_id,),
        ).fetchall()
    )
    return {"request": request, "stages": workflow_stages, "timeline": timeline}


def get_stage_requirements(db: sqlite3.Connection, request_id: str, stage_id: str) -> list[dict]:
    rows = db.execute(
        """
        SELECT
          req.requirement_id,
          req.stage_id,
          req.requirement_key,
          req.label,
          req.input_type,
          req.master_data_type,
          req.help_text,
          req.is_required,
          CASE req.requirement_key
            WHEN 'lead_domain_id' THEN r.lead_domain_id
            WHEN 'lead_subdomain_id' THEN COALESCE(r.lead_subdomain_id, '')
            WHEN 'expected_date' THEN COALESCE(r.expected_date, '')
            WHEN 'additional_comments' THEN COALESCE(r.additional_comments, '')
            ELSE COALESCE(ans.answer_value, '')
          END AS answer_value
        FROM md_stage_requirements req
        JOIN data_product_requests r
          ON r.request_id = ?
        LEFT JOIN request_stage_answers ans
          ON ans.requirement_id = req.requirement_id
         AND ans.request_id = ?
        WHERE req.stage_id = ?
        ORDER BY req.sort_order
        """,
        (request_id, request_id, stage_id),
    ).fetchall()
    return [dict(row) for row in rows]


def is_answer_complete(item: dict) -> bool:
    value = str(item["answer_value"] or "").strip()
    if item["input_type"] == "checkbox":
        return value == "true"
    return bool(value)


def save_workflow_answers(db: sqlite3.Connection, request_id: str, payload: dict) -> dict:
    timestamp = now()
    stage_id = payload.get("stageId")
    if not stage_id:
        raise ValueError("stageId is required")

    workflow = get_workflow(db, request_id)
    stage = next((item for item in workflow["stages"] if item["stageId"] == stage_id), None)
    if not stage:
        raise ValueError("stage not found")
    if not stage["canSubmit"]:
        raise PermissionError("Previous stages must be completed before this stage can be submitted")

    requirement_by_id = {item["requirement_id"]: item for item in stage["requirements"]}
    answers = payload.get("answers", {})
    for requirement_id, answer_value in answers.items():
        requirement = requirement_by_id.get(requirement_id)
        if not requirement:
            continue
        clean_value = "true" if requirement["input_type"] == "checkbox" and answer_value else str(answer_value).strip()
        db.execute(
            """
            INSERT INTO request_stage_answers (answer_id, request_id, requirement_id, answer_value, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(request_id, requirement_id)
            DO UPDATE SET answer_value = excluded.answer_value, updated_at = excluded.updated_at
            """,
            (str(uuid.uuid4()), request_id, requirement_id, clean_value, timestamp),
        )
        update_structured_field(db, request_id, requirement["requirement_key"], clean_value)

    reconcile_domain_subdomain(db, request_id)

    status_id = payload.get("statusId")
    if status_id:
        db.execute("UPDATE data_product_requests SET status_id = ? WHERE request_id = ?", (status_id, request_id))
        add_timeline(db, request_id, "status_changed", "Status updated", f"Status changed to {status_id}.", stage_id=stage_id, status_id=status_id, created_by=payload.get("updatedBy", "admin"), created_at=timestamp)

    add_timeline(db, request_id, "answers_saved", f"{stage['name']} saved", "Stage information was saved.", stage_id=stage_id, status_id=status_id, created_by=payload.get("updatedBy", "admin"), created_at=timestamp)
    advanced = advance_if_complete(db, request_id, stage_id, timestamp)
    db.execute("UPDATE data_product_requests SET updated_at = ? WHERE request_id = ?", (timestamp, request_id))
    result = get_workflow(db, request_id)
    result["advanced"] = advanced
    return result


def save_request_status(db: sqlite3.Connection, request_id: str, payload: dict) -> dict:
    timestamp = now()
    status_id = payload.get("statusId")
    if not status_id:
        raise ValueError("statusId is required")
    exists = db.execute("SELECT 1 FROM md_statuses WHERE status_id = ?", (status_id,)).fetchone()
    if not exists:
        raise ValueError("statusId is not valid")
    current = db.execute("SELECT current_stage_id FROM data_product_requests WHERE request_id = ?", (request_id,)).fetchone()
    if not current:
        raise ValueError("request not found")
    db.execute(
        "UPDATE data_product_requests SET status_id = ?, updated_at = ? WHERE request_id = ?",
        (status_id, timestamp, request_id),
    )
    add_timeline(
        db,
        request_id,
        "status_changed",
        "Status updated",
        f"Status changed to {status_id}.",
        stage_id=current["current_stage_id"],
        status_id=status_id,
        created_by=payload.get("updatedBy", "admin"),
        created_at=timestamp,
    )
    return get_workflow(db, request_id)


def update_structured_field(db: sqlite3.Connection, request_id: str, key: str, value: str) -> None:
    field_map = {
        "lead_domain_id": "lead_domain_id",
        "lead_subdomain_id": "lead_subdomain_id",
        "data_domain_owner_user_id": "data_domain_owner_user_id",
        "source_system_id": "source_system_id",
        "domain_delivery_lead_user_id": "domain_delivery_lead_user_id",
        "lynx_pm_user_id": "lynx_pm_user_id",
        "build_status_id": "build_status_id",
        "expected_date": "expected_date",
        "additional_comments": "additional_comments",
    }
    column = field_map.get(key)
    if column:
        db.execute(f"UPDATE data_product_requests SET {column} = ? WHERE request_id = ?", (value, request_id))


def reconcile_domain_subdomain(db: sqlite3.Connection, request_id: str) -> None:
    row = db.execute(
        """
        SELECT r.lead_domain_id, r.lead_subdomain_id, s.domain_id AS subdomain_domain_id
        FROM data_product_requests r
        LEFT JOIN md_subdomains s ON s.subdomain_id = r.lead_subdomain_id
        WHERE r.request_id = ?
        """,
        (request_id,),
    ).fetchone()
    if not row or not row["lead_subdomain_id"]:
        return
    if row["lead_domain_id"] == row["subdomain_domain_id"]:
        return
    db.execute("UPDATE data_product_requests SET lead_subdomain_id = NULL WHERE request_id = ?", (request_id,))
    db.execute(
        """
        DELETE FROM request_stage_answers
        WHERE request_id = ?
          AND requirement_id IN ('reuse_domain_lead_subdomain_id')
        """,
        (request_id,),
    )


def advance_if_complete(db: sqlite3.Connection, request_id: str, saved_stage_id: str, timestamp: str) -> bool:
    current = db.execute(
        """
        SELECT r.current_stage_id, s.stage_number
        FROM data_product_requests r
        JOIN md_stages s ON s.stage_id = r.current_stage_id
        WHERE r.request_id = ?
        """,
        (request_id,),
    ).fetchone()
    if not current or current["current_stage_id"] != saved_stage_id:
        return False

    missing = db.execute(
        """
        SELECT COUNT(*) AS missing_count
        FROM md_stage_requirements req
        LEFT JOIN request_stage_answers ans
          ON ans.requirement_id = req.requirement_id
         AND ans.request_id = ?
        WHERE req.stage_id = ?
          AND req.is_required = 1
          AND (
            ans.answer_value IS NULL
            OR TRIM(ans.answer_value) = ''
            OR (req.input_type = 'checkbox' AND ans.answer_value <> 'true')
          )
        """,
        (request_id, saved_stage_id),
    ).fetchone()["missing_count"]
    if missing:
        return False

    next_stage = db.execute(
        "SELECT stage_id FROM md_stages WHERE stage_number > ? ORDER BY stage_number LIMIT 1",
        (current["stage_number"],),
    ).fetchone()
    if not next_stage:
        db.execute("UPDATE data_product_requests SET status_id = 'operating' WHERE request_id = ?", (request_id,))
        add_timeline(db, request_id, "completed", "Workflow completed", "All stages are complete.", stage_id=saved_stage_id, status_id="operating", created_by="admin", created_at=timestamp)
        return False

    next_status = "operating" if next_stage["stage_id"] == "operate" else "in_review"
    db.execute(
        """
        UPDATE data_product_requests
        SET current_stage_id = ?, status_id = ?, note = 'Advanced automatically after required information was completed.'
        WHERE request_id = ?
        """,
        (next_stage["stage_id"], next_status, request_id),
    )
    add_timeline(db, request_id, "stage_advanced", "Stage advanced", f"Advanced from {saved_stage_id} to {next_stage['stage_id']}.", stage_id=next_stage["stage_id"], from_stage_id=saved_stage_id, to_stage_id=next_stage["stage_id"], status_id=next_status, created_by="system", created_at=timestamp)
    return True


def add_timeline(
    db: sqlite3.Connection,
    request_id: str,
    event_type: str,
    event_label: str,
    event_detail: str = "",
    stage_id: str | None = None,
    from_stage_id: str | None = None,
    to_stage_id: str | None = None,
    status_id: str | None = None,
    created_by: str | None = None,
    created_at: str | None = None,
) -> None:
    db.execute(
        """
        INSERT INTO request_timeline (
          timeline_id, request_id, event_type, stage_id, from_stage_id, to_stage_id,
          status_id, event_label, event_detail, created_by, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (str(uuid.uuid4()), request_id, event_type, stage_id, from_stage_id, to_stage_id, status_id, event_label, event_detail, created_by or "system", created_at or now()),
    )


def serialize_request(row: sqlite3.Row) -> dict:
    current_stage_entered_at = row["current_stage_entered_at"] or row["created_at"]
    return {
        "id": row["request_number"],
        "requestId": row["request_id"],
        "title": row["title"],
        "description": row["description"] or "",
        "domain": row["domain_name"],
        "domainId": row["lead_domain_id"],
        "businessUnit": row["business_unit_name"] or "",
        "type": row["product_type_name"],
        "platform": row["platform_name"],
        "priority": row["priority_name"],
        "scope": row["scope_name"] or "",
        "requester": row["requester_name"] or "",
        "requesterEmail": row["requester_email"] or "",
        "expectedDate": row["expected_date"] or "",
        "additionalComments": row["additional_comments"] or "",
        "stage": row["stage_name"],
        "stageId": row["current_stage_id"],
        "stageNumber": row["stage_number"],
        "currentStageEnteredAt": format_date(current_stage_entered_at),
        "daysInStage": days_since(current_stage_entered_at),
        "status": row["status_name"],
        "statusId": row["status_id"],
        "leadSubdomain": row["subdomain_name"] or "",
        "leadSubdomainDomainId": row["subdomain_domain_id"] or "",
        "dataDomainOwner": row["data_domain_owner_name"] or "",
        "sourceSystem": row["source_system_name"] or "",
        "domainDeliveryLead": row["domain_delivery_lead_name"] or "",
        "lynxPm": row["lynx_pm_name"] or "",
        "buildStatus": row["build_status_name"] or "",
        "owner": row["data_domain_owner_name"] or row["requester_name"] or "Unassigned",
        "note": row["note"] or "",
    }


def days_since(value: str) -> int:
    try:
        entered_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0
    return max(0, (datetime.now(timezone.utc) - entered_at).days)


def format_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return value[:10]


class GovernanceHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path == "/api/health":
                self.send_json({"ok": True, "backend": APP_BACKEND, "database": str(DB_PATH)})
                return
            if path == "/api/session":
                with connect() as db:
                    self.send_json(get_session(db, query.get("email", [""])[0]))
                return
            if path == "/api/master-data":
                with connect() as db:
                    self.send_json(get_master_data(db))
                return
            if path == "/api/requests":
                with connect() as db:
                    email = query.get("email", [""])[0]
                    self.send_json(get_requests_for_user(db, email) if email else get_requests(db))
                return
            if path.startswith("/api/requests/") and path.endswith("/workflow"):
                request_id = path.split("/")[3]
                with connect() as db:
                    self.send_json(get_workflow(db, request_id))
                return
            super().do_GET()
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        try:
            if path.startswith("/api/requests/") and path.endswith("/answers"):
                request_id = path.split("/")[3]
                with connect() as db:
                    require_admin(db, self.headers.get("X-User-Email"))
                    result = save_workflow_answers(db, request_id, payload)
                    db.commit()
                self.send_json(result)
                return

            if path.startswith("/api/requests/") and path.endswith("/status"):
                request_id = path.split("/")[3]
                with connect() as db:
                    require_admin(db, self.headers.get("X-User-Email"))
                    result = save_request_status(db, request_id, payload)
                    db.commit()
                self.send_json(result)
                return

            if path.startswith("/api/master-data/"):
                collection = path.split("/")[3]
                with connect() as db:
                    require_admin(db, self.headers.get("X-User-Email"))
                    result = upsert_master_data_item(db, collection, payload)
                    db.commit()
                    master_data = get_master_data(db)
                self.send_json({"saved": result, "masterData": master_data}, status=201)
                return

            if path != "/api/requests":
                self.send_error(404)
                return

            error = validate_payload(payload)
            if error:
                self.send_json({"error": error}, status=400)
                return

            with connect() as db:
                created = insert_request(db, payload)
                db.commit()
            self.send_json(created, status=201)
        except PermissionError as exc:
            self.send_json({"error": str(exc)}, status=409)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, status=400)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        try:
            if path.startswith("/api/master-data/"):
                parts = path.split("/")
                if len(parts) != 5:
                    self.send_error(404)
                    return
                with connect() as db:
                    session = get_session(db, self.headers.get("X-User-Email") or "")
                    if not session.get("canDeleteMasterData"):
                        self.send_json({"error": "Only admins can remove master data"}, status=403)
                        return
                    result = delete_master_data_item(db, parts[3], parts[4])
                    db.commit()
                    master_data = get_master_data(db)
                self.send_json({"deleted": result, "masterData": master_data})
                return
            self.send_error(404)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    init_db()
    port = int(sys.argv[1] if len(sys.argv) > 1 else os.getenv("DATABRICKS_APP_PORT", os.getenv("PORT", "8502")))
    server = ThreadingHTTPServer(("0.0.0.0", port), GovernanceHandler)
    print(f"Serving Governance Input Tool on http://localhost:{port}", flush=True)
    print(f"Backend: {APP_BACKEND}", flush=True)
    if APP_BACKEND == "sqlite":
        print(f"SQLite database: {DB_PATH}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
