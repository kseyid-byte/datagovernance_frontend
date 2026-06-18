from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
LAKEBASE_SCHEMA = os.getenv("GOVERNANCE_LAKEBASE_SCHEMA", "governance_app").strip() or "governance_app"
STARTUP_ERROR: str | None = None
ADMIN_ROLE_KEYS = {"admin", "data_domain_owner", "domain_delivery_lead", "hub_owner", "lynx_pm"}
CONFIGURED_ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.getenv("GOVERNANCE_ADMIN_EMAILS", "").split(",")
    if email.strip()
}
MASTER_DATA_CACHE_SECONDS = 300
MASTER_DATA_CACHE = {"expires_at": 0.0, "data": None}
LAKEBASE_TOKEN_CACHE = {"expires_at": 0.0, "token": ""}
MAX_REQUEST_BODY_BYTES = 1_000_000
MAX_TEXT_LENGTH = 500
MAX_TEXTAREA_LENGTH = 4000
MAX_URL_LENGTH = 2048
TRUSTED_IDENTITY_HEADERS = [
    "X-Forwarded-Email",
    "X-Forwarded-Preferred-Username",
    "X-Forwarded-User",
    "X-Forwarded-Login",
    "X-Databricks-User-Email",
    "X-Databricks-User",
]

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
    "expectedOutputs": {
        "table": "md_expected_outputs",
        "id": "expected_output_id",
        "name": "expected_output_name",
        "fields": [("name", "expected_output_name")],
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

CAMEL_CASE_KEYS = {
    "stageid": "stageId",
    "statusid": "statusId",
    "domainid": "domainId",
    "domainname": "domainName",
    "parentid": "parentId",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LakebaseConnection:
    def __init__(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("psycopg[binary] is required for Lakebase") from exc

        conninfo = os.getenv("GOVERNANCE_LAKEBASE_DSN", "").strip() or os.getenv("DATABASE_URL", "").strip()
        connect_kwargs = {"row_factory": dict_row}
        if not conninfo and not os.getenv("PGHOST", "").strip():
            raise RuntimeError(
                "Lakebase connection settings were not found. Add the Lakebase database resource "
                "to the Databricks App so PGHOST, PGPORT, PGDATABASE, PGUSER, and PGSSLMODE are set."
            )
        password = lakebase_password()
        if password:
            connect_kwargs["password"] = password
        elif not os.getenv("PGPASSWORD", "").strip():
            raise RuntimeError(
                "Lakebase password/token was not found. Add DATABRICKS_POSTGRES_ENDPOINT with "
                "valueFrom: governance-lakebase, or provide PGPASSWORD through a Databricks secret."
            )
        if "sslmode=" not in conninfo and not os.getenv("PGSSLMODE", "").strip():
            connect_kwargs["sslmode"] = "require"

        self.connection = psycopg.connect(conninfo, **connect_kwargs)
        self.execute(f"SET search_path TO {quote_postgres_identifier(LAKEBASE_SCHEMA)}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, _tb):
        self.close()

    def execute(self, statement: str, params: tuple | list | None = None):
        cursor = self.connection.cursor()
        if params:
            cursor.execute(postgres_statement(statement), tuple(params))
        else:
            cursor.execute(statement)
        return cursor

    def executemany(self, statement: str, rows: list[tuple]):
        cursor = self.connection.cursor()
        cursor.executemany(postgres_statement(statement), rows)
        return cursor

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        self.connection.close()


def quote_postgres_identifier(value: str) -> str:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", value):
        raise ValueError(f"Invalid PostgreSQL identifier: {value}")
    return f'"{value}"'


def postgres_statement(statement: str) -> str:
    return statement.replace("%", "%%").replace("?", "%s")


def lakebase_password() -> str:
    explicit_password = first_env_value(
        "PGPASSWORD",
        "POSTGRES_PASSWORD",
        "DATABRICKS_DATABASE_PASSWORD",
        "DATABRICKS_POSTGRES_PASSWORD",
        "GOVERNANCE_LAKEBASE_PASSWORD",
    )
    if explicit_password:
        return explicit_password

    endpoint = first_env_value(
        "DATABRICKS_POSTGRES_ENDPOINT",
        "DATABRICKS_DATABASE_ENDPOINT",
        "LAKEBASE_ENDPOINT",
        "GOVERNANCE_LAKEBASE_ENDPOINT",
    )
    if not endpoint:
        return ""

    cached_token = str(LAKEBASE_TOKEN_CACHE.get("token") or "")
    if cached_token and float(LAKEBASE_TOKEN_CACHE.get("expires_at") or 0) > time.time() + 120:
        return cached_token

    try:
        from databricks.sdk import WorkspaceClient
    except ImportError as exc:
        raise RuntimeError(
            "databricks-sdk is required to generate Lakebase OAuth database credentials"
        ) from exc

    credential = WorkspaceClient().postgres.generate_database_credential(endpoint=endpoint)
    token = getattr(credential, "token", "") or ""
    if not token:
        raise RuntimeError("Databricks did not return a Lakebase database credential token")

    LAKEBASE_TOKEN_CACHE["token"] = token
    LAKEBASE_TOKEN_CACHE["expires_at"] = lakebase_token_expiry_epoch(getattr(credential, "expire_time", None))
    return token


def first_env_value(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def lakebase_token_expiry_epoch(expire_time: object) -> float:
    if expire_time is None:
        return time.time() + 50 * 60
    timestamp = getattr(expire_time, "timestamp", None)
    if callable(timestamp):
        return float(timestamp())
    seconds = getattr(expire_time, "seconds", None)
    if isinstance(seconds, (int, float)):
        if seconds > 10_000_000_000:
            return float(seconds / 1000)
        if seconds > 1_000_000_000:
            return float(seconds)
    if isinstance(expire_time, str):
        try:
            return datetime.fromisoformat(expire_time.replace("Z", "+00:00")).timestamp()
        except ValueError:
            pass
    return time.time() + 50 * 60


def connect() -> LakebaseConnection:
    return LakebaseConnection()


def row_to_dict(row) -> dict:
    return {CAMEL_CASE_KEYS.get(key, key): value for key, value in dict(row).items()}


def dict_rows(rows: list) -> list[dict]:
    return [row_to_dict(row) for row in rows]


REQUIRED_TABLES = [
    "md_domains",
    "md_business_units",
    "md_product_types",
    "md_expected_outputs",
    "md_platforms",
    "md_priorities",
    "md_stages",
    "md_statuses",
    "md_subdomains",
    "md_users",
    "md_source_systems",
    "md_scope_options",
    "md_build_statuses",
    "md_stage_requirements",
    "governance_requests",
    "data_products",
    "product_stage_answers",
    "governance_timeline",
]


def validate_database_ready() -> None:
    with connect() as db:
        missing_tables = [table for table in REQUIRED_TABLES if not table_exists(db, table)]
        if missing_tables:
            raise RuntimeError(f"Database migration is missing required tables: {', '.join(missing_tables)}")
        counts = master_data_counts(db)
        missing_master_data = [
            key
            for key in (
                "domains",
                "businessUnits",
                "productTypes",
                "expectedOutputs",
                "platforms",
                "priorities",
                "stages",
                "statuses",
                "subdomains",
                "users",
                "sourceSystems",
                "scopeOptions",
                "buildStatuses",
                "stageRequirements",
            )
            if counts.get(key, 0) == 0
        ]
        if missing_master_data:
            raise RuntimeError(f"Database migration is missing master data: {', '.join(missing_master_data)}")


def table_exists(db: LakebaseConnection, table: str) -> bool:
    row = db.execute(
        """
        SELECT EXISTS (
          SELECT 1
          FROM information_schema.tables
          WHERE table_schema = current_schema()
            AND table_name = ?
        ) AS exists
        """,
        (table,),
    ).fetchone()
    return bool(row and row["exists"])


def normalize_request_number(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    numeric_match = re.fullmatch(r"\d+", text)
    if numeric_match:
        return text.zfill(8)
    prefixed_match = re.fullmatch(r"REQ-(\d+)", text, flags=re.IGNORECASE)
    if prefixed_match:
        return prefixed_match.group(1).zfill(8)
    return text


def request_number_sort_value(value: object) -> int:
    text = str(value or "").strip()
    numeric_match = re.fullmatch(r"\d+", text)
    if numeric_match:
        return int(text)
    prefixed_match = re.fullmatch(r"REQ-(\d+)", text, flags=re.IGNORECASE)
    if prefixed_match:
        return int(prefixed_match.group(1))
    trailing_match = re.search(r"(\d+)$", text)
    if trailing_match:
        return int(trailing_match.group(1))
    return 0


def next_request_number(db: LakebaseConnection) -> str:
    rows = db.execute("SELECT request_number FROM governance_requests").fetchall()
    max_number = 0
    for row in rows:
        max_number = max(max_number, request_number_sort_value(row["request_number"]))
    return f"{max_number + 1:08d}"


def next_product_number(db: LakebaseConnection) -> str:
    rows = db.execute("SELECT data_product_number FROM data_products").fetchall()
    max_number = 0
    for row in rows:
        max_number = max(max_number, request_number_sort_value(row["data_product_number"]))
    return f"{max_number + 1:08d}"


def validate_payload(payload: dict) -> str | None:
    if not payload.get("initiative", "").strip():
        return "initiative is required"
    email = payload.get("requesterEmail", "").strip().lower()
    if not re.match(r"^[^@\s]+@syngenta\.com$", email):
        return "requester email must use syngenta.com"
    return None


def resolve_domain_id(db: LakebaseConnection, domain_id: str | None) -> str:
    clean_domain_id = slug_id(domain_id or "commercial")
    exists = db.execute("SELECT 1 FROM md_domains WHERE domain_id = ?", (clean_domain_id,)).fetchone()
    if not exists:
        raise ValueError("domain is not valid")
    return clean_domain_id


def insert_request(db: LakebaseConnection, payload: dict, timestamp: str | None = None) -> dict:
    timestamp = timestamp or now()
    request_id = str(uuid.uuid4())
    request_number = normalize_request_number(payload.get("request_number")) or next_request_number(db)
    status_id = ensure_reference(db, "md_statuses", "status_id", payload.get("status", "new"), "status")
    requester_email = clean_email(payload.get("requesterEmail"), "requester email")
    priority_id = ensure_reference(db, "md_priorities", "priority_id", payload.get("priority") or "p2", "priority")
    business_unit_id = ensure_reference(db, "md_business_units", "business_unit_id", payload.get("businessUnit", "cp"), "business unit", required=False)
    scope_id = ensure_reference(db, "md_scope_options", "scope_id", payload.get("scope") or "global", "scope", required=False)
    expected_output_id = ensure_reference(db, "md_expected_outputs", "expected_output_id", payload.get("expectedOutput") or "table_dataset", "expected output", required=False) or None
    platform_id = ensure_reference(db, "md_platforms", "platform_id", payload.get("platform") or "databricks", "target platform")
    db.execute(
        """
        INSERT INTO governance_requests (
          request_id, request_number, initiative, business_decision, business_value,
          expected_output_id, target_platform_id, priority_id, business_unit_id, scope_id, requester_name, requester_email,
          expected_date, additional_comments, status_id, note, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request_id,
            request_number,
            clean_text(payload.get("initiative"), "initiative", required=True),
            clean_text(payload.get("description"), "business decision", max_length=MAX_TEXTAREA_LENGTH),
            clean_text(payload.get("businessValue"), "business value", max_length=MAX_TEXTAREA_LENGTH),
            expected_output_id,
            platform_id,
            priority_id,
            business_unit_id,
            scope_id,
            clean_text(payload.get("requester"), "requester", required=True),
            requester_email,
            clean_date(payload.get("expectedDate"), "expected date", required=True),
            clean_text(payload.get("additionalComments"), "additional comments", max_length=MAX_TEXTAREA_LENGTH),
            status_id,
            clean_text(payload.get("note", "New initiative submitted for triage"), "note", max_length=MAX_TEXTAREA_LENGTH),
            timestamp,
            timestamp,
        ),
    )
    add_timeline(db, "request", request_id, None, "created", "Initiative created", "New initiative submitted.", status_id=status_id, created_by=requester_email, created_at=timestamp)
    return get_initiative_by_id(db, request_id)


def insert_product(db: LakebaseConnection, request_id: str, payload: dict, actor: str, timestamp: str | None = None) -> dict:
    timestamp = timestamp or now()
    parent = db.execute("SELECT 1 FROM governance_requests WHERE request_id = ?", (request_id,)).fetchone()
    if not parent:
        raise ValueError("initiative not found")
    product_id = str(uuid.uuid4())
    product_number = normalize_request_number(payload.get("productNumber")) or next_product_number(db)
    stage_id = ensure_reference(db, "md_stages", "stage_id", payload.get("stage", "intake"), "stage")
    status_id = ensure_reference(db, "md_statuses", "status_id", payload.get("status", "in_review"), "status")
    domain_id = resolve_domain_id(db, payload.get("domain"))
    db.execute(
        """
        INSERT INTO data_products (
          data_product_id, request_id, data_product_number, title, description,
          expected_output_id, product_type_id, target_platform_id, data_product_owner,
          lead_domain_id, current_stage_id, status_id, note, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product_id,
            request_id,
            product_number,
            clean_text(payload.get("title"), "product title", required=True),
            clean_text(payload.get("description"), "product description", max_length=MAX_TEXTAREA_LENGTH),
            ensure_reference(db, "md_expected_outputs", "expected_output_id", payload.get("expectedOutput") or "table_dataset", "expected output", required=False) or None,
            ensure_reference(db, "md_product_types", "product_type_id", payload.get("productType") or "structured", "product type"),
            ensure_reference(db, "md_platforms", "platform_id", payload.get("platform") or "databricks", "target platform"),
            clean_text(payload.get("dataProductOwner"), "Data Product Owner") or None,
            domain_id,
            stage_id,
            status_id,
            clean_text(payload.get("note", "Product created for governance"), "note", max_length=MAX_TEXTAREA_LENGTH),
            timestamp,
            timestamp,
        ),
    )
    add_timeline(db, "product", request_id, product_id, "created", "Product created", "Data product added to initiative.", stage_id=stage_id, status_id=status_id, created_by=actor, created_at=timestamp)
    return get_request_by_id(db, product_id)


def get_requests(db: LakebaseConnection) -> list[dict]:
    rows = db.execute(request_overview_select_sql() + " ORDER BY p.created_at DESC").fetchall()
    return [serialize_request(row) for row in rows]


def get_initiatives(db: LakebaseConnection) -> list[dict]:
    rows = db.execute(
        """
        SELECT
          r.*,
          bu.business_unit_name,
          pr.priority_name,
          scope.scope_name,
          st.status_name,
          eo.expected_output_name,
          pl.platform_name,
          COUNT(p.data_product_id) AS product_count,
          CONCAT_WS(
            ' ',
            r.request_id, r.request_number, r.initiative, r.business_decision,
            r.business_value, r.requester_name, r.requester_email,
            r.expected_date, r.additional_comments, r.note,
            bu.business_unit_name, pr.priority_name, scope.scope_name, st.status_name,
            eo.expected_output_name, pl.platform_name,
            STRING_AGG(COALESCE(p.title, ''), ' ')
          ) AS search_text
        FROM governance_requests r
        LEFT JOIN data_products p ON p.request_id = r.request_id
        LEFT JOIN md_business_units bu ON bu.business_unit_id = r.business_unit_id
        LEFT JOIN md_priorities pr ON pr.priority_id = r.priority_id
        LEFT JOIN md_scope_options scope ON scope.scope_id = r.scope_id
        LEFT JOIN md_statuses st ON st.status_id = r.status_id
        LEFT JOIN md_expected_outputs eo ON eo.expected_output_id = r.expected_output_id
        LEFT JOIN md_platforms pl ON pl.platform_id = r.target_platform_id
        GROUP BY r.request_id, bu.business_unit_name, pr.priority_name, scope.scope_name, st.status_name, eo.expected_output_name, pl.platform_name
        ORDER BY r.created_at DESC
        """
    ).fetchall()
    return [serialize_initiative(row) for row in rows]


def get_initiative_by_id(db: LakebaseConnection, request_id: str) -> dict:
    row = db.execute(
        """
        SELECT
          r.*,
          bu.business_unit_name,
          pr.priority_name,
          scope.scope_name,
          st.status_name,
          eo.expected_output_name,
          pl.platform_name,
          COUNT(p.data_product_id) AS product_count,
          CONCAT_WS(' ', r.request_id, r.request_number, r.initiative, r.business_decision, r.business_value, r.requester_name, r.requester_email, r.note) AS search_text
        FROM governance_requests r
        LEFT JOIN data_products p ON p.request_id = r.request_id
        LEFT JOIN md_business_units bu ON bu.business_unit_id = r.business_unit_id
        LEFT JOIN md_priorities pr ON pr.priority_id = r.priority_id
        LEFT JOIN md_scope_options scope ON scope.scope_id = r.scope_id
        LEFT JOIN md_statuses st ON st.status_id = r.status_id
        LEFT JOIN md_expected_outputs eo ON eo.expected_output_id = r.expected_output_id
        LEFT JOIN md_platforms pl ON pl.platform_id = r.target_platform_id
        WHERE r.request_id = ?
        GROUP BY r.request_id, bu.business_unit_name, pr.priority_name, scope.scope_name, st.status_name, eo.expected_output_name, pl.platform_name
        """,
        (request_id,),
    ).fetchone()
    if not row:
        raise ValueError("initiative not found")
    initiative = serialize_initiative(row)
    initiative["products"] = get_products_for_request(db, request_id)
    return initiative


def get_products_for_request(db: LakebaseConnection, request_id: str) -> list[dict]:
    rows = db.execute(request_overview_select_sql() + " WHERE p.request_id = ? ORDER BY p.created_at DESC", (request_id,)).fetchall()
    return [serialize_request(row) for row in rows]


def get_dashboard(db: LakebaseConnection) -> dict:
    totals = db.execute(
        """
        SELECT
          COUNT(*) AS total,
          SUM(CASE WHEN status_id IN ('in_review', 'in_progress') THEN 1 ELSE 0 END) AS in_review,
          SUM(CASE WHEN status_id = 'blocked' THEN 1 ELSE 0 END) AS blocked,
          SUM(CASE WHEN current_stage_id IN ('publish', 'operate') THEN 1 ELSE 0 END) AS live
        FROM data_products
        """
    ).fetchone()
    initiative_count = db.execute("SELECT COUNT(*) AS count FROM governance_requests").fetchone()
    stage_rows = dict_rows(
        db.execute(
            """
            SELECT current_stage_id AS stageId, COUNT(*) AS count
            FROM data_products
            GROUP BY current_stage_id
            """
        ).fetchall()
    )
    status_rows = dict_rows(
        db.execute(
            """
            SELECT status_id AS statusId, COUNT(*) AS count
            FROM data_products
            GROUP BY status_id
            """
        ).fetchall()
    )
    return {
        "total": int(totals["total"] or 0),
        "initiatives": int(initiative_count["count"] or 0),
        "inReview": int(totals["in_review"] or 0),
        "blocked": int(totals["blocked"] or 0),
        "live": int(totals["live"] or 0),
        "stageCounts": {row["stageId"]: int(row["count"] or 0) for row in stage_rows},
        "statusCounts": {row["statusId"]: int(row["count"] or 0) for row in status_rows},
    }


def get_session(db: LakebaseConnection, email: str) -> dict:
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
    can_admin = clean_email in CONFIGURED_ADMIN_EMAILS or bool(user and user["role_key"] in ADMIN_ROLE_KEYS)
    can_delete_master_data = clean_email in CONFIGURED_ADMIN_EMAILS or bool(user and user["role_key"] == "admin")
    return {
        "email": clean_email,
        "role": "admin" if can_admin else "requester",
        "canAdmin": can_admin,
        "canDeleteMasterData": can_delete_master_data,
        "name": user["display_name"] if user else clean_email.split("@")[0],
    }


def log_exception(context: str, exc: Exception) -> None:
    print(f"[ERROR] {context}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)


def startup_error_payload() -> dict:
    return {
        "error": STARTUP_ERROR or "Backend is not ready",
        "database": database_label(),
    }


def database_label() -> str:
    return f"{os.getenv('PGDATABASE', 'unknown')}/{LAKEBASE_SCHEMA}"


def resolve_user_email(headers) -> tuple[str, str]:
    for source in TRUSTED_IDENTITY_HEADERS:
        value = headers.get(source)
        clean_value = str(value or "").strip().lower()
        if clean_value and re.match(r"^[^@\s]+@syngenta\.com$", clean_value):
            return clean_value, source
    raise PermissionError("No valid syngenta.com user email was provided by Databricks.")


def request_user_email(headers) -> str:
    return resolve_user_email(headers)[0]


def require_admin(db: LakebaseConnection, email: str | None) -> None:
    if not get_session(db, email or "")["canAdmin"]:
        raise PermissionError("Admin access is required")


def get_master_data(db: LakebaseConnection) -> dict:
    users = dict_rows(db.execute("SELECT user_id AS id, display_name AS name, email, role_key FROM md_users ORDER BY display_name").fetchall())
    return {
        "domains": dict_rows(db.execute("SELECT domain_id AS id, domain_name AS name FROM md_domains ORDER BY domain_name").fetchall()),
        "businessUnits": dict_rows(db.execute("SELECT business_unit_id AS id, business_unit_name AS name FROM md_business_units ORDER BY business_unit_name").fetchall()),
        "productTypes": dict_rows(db.execute("SELECT product_type_id AS id, product_type_name AS name FROM md_product_types ORDER BY product_type_name").fetchall()),
        "expectedOutputs": dict_rows(db.execute("SELECT expected_output_id AS id, expected_output_name AS name FROM md_expected_outputs ORDER BY expected_output_name").fetchall()),
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
        "hubOwners": [user for user in users if user["role_key"] == "hub_owner"],
        "lynxPms": [user for user in users if user["role_key"] == "lynx_pm"],
        "users": users,
    }


def get_cached_master_data(db: LakebaseConnection) -> dict:
    now_monotonic = time.monotonic()
    if MASTER_DATA_CACHE["data"] is not None and MASTER_DATA_CACHE["expires_at"] > now_monotonic:
        return MASTER_DATA_CACHE["data"]
    data = get_master_data(db)
    MASTER_DATA_CACHE["data"] = data
    MASTER_DATA_CACHE["expires_at"] = now_monotonic + MASTER_DATA_CACHE_SECONDS
    return data


def clear_master_data_cache() -> None:
    MASTER_DATA_CACHE["data"] = None
    MASTER_DATA_CACHE["expires_at"] = 0.0


def master_data_counts(db: LakebaseConnection) -> dict:
    tables = {
        "domains": "md_domains",
        "businessUnits": "md_business_units",
        "productTypes": "md_product_types",
        "expectedOutputs": "md_expected_outputs",
        "platforms": "md_platforms",
        "priorities": "md_priorities",
        "stages": "md_stages",
        "statuses": "md_statuses",
        "subdomains": "md_subdomains",
        "users": "md_users",
        "sourceSystems": "md_source_systems",
        "scopeOptions": "md_scope_options",
        "buildStatuses": "md_build_statuses",
        "stageRequirements": "md_stage_requirements",
        "requests": "governance_requests",
    }
    counts = {}
    for key, table in tables.items():
        row = db.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
        counts[key] = int(row["count"] or 0)
    return counts


def upsert_master_data_item(db: LakebaseConnection, collection: str, payload: dict) -> dict:
    config = MASTER_DATA_CONFIG.get(collection)
    if not config:
        raise ValueError("Unsupported master data collection")
    if collection == "users":
        item_id = slug_id(payload.get("email") or "")
    else:
        item_id = slug_id(payload.get("id") or payload.get("name") or "")
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
            allowed_roles = {"requester", "admin", "data_domain_owner", "domain_delivery_lead", "hub_owner", "lynx_pm"}
            if value not in allowed_roles:
                raise ValueError("roleKey is not valid")
        elif payload_key == "type":
            value = value or "Region"
            if value not in {"Global", "Region"}:
                raise ValueError("type is not valid")
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


def delete_master_data_item(db: LakebaseConnection, collection: str, item_id: str) -> dict:
    config = MASTER_DATA_CONFIG.get(collection)
    if not config:
        raise ValueError("Unsupported master data collection")
    protected = {
        "businessUnits": {"cp", "seeds", "vegetables"},
        "domains": {"commercial"},
    }
    if item_id in protected.get(collection, set()):
        raise ValueError("This master data item is protected")
    db.execute(f"DELETE FROM {config['table']} WHERE {config['id']} = ?", (item_id,))
    return {"deleted": item_id}


def slug_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def clean_text(value: object, label: str, *, required: bool = False, max_length: int = MAX_TEXT_LENGTH) -> str:
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{label} is required")
    if len(text) > max_length:
        raise ValueError(f"{label} must be {max_length} characters or fewer")
    return text


def clean_email(value: object, label: str = "email", *, required: bool = True) -> str:
    email = str(value or "").strip().lower()
    if required and not email:
        raise ValueError(f"{label} is required")
    if email and not re.match(r"^[^@\s]+@syngenta\.com$", email):
        raise ValueError(f"{label} must use syngenta.com")
    return email


def clean_date(value: object, label: str, *, required: bool = False) -> str:
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{label} is required")
    if not text:
        return ""
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{label} must use YYYY-MM-DD format") from exc
    return text


def clean_non_negative_int(value: object, label: str, *, required: bool = False) -> int | None:
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{label} is required")
    if not text:
        return None
    if not re.match(r"^\d+$", text):
        raise ValueError(f"{label} must be a whole number")
    return int(text)


def clean_http_url(value: object, label: str, *, required: bool = False) -> str:
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{label} is required")
    if not text:
        return ""
    if len(text) > MAX_URL_LENGTH:
        raise ValueError(f"{label} must be {MAX_URL_LENGTH} characters or fewer")
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{label} must be a valid http(s) URL")
    return text


def ensure_reference(
    db: LakebaseConnection,
    table: str,
    id_column: str,
    value: object,
    label: str,
    *,
    required: bool = True,
    extra_where: str = "",
    extra_params: tuple = (),
) -> str:
    clean_value = slug_id(str(value or ""))
    if required and not clean_value:
        raise ValueError(f"{label} is required")
    if not clean_value:
        return ""
    query = f"SELECT 1 FROM {table} WHERE {id_column} = ? {extra_where}"
    exists = db.execute(query, (clean_value, *extra_params)).fetchone()
    if not exists:
        raise ValueError(f"{label} is not valid")
    return clean_value


def ensure_user_role_reference(
    db: LakebaseConnection,
    value: object,
    label: str,
    role_key: str,
    *,
    required: bool = True,
) -> str:
    return ensure_reference(
        db,
        "md_users",
        "user_id",
        value,
        label,
        required=required,
        extra_where="AND role_key = ?",
        extra_params=(role_key,),
    )


def validate_requirement_answer(db: LakebaseConnection, requirement: dict, value: object) -> str:
    key = requirement["requirement_key"]
    input_type = requirement["input_type"]
    master_type = requirement["master_data_type"]
    if key == "domain_delivery_lead_user_id":
        master_type = "hubOwners"

    if input_type == "checkbox":
        return "true" if value is True or str(value).strip().lower() == "true" else "false"
    if input_type == "number":
        number = clean_non_negative_int(value, requirement["label"])
        return "" if number is None else str(number)
    if input_type == "date":
        return clean_date(value, requirement["label"])
    if key in {"jira_link", "alation_link"}:
        return clean_http_url(value, requirement["label"])

    text_value = str(value or "").strip()
    if not text_value:
        return ""

    if master_type == "domains":
        return ensure_reference(db, "md_domains", "domain_id", text_value, requirement["label"])
    if master_type == "productTypes":
        return ensure_reference(db, "md_product_types", "product_type_id", text_value, requirement["label"])
    if master_type == "expectedOutputs":
        return ensure_reference(db, "md_expected_outputs", "expected_output_id", text_value, requirement["label"])
    if master_type == "platforms":
        return ensure_reference(db, "md_platforms", "platform_id", text_value, requirement["label"])
    if master_type == "priorities":
        return ensure_reference(db, "md_priorities", "priority_id", text_value, requirement["label"])
    if master_type == "scopeOptions":
        return ensure_reference(db, "md_scope_options", "scope_id", text_value, requirement["label"])
    if master_type == "subdomains":
        return ensure_reference(db, "md_subdomains", "subdomain_id", text_value, requirement["label"])
    if master_type == "sourceSystems":
        return ensure_reference(db, "md_source_systems", "source_system_id", text_value, requirement["label"])
    if master_type == "buildStatuses":
        return ensure_reference(db, "md_build_statuses", "build_status_id", text_value, requirement["label"])
    if master_type == "dataDomainOwners":
        return ensure_user_role_reference(db, text_value, requirement["label"], "data_domain_owner")
    if master_type == "domainDeliveryLeads":
        return ensure_user_role_reference(db, text_value, requirement["label"], "domain_delivery_lead")
    if master_type == "hubOwners":
        label = "Hub Owner" if key == "domain_delivery_lead_user_id" else requirement["label"]
        return ensure_user_role_reference(db, text_value, label, "hub_owner")
    if master_type == "lynxPms":
        return ensure_user_role_reference(db, text_value, requirement["label"], "lynx_pm")
    if input_type == "textarea":
        return clean_text(text_value, requirement["label"], max_length=MAX_TEXTAREA_LENGTH)
    return clean_text(text_value, requirement["label"])


def request_select_sql() -> str:
    return """
        SELECT
          p.*,
          r.request_number,
          r.initiative,
          r.business_decision,
          r.business_value,
          r.business_unit_id,
          r.scope_id,
          r.requester_name,
          r.requester_email,
          r.expected_date,
          r.additional_comments,
          r.priority_id,
          r.request_id AS initiative_request_id,
          COALESCE(d.domain_name, NULLIF(p.lead_domain_id, ''), 'Unassigned') AS domain_name,
          bu.business_unit_name,
          COALESCE(pt.product_type_name, NULLIF(p.product_type_id, ''), 'Unassigned') AS product_type_name,
          eo.expected_output_name,
          COALESCE(pl.platform_name, NULLIF(p.target_platform_id, ''), 'Unassigned') AS platform_name,
          COALESCE(pr.priority_name, NULLIF(r.priority_id, ''), 'Unassigned') AS priority_name,
          COALESCE(s.stage_name, NULLIF(p.current_stage_id, ''), 'Unassigned') AS stage_name,
          s.stage_number,
          COALESCE(st.status_name, NULLIF(p.status_id, ''), 'Unassigned') AS status_name,
          scope.scope_name,
          sub.subdomain_name,
          sub.domain_id AS subdomain_domain_id,
          ddo.display_name AS data_domain_owner_name,
          ddo.email AS data_domain_owner_email,
          src.source_system_name,
          dle.display_name AS delivery_lead_name,
          ddl.display_name AS domain_delivery_lead_name,
          lpm.display_name AS lynx_pm_name,
          bs.build_status_name,
          CONCAT_WS(
            ' ',
            r.request_number,
            r.request_id,
            r.initiative,
            r.business_decision,
            r.business_value,
            r.expected_date,
            r.additional_comments,
            r.requester_name,
            r.requester_email,
            p.data_product_id,
            p.data_product_number,
            p.title,
            p.description,
            p.data_product_owner,
            p.delivery_date,
            CAST(p.effort AS TEXT),
            p.jira_epic_id,
            p.jira_link,
            p.alation_link,
            r.status_change_reason,
            r.last_status_change_date,
            r.last_status_changed_by,
            p.status_change_reason,
            p.last_status_change_date,
            p.last_status_changed_by,
            p.note,
            p.product_type_id,
            p.target_platform_id,
            r.priority_id,
            p.lead_domain_id,
            r.business_unit_id,
            r.scope_id,
            p.delivery_lead,
            p.current_stage_id,
            p.status_id,
            p.lead_subdomain_id,
            p.data_domain_owner_user_id,
            p.source_system_id,
            p.domain_delivery_lead_user_id,
            p.lynx_pm_user_id,
            p.build_status_id,
            d.domain_name,
            bu.business_unit_name,
            pt.product_type_name,
            eo.expected_output_name,
            pl.platform_name,
            pr.priority_name,
            s.stage_name,
            st.status_name,
            scope.scope_name,
            sub.subdomain_name,
            ddo.display_name,
            ddo.email,
            src.source_system_name,
            dle.display_name,
            dle.email,
            ddl.display_name,
            ddl.email,
            lpm.display_name,
            lpm.email,
            bs.build_status_name,
            (
              SELECT STRING_AGG(CONCAT_WS(' ', req.label, req.requirement_key, ans.answer_value), ' ')
              FROM product_stage_answers ans
              LEFT JOIN md_stage_requirements req ON req.requirement_id = ans.requirement_id
              WHERE ans.data_product_id = p.data_product_id
            ),
            (
              SELECT STRING_AGG(
                CONCAT_WS(
                  ' ',
                  t.event_type,
                  t.event_label,
                  t.event_detail,
                  t.created_by,
                  t.stage_id,
                  t.from_stage_id,
                  t.to_stage_id,
                  t.status_id
                ),
                ' '
              )
              FROM governance_timeline t
              WHERE t.data_product_id = p.data_product_id
            )
          ) AS search_text,
          COALESCE(
            (
              SELECT MAX(t.created_at)
              FROM governance_timeline t
              WHERE t.data_product_id = p.data_product_id
                AND t.event_type = 'stage_advanced'
                AND t.to_stage_id = p.current_stage_id
            ),
            p.created_at
          ) AS current_stage_entered_at
        FROM data_products p
        JOIN governance_requests r ON r.request_id = p.request_id
        LEFT JOIN md_domains d ON d.domain_id = p.lead_domain_id
        LEFT JOIN md_business_units bu ON bu.business_unit_id = r.business_unit_id
        LEFT JOIN md_product_types pt ON pt.product_type_id = p.product_type_id
        LEFT JOIN md_expected_outputs eo ON eo.expected_output_id = p.expected_output_id
        LEFT JOIN md_platforms pl ON pl.platform_id = p.target_platform_id
        LEFT JOIN md_priorities pr ON pr.priority_id = r.priority_id
        LEFT JOIN md_stages s ON s.stage_id = p.current_stage_id
        LEFT JOIN md_statuses st ON st.status_id = p.status_id
        LEFT JOIN md_scope_options scope ON scope.scope_id = r.scope_id
        LEFT JOIN md_subdomains sub ON sub.subdomain_id = p.lead_subdomain_id
        LEFT JOIN md_users ddo ON ddo.user_id = p.data_domain_owner_user_id
        LEFT JOIN md_source_systems src ON src.source_system_id = p.source_system_id
        LEFT JOIN md_users dle ON dle.user_id = p.delivery_lead
        LEFT JOIN md_users ddl ON ddl.user_id = p.domain_delivery_lead_user_id
        LEFT JOIN md_users lpm ON lpm.user_id = p.lynx_pm_user_id
        LEFT JOIN md_build_statuses bs ON bs.build_status_id = p.build_status_id
    """


def request_overview_select_sql() -> str:
    return request_select_sql()


def get_request_by_id(db: LakebaseConnection, request_id: str) -> dict:
    row = db.execute(request_select_sql() + " WHERE p.data_product_id = ?", (request_id,)).fetchone()
    if not row:
        raise ValueError("request not found")
    return serialize_request(row)


def get_workflow(db: LakebaseConnection, request_id: str) -> dict:
    request = get_request_by_id(db, request_id)
    stages = db.execute("SELECT stage_id, stage_name, stage_number FROM md_stages ORDER BY stage_number").fetchall()
    workflow_stages = []
    previous_complete = True
    for stage in stages:
        requirements = get_stage_requirements(db, request_id, stage["stage_id"])
        complete = all(not item["is_required"] or is_answer_complete(item) for item in requirements)
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
            FROM governance_timeline t
            LEFT JOIN md_stages s ON s.stage_id = t.stage_id
            LEFT JOIN md_statuses st ON st.status_id = t.status_id
            WHERE t.data_product_id = ?
            ORDER BY t.created_at DESC
            """,
            (request_id,),
        ).fetchall()
    )
    return {"request": request, "stages": workflow_stages, "timeline": timeline}


def get_stage_requirements(db: LakebaseConnection, request_id: str, stage_id: str) -> list[dict]:
    effort_expr = "COALESCE(CAST(r.effort AS TEXT), '')"
    rows = db.execute(
        f"""
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
            WHEN 'product_type_id' THEN r.product_type_id
            WHEN 'data_product_owner' THEN COALESCE(r.data_product_owner, '')
            WHEN 'expected_output_id' THEN COALESCE(r.expected_output_id, '')
            WHEN 'target_platform_id' THEN r.target_platform_id
            WHEN 'priority_id' THEN parent.priority_id
            WHEN 'scope_id' THEN COALESCE(parent.scope_id, '')
            WHEN 'business_decision' THEN COALESCE(parent.business_decision, '')
            WHEN 'business_value' THEN COALESCE(parent.business_value, '')
            WHEN 'lead_domain_id' THEN r.lead_domain_id
            WHEN 'lead_subdomain_id' THEN COALESCE(r.lead_subdomain_id, '')
            WHEN 'delivery_date' THEN COALESCE(r.delivery_date, '')
            WHEN 'delivery_lead' THEN COALESCE(r.delivery_lead, '')
            WHEN 'domain_delivery_lead_user_id' THEN COALESCE(r.domain_delivery_lead_user_id, '')
            WHEN 'effort' THEN {effort_expr}
            WHEN 'jira_epic_id' THEN COALESCE(r.jira_epic_id, '')
            WHEN 'jira_link' THEN COALESCE(r.jira_link, '')
            WHEN 'alation_link' THEN COALESCE(r.alation_link, '')
            WHEN 'expected_date' THEN COALESCE(parent.expected_date, '')
            WHEN 'additional_comments' THEN COALESCE(parent.additional_comments, '')
            ELSE COALESCE(ans.answer_value, '')
          END AS answer_value
        FROM md_stage_requirements req
        JOIN data_products r
          ON r.data_product_id = ?
        JOIN governance_requests parent
          ON parent.request_id = r.request_id
        LEFT JOIN product_stage_answers ans
          ON ans.requirement_id = req.requirement_id
         AND ans.data_product_id = ?
        WHERE req.stage_id = ?
        ORDER BY req.sort_order
        """,
        (request_id, request_id, stage_id),
    ).fetchall()
    return dict_rows(rows)


def is_answer_complete(item: dict) -> bool:
    value = str(item["answer_value"] or "").strip()
    if item["input_type"] == "checkbox":
        return value == "true"
    return bool(value)


def save_workflow_answers(db: LakebaseConnection, request_id: str, payload: dict) -> dict:
    timestamp = now()
    stage_id = payload.get("stageId")
    actor = clean_email(payload.get("updatedBy"), "updated by", required=False) or "system"
    if not stage_id:
        raise ValueError("stageId is required")

    workflow = get_workflow(db, request_id)
    stage = next((item for item in workflow["stages"] if item["stageId"] == stage_id), None)
    if not stage:
        raise ValueError("stage not found")
    if not stage["canSubmit"]:
        raise PermissionError("Previous stages must be completed before this stage can be submitted")

    requirement_by_id = {item["requirement_id"]: item for item in stage["requirements"]}
    previous_answers = {
        item["requirement_id"]: str(item.get("answer_value") or "").strip()
        for item in stage["requirements"]
    }
    answers = payload.get("answers", {})
    changes: list[dict] = []
    for requirement_id, answer_value in answers.items():
        requirement = requirement_by_id.get(requirement_id)
        if not requirement:
            continue
        clean_value = validate_requirement_answer(db, requirement, answer_value)
        old_value = previous_answers.get(requirement_id, "")
        upsert_stage_answer(db, request_id, requirement_id, clean_value, timestamp)
        update_structured_field(db, request_id, requirement["requirement_key"], clean_value)
        if normalize_log_value(old_value) != normalize_log_value(clean_value):
            changes.append(
                {
                    "label": "Hub Owner" if requirement["requirement_key"] == "domain_delivery_lead_user_id" else requirement["label"],
                    "input_type": requirement["input_type"],
                    "master_data_type": "hubOwners" if requirement["requirement_key"] == "domain_delivery_lead_user_id" else requirement["master_data_type"],
                    "old": old_value,
                    "new": clean_value,
                }
            )

    reconcile_domain_subdomain(db, request_id)

    status_id = payload.get("statusId")
    if status_id:
        status_id = ensure_reference(db, "md_statuses", "status_id", status_id, "status")
        current_status = workflow["request"].get("statusId")
        db.execute("UPDATE data_products SET status_id = ? WHERE data_product_id = ?", (status_id, request_id))
        if status_id != current_status:
            add_timeline(
                db,
                "product",
                workflow["request"].get("initiativeRequestId"),
                request_id,
                "status_changed",
                "Status updated",
                f"Status changed from {format_status_for_log(db, current_status)} to {format_status_for_log(db, status_id)}.",
                stage_id=stage_id,
                status_id=status_id,
                created_by=actor,
                created_at=timestamp,
            )

    event_detail = describe_workflow_changes(db, changes)
    add_timeline(db, "product", workflow["request"].get("initiativeRequestId"), request_id, "answers_saved", f"{stage['name']} saved", event_detail, stage_id=stage_id, status_id=status_id, created_by=actor, created_at=timestamp)
    advanced = advance_if_complete(db, request_id, stage_id, timestamp)
    db.execute("UPDATE data_products SET updated_at = ? WHERE data_product_id = ?", (timestamp, request_id))
    result = get_workflow(db, request_id)
    result["advanced"] = advanced
    return result


def upsert_stage_answer(db: LakebaseConnection, request_id: str, requirement_id: str, value: str, timestamp: str) -> None:
    db.execute(
        """
        INSERT INTO product_stage_answers (answer_id, data_product_id, requirement_id, answer_value, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(data_product_id, requirement_id)
        DO UPDATE SET answer_value = excluded.answer_value, updated_at = excluded.updated_at
        """,
        (str(uuid.uuid4()), request_id, requirement_id, value, timestamp),
    )


def normalize_log_value(value: object) -> str:
    return str(value or "").strip()


def describe_workflow_changes(db: LakebaseConnection, changes: list[dict]) -> str:
    if not changes:
        return "Submitted with no field changes."
    parts = []
    for change in changes[:6]:
        old_value = format_answer_for_log(db, change, change["old"])
        new_value = format_answer_for_log(db, change, change["new"])
        parts.append(f"{change['label']}: {old_value} -> {new_value}")
    if len(changes) > 6:
        parts.append(f"{len(changes) - 6} more field(s) changed")
    return "; ".join(parts)


def format_answer_for_log(db: LakebaseConnection, requirement: dict, value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "empty"
    if requirement.get("input_type") == "checkbox":
        return "checked" if text == "true" else "unchecked"

    master_type = requirement.get("master_data_type")
    lookup = {
        "domains": ("md_domains", "domain_id", "domain_name"),
        "productTypes": ("md_product_types", "product_type_id", "product_type_name"),
        "expectedOutputs": ("md_expected_outputs", "expected_output_id", "expected_output_name"),
        "platforms": ("md_platforms", "platform_id", "platform_name"),
        "priorities": ("md_priorities", "priority_id", "priority_name"),
        "scopeOptions": ("md_scope_options", "scope_id", "scope_name"),
        "subdomains": ("md_subdomains", "subdomain_id", "subdomain_name"),
        "sourceSystems": ("md_source_systems", "source_system_id", "source_system_name"),
        "buildStatuses": ("md_build_statuses", "build_status_id", "build_status_name"),
        "dataDomainOwners": ("md_users", "user_id", "display_name"),
        "domainDeliveryLeads": ("md_users", "user_id", "display_name"),
        "hubOwners": ("md_users", "user_id", "display_name"),
        "lynxPms": ("md_users", "user_id", "display_name"),
    }.get(master_type)
    if lookup:
        table, id_column, name_column = lookup
        row = db.execute(f"SELECT {name_column} AS name FROM {table} WHERE {id_column} = ?", (text,)).fetchone()
        if row and row["name"]:
            text = row["name"]

    return truncate_for_log(text)


def format_status_for_log(db: LakebaseConnection, status_id: object) -> str:
    text = str(status_id or "").strip()
    if not text:
        return "empty"
    row = db.execute("SELECT status_name FROM md_statuses WHERE status_id = ?", (text,)).fetchone()
    return row["status_name"] if row and row["status_name"] else truncate_for_log(text)


def truncate_for_log(value: str, limit: int = 90) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def save_request_status(db: LakebaseConnection, request_id: str, payload: dict) -> dict:
    timestamp = now()
    status_id = payload.get("statusId")
    reason = str(payload.get("statusChangeReason") or "").strip()
    changed_by = clean_email(payload.get("updatedBy"), "updated by", required=False) or "system"
    if not status_id:
        raise ValueError("statusId is required")
    status_id = ensure_reference(db, "md_statuses", "status_id", status_id, "status")
    current = db.execute("SELECT request_id, current_stage_id FROM data_products WHERE data_product_id = ?", (request_id,)).fetchone()
    if not current:
        raise ValueError("request not found")
    db.execute(
        """
        UPDATE data_products
        SET status_id = ?,
            status_change_reason = ?,
            last_status_change_date = ?,
            last_status_changed_by = ?,
            updated_at = ?
        WHERE data_product_id = ?
        """,
        (status_id, reason, timestamp, changed_by, timestamp, request_id),
    )
    add_timeline(
        db,
        "product",
        current["request_id"],
        request_id,
        "status_changed",
        "Status updated",
        f"Status changed to {status_id}." + (f" Reason: {reason}" if reason else ""),
        stage_id=current["current_stage_id"],
        status_id=status_id,
        created_by=changed_by,
        created_at=timestamp,
    )
    return get_workflow(db, request_id)


def save_initiative_status(db: LakebaseConnection, request_id: str, payload: dict) -> dict:
    timestamp = now()
    status_id = payload.get("statusId")
    reason = str(payload.get("statusChangeReason") or "").strip()
    changed_by = clean_email(payload.get("updatedBy"), "updated by", required=False) or "system"
    if not status_id:
        raise ValueError("statusId is required")
    status_id = ensure_reference(db, "md_statuses", "status_id", status_id, "status")
    current = db.execute("SELECT status_id FROM governance_requests WHERE request_id = ?", (request_id,)).fetchone()
    if not current:
        raise ValueError("initiative not found")
    db.execute(
        """
        UPDATE governance_requests
        SET status_id = ?,
            status_change_reason = ?,
            last_status_change_date = ?,
            last_status_changed_by = ?,
            updated_at = ?
        WHERE request_id = ?
        """,
        (status_id, reason, timestamp, changed_by, timestamp, request_id),
    )
    add_timeline(
        db,
        "request",
        request_id,
        None,
        "status_changed",
        "Initiative status updated",
        f"Status changed from {format_status_for_log(db, current['status_id'])} to {format_status_for_log(db, status_id)}." + (f" Reason: {reason}" if reason else ""),
        status_id=status_id,
        created_by=changed_by,
        created_at=timestamp,
    )
    return get_initiative_by_id(db, request_id)


def update_structured_field(db: LakebaseConnection, request_id: str, key: str, value: str) -> None:
    parent_field_map = {
        "priority_id": "priority_id",
        "scope_id": "scope_id",
        "business_decision": "business_decision",
        "business_value": "business_value",
        "expected_date": "expected_date",
        "additional_comments": "additional_comments",
    }
    field_map = {
        "product_type_id": "product_type_id",
        "data_product_owner": "data_product_owner",
        "expected_output_id": "expected_output_id",
        "target_platform_id": "target_platform_id",
        "lead_domain_id": "lead_domain_id",
        "lead_subdomain_id": "lead_subdomain_id",
        "delivery_date": "delivery_date",
        "delivery_lead": "delivery_lead",
        "effort": "effort",
        "jira_epic_id": "jira_epic_id",
        "jira_link": "jira_link",
        "alation_link": "alation_link",
        "data_domain_owner_user_id": "data_domain_owner_user_id",
        "source_system_id": "source_system_id",
        "domain_delivery_lead_user_id": "domain_delivery_lead_user_id",
        "lynx_pm_user_id": "lynx_pm_user_id",
        "build_status_id": "build_status_id",
    }
    column = field_map.get(key) or parent_field_map.get(key)
    if not column:
        return

    stored_value: str | int | None = value
    if key == "product_type_id":
        stored_value = ensure_reference(db, "md_product_types", "product_type_id", value, "product type")
    elif key == "data_product_owner":
        stored_value = clean_text(value, "Data Product Owner") or None
    elif key == "expected_output_id":
        stored_value = ensure_reference(db, "md_expected_outputs", "expected_output_id", value, "expected output", required=False) or None
    elif key == "target_platform_id":
        stored_value = ensure_reference(db, "md_platforms", "platform_id", value, "target platform")
    elif key == "priority_id":
        stored_value = ensure_reference(db, "md_priorities", "priority_id", value, "priority")
    elif key == "scope_id":
        stored_value = ensure_reference(db, "md_scope_options", "scope_id", value, "scope", required=False) or None
    elif key == "business_decision":
        stored_value = clean_text(value, "business decision", max_length=MAX_TEXTAREA_LENGTH) or None
    elif key == "business_value":
        stored_value = clean_text(value, "business value", max_length=MAX_TEXTAREA_LENGTH) or None
    elif key == "lead_domain_id":
        stored_value = resolve_domain_id(db, value)
    elif key == "lead_subdomain_id":
        stored_value = ensure_reference(db, "md_subdomains", "subdomain_id", value, "lead subdomain", required=False) or None
    elif key == "delivery_date":
        stored_value = clean_date(value, "delivery date") or None
    elif key == "delivery_lead":
        stored_value = ensure_user_role_reference(db, value, "delivery lead", "domain_delivery_lead", required=False) or None
    elif key == "effort":
        stored_value = clean_non_negative_int(value, "effort")
    elif key == "jira_epic_id":
        stored_value = clean_text(value, "Jira epic ID") or None
    elif key == "jira_link":
        stored_value = clean_http_url(value, "Jira link") or None
    elif key == "alation_link":
        stored_value = clean_http_url(value, "Alation link") or None
    elif key == "data_domain_owner_user_id":
        stored_value = ensure_user_role_reference(db, value, "Data Domain Owner", "data_domain_owner", required=False) or None
    elif key == "source_system_id":
        stored_value = ensure_reference(db, "md_source_systems", "source_system_id", value, "source system", required=False) or None
    elif key == "domain_delivery_lead_user_id":
        stored_value = ensure_user_role_reference(db, value, "Hub Owner", "hub_owner", required=False) or None
    elif key == "lynx_pm_user_id":
        stored_value = ensure_user_role_reference(db, value, "Lynx PM", "lynx_pm", required=False) or None
    elif key == "build_status_id":
        stored_value = ensure_reference(db, "md_build_statuses", "build_status_id", value, "build status", required=False) or None
    elif key == "expected_date":
        stored_value = clean_date(value, "expected date") or None
    elif key == "additional_comments":
        stored_value = clean_text(value, "additional comments", max_length=MAX_TEXTAREA_LENGTH) or None

    if key in parent_field_map:
        db.execute(
            f"""
            UPDATE governance_requests
            SET {column} = ?
            WHERE request_id = (SELECT request_id FROM data_products WHERE data_product_id = ?)
            """,
            (stored_value, request_id),
        )
        return

    db.execute(f"UPDATE data_products SET {column} = ? WHERE data_product_id = ?", (stored_value, request_id))


def reconcile_domain_subdomain(db: LakebaseConnection, request_id: str) -> None:
    row = db.execute(
        """
        SELECT r.lead_domain_id, r.lead_subdomain_id, s.domain_id AS subdomain_domain_id
        FROM data_products r
        LEFT JOIN md_subdomains s ON s.subdomain_id = r.lead_subdomain_id
        WHERE r.data_product_id = ?
        """,
        (request_id,),
    ).fetchone()
    if not row or not row["lead_subdomain_id"]:
        return
    if row["lead_domain_id"] == row["subdomain_domain_id"]:
        return
    db.execute("UPDATE data_products SET lead_subdomain_id = NULL WHERE data_product_id = ?", (request_id,))
    db.execute(
        """
        DELETE FROM product_stage_answers
        WHERE data_product_id = ?
          AND requirement_id IN ('reuse_domain_lead_subdomain_id')
        """,
        (request_id,),
    )


def advance_if_complete(db: LakebaseConnection, request_id: str, saved_stage_id: str, timestamp: str) -> bool:
    current = db.execute(
        """
        SELECT r.request_id, r.current_stage_id, s.stage_number
        FROM data_products r
        JOIN md_stages s ON s.stage_id = r.current_stage_id
        WHERE r.data_product_id = ?
        """,
        (request_id,),
    ).fetchone()
    if not current or current["current_stage_id"] != saved_stage_id:
        return False

    requirements = get_stage_requirements(db, request_id, saved_stage_id)
    missing_required = any(item["is_required"] and not is_answer_complete(item) for item in requirements)
    if missing_required:
        return False

    next_stage = db.execute(
        "SELECT stage_id FROM md_stages WHERE stage_number > ? ORDER BY stage_number LIMIT 1",
        (current["stage_number"],),
    ).fetchone()
    if not next_stage:
        db.execute("UPDATE data_products SET status_id = 'operating' WHERE data_product_id = ?", (request_id,))
        add_timeline(db, "product", current["request_id"], request_id, "completed", "Workflow completed", "All stages are complete.", stage_id=saved_stage_id, status_id="operating", created_by="admin", created_at=timestamp)
        return False

    next_status = "operating" if next_stage["stage_id"] == "operate" else "in_review"
    db.execute(
        """
        UPDATE data_products
        SET current_stage_id = ?, status_id = ?, note = 'Advanced automatically after required information was completed.'
        WHERE data_product_id = ?
        """,
        (next_stage["stage_id"], next_status, request_id),
    )
    add_timeline(db, "product", current["request_id"], request_id, "stage_advanced", "Stage advanced", f"Advanced from {saved_stage_id} to {next_stage['stage_id']}.", stage_id=next_stage["stage_id"], from_stage_id=saved_stage_id, to_stage_id=next_stage["stage_id"], status_id=next_status, created_by="system", created_at=timestamp)
    return True


def add_timeline(
    db: LakebaseConnection,
    entity_type: str,
    request_id: str,
    data_product_id: str | None,
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
        INSERT INTO governance_timeline (
          timeline_id, entity_type, request_id, data_product_id, event_type, stage_id, from_stage_id, to_stage_id,
          status_id, event_label, event_detail, created_by, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (str(uuid.uuid4()), entity_type, request_id, data_product_id, event_type, stage_id, from_stage_id, to_stage_id, status_id, event_label, event_detail, created_by or "system", created_at or now()),
    )


def effective_stage_entered_at(row: dict) -> str:
    return valid_timestamp_or_empty(row["current_stage_entered_at"]) or valid_timestamp_or_empty(row["created_at"]) or now()


def valid_timestamp_or_empty(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parse_timestamp(text)
    except ValueError:
        return ""
    return text


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def serialize_request(row: dict) -> dict:
    current_stage_entered_at = effective_stage_entered_at(row)
    stage_id = row["current_stage_id"] or ""
    status_id = row["status_id"] or ""
    delivery_lead = row["delivery_lead"] or ""
    delivery_lead_name = row["delivery_lead_name"] or delivery_lead
    return {
        "id": normalize_request_number(row["data_product_number"]),
        "requestId": row["data_product_id"],
        "initiativeRequestId": row["initiative_request_id"],
        "initiativeNumber": normalize_request_number(row["request_number"]),
        "title": row["title"],
        "description": row["description"] or "",
        "domain": row["domain_name"] or "Unassigned",
        "domainId": row["lead_domain_id"] or "",
        "businessUnit": row["business_unit_name"] or "",
        "type": row["product_type_name"],
        "dataProductOwner": row["data_product_owner"] or "",
        "expectedOutput": row["expected_output_name"] or "",
        "expectedOutputId": row["expected_output_id"] or "",
        "businessValue": row["business_value"] or "",
        "platform": row["platform_name"],
        "priority": row["priority_name"],
        "scope": row["scope_name"] or "",
        "requester": row["requester_name"] or "",
        "requesterEmail": row["requester_email"] or "",
        "initiative": row["initiative"] or "",
        "expectedDate": row["expected_date"] or "",
        "deliveryDate": row["delivery_date"] or "",
        "deliveryLead": delivery_lead_name,
        "deliveryLeadId": delivery_lead,
        "effort": row["effort"],
        "jiraEpicId": row["jira_epic_id"] or "",
        "jiraLink": row["jira_link"] or "",
        "alationLink": row["alation_link"] or "",
        "additionalComments": row["additional_comments"] or "",
        "stage": row["stage_name"] or stage_id or "Unassigned",
        "stageId": stage_id,
        "stageNumber": row["stage_number"] or 0,
        "currentStageEnteredAt": format_date(current_stage_entered_at),
        "daysInStage": days_since(current_stage_entered_at),
        "status": row["status_name"] or status_id or "Unassigned",
        "statusId": status_id,
        "statusChangeReason": row["status_change_reason"] or "",
        "lastStatusChangeDate": row["last_status_change_date"] or "",
        "lastStatusChangedBy": row["last_status_changed_by"] or "",
        "leadSubdomain": row["subdomain_name"] or "",
        "leadSubdomainDomainId": row["subdomain_domain_id"] or "",
        "dataDomainOwner": row["data_domain_owner_name"] or "",
        "sourceSystem": row["source_system_name"] or "",
        "domainDeliveryLead": row["domain_delivery_lead_name"] or "",
        "hubOwner": row["domain_delivery_lead_name"] or "",
        "lynxPm": row["lynx_pm_name"] or "",
        "buildStatus": row["build_status_name"] or "",
        "owner": row["data_domain_owner_name"] or row["requester_name"] or "Unassigned",
        "note": row["note"] or "",
        "searchText": row["search_text"] or "",
    }


def serialize_initiative(row: dict) -> dict:
    status_id = row["status_id"] or ""
    return {
        "id": normalize_request_number(row["request_number"]),
        "requestId": row["request_id"],
        "initiative": row["initiative"] or "",
        "title": row["initiative"] or f"Initiative {normalize_request_number(row['request_number'])}",
        "businessDecision": row["business_decision"] or "",
        "description": row["business_decision"] or "",
        "businessValue": row["business_value"] or "",
        "businessUnit": row["business_unit_name"] or "",
        "businessUnitId": row["business_unit_id"] or "",
        "scope": row["scope_name"] or "",
        "scopeId": row["scope_id"] or "",
        "priority": row["priority_name"] or "",
        "priorityId": row["priority_id"] or "",
        "expectedOutput": row["expected_output_name"] or "",
        "expectedOutputId": row["expected_output_id"] or "",
        "platform": row["platform_name"] or "",
        "platformId": row["target_platform_id"] or "",
        "requester": row["requester_name"] or "",
        "requesterEmail": row["requester_email"] or "",
        "expectedDate": row["expected_date"] or "",
        "additionalComments": row["additional_comments"] or "",
        "status": row["status_name"] or status_id or "Unassigned",
        "statusId": status_id,
        "statusChangeReason": row["status_change_reason"] or "",
        "lastStatusChangeDate": row["last_status_change_date"] or "",
        "lastStatusChangedBy": row["last_status_changed_by"] or "",
        "productCount": int(row["product_count"] or 0),
        "note": row["note"] or "",
        "createdAt": row["created_at"] or "",
        "updatedAt": row["updated_at"] or "",
        "searchText": row["search_text"] or "",
    }


def days_since(value: str) -> int:
    try:
        entered_at = parse_timestamp(value)
    except (TypeError, ValueError):
        return 0
    return max(0, (datetime.now(timezone.utc) - entered_at).days)


def format_date(value: str) -> str:
    try:
        return parse_timestamp(value).date().isoformat()
    except (TypeError, ValueError):
        return str(value or "")[:10]


class GovernanceHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/index.html", "/app.js", "/styles.css"} or path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/health":
                payload = {"ok": STARTUP_ERROR is None, "database": database_label()}
                if STARTUP_ERROR:
                    payload["startupError"] = STARTUP_ERROR
                else:
                    try:
                        with connect() as db:
                            payload["counts"] = master_data_counts(db)
                    except Exception as exc:
                        payload["ok"] = False
                        payload["healthError"] = f"{type(exc).__name__}: {exc}"
                self.send_json(payload)
                return
            if STARTUP_ERROR:
                self.send_json(startup_error_payload(), status=503)
                return
            if path == "/api/session":
                email, identity_source = resolve_user_email(self.headers)
                with connect() as db:
                    session = get_session(db, email)
                    session["identitySource"] = identity_source
                    self.send_json(session)
                return
            if path == "/api/master-data":
                with connect() as db:
                    self.send_json(get_cached_master_data(db))
                return
            if path == "/api/dashboard":
                with connect() as db:
                    self.send_json(get_dashboard(db))
                return
            if path == "/api/requests":
                with connect() as db:
                    self.send_json(get_requests(db))
                return
            if path == "/api/initiatives":
                with connect() as db:
                    self.send_json(get_initiatives(db))
                return
            if path.startswith("/api/initiatives/"):
                request_id = path.split("/")[3]
                with connect() as db:
                    self.send_json(get_initiative_by_id(db, request_id))
                return
            if path.startswith("/api/requests/") and path.endswith("/workflow"):
                request_id = path.split("/")[3]
                with connect() as db:
                    self.send_json(get_workflow(db, request_id))
                return
            super().do_GET()
        except PermissionError as exc:
            self.send_json({"error": str(exc)}, status=403)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, status=400)
        except Exception as exc:
            log_exception(f"GET {path}", exc)
            self.send_json({"error": "Internal server error"}, status=500)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if STARTUP_ERROR:
                self.send_json(startup_error_payload(), status=503)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length > MAX_REQUEST_BODY_BYTES:
                self.send_json({"error": "Request body is too large"}, status=413)
                return
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            except json.JSONDecodeError as exc:
                raise ValueError("Request body must be valid JSON") from exc
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object")

            if path.startswith("/api/requests/") and path.endswith("/answers"):
                request_id = path.split("/")[3]
                actor_email = request_user_email(self.headers)
                payload["updatedBy"] = actor_email
                with connect() as db:
                    require_admin(db, actor_email)
                    result = save_workflow_answers(db, request_id, payload)
                    db.commit()
                self.send_json(result)
                return

            if path.startswith("/api/requests/") and path.endswith("/status"):
                request_id = path.split("/")[3]
                actor_email = request_user_email(self.headers)
                payload["updatedBy"] = actor_email
                with connect() as db:
                    require_admin(db, actor_email)
                    result = save_request_status(db, request_id, payload)
                    db.commit()
                self.send_json(result)
                return

            if path.startswith("/api/initiatives/") and path.endswith("/status"):
                request_id = path.split("/")[3]
                actor_email = request_user_email(self.headers)
                payload["updatedBy"] = actor_email
                with connect() as db:
                    require_admin(db, actor_email)
                    result = save_initiative_status(db, request_id, payload)
                    db.commit()
                self.send_json(result)
                return

            if path.startswith("/api/master-data/"):
                collection = path.split("/")[3]
                actor_email = request_user_email(self.headers)
                with connect() as db:
                    require_admin(db, actor_email)
                    result = upsert_master_data_item(db, collection, payload)
                    db.commit()
                    clear_master_data_cache()
                    master_data = get_cached_master_data(db)
                self.send_json({"saved": result, "masterData": master_data}, status=201)
                return

            if path.startswith("/api/requests/") and path.endswith("/products"):
                request_id = path.split("/")[3]
                actor_email = request_user_email(self.headers)
                with connect() as db:
                    require_admin(db, actor_email)
                    result = insert_product(db, request_id, payload, actor_email)
                    db.commit()
                self.send_json(result, status=201)
                return

            if path != "/api/requests":
                self.send_json({"error": "Not found"}, status=404)
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
            self.send_json({"error": str(exc)}, status=403)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, status=400)
        except Exception as exc:
            log_exception(f"POST {path}", exc)
            self.send_json({"error": "Internal server error"}, status=500)

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        try:
            if STARTUP_ERROR:
                self.send_json(startup_error_payload(), status=503)
                return
            if path.startswith("/api/master-data/"):
                parts = path.split("/")
                if len(parts) != 5:
                    self.send_json({"error": "Not found"}, status=404)
                    return
                with connect() as db:
                    session = get_session(db, request_user_email(self.headers))
                    if not session.get("canDeleteMasterData"):
                        self.send_json({"error": "Only admins can remove master data"}, status=403)
                        return
                    result = delete_master_data_item(db, parts[3], parts[4])
                    db.commit()
                    clear_master_data_cache()
                    master_data = get_cached_master_data(db)
                self.send_json({"deleted": result, "masterData": master_data})
                return
            self.send_json({"error": "Not found"}, status=404)
        except PermissionError as exc:
            self.send_json({"error": str(exc)}, status=403)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, status=400)
        except Exception as exc:
            log_exception(f"DELETE {path}", exc)
            self.send_json({"error": "Internal server error"}, status=500)

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    global STARTUP_ERROR
    print("Starting Governance Input Tool", flush=True)
    try:
        validate_database_ready()
    except Exception as exc:
        STARTUP_ERROR = f"{type(exc).__name__}: {exc}"
        log_exception("startup database initialization", exc)
    port_value = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].isdigit() else os.getenv("DATABRICKS_APP_PORT", os.getenv("PORT", "8502"))
    port = int(port_value)
    server = ThreadingHTTPServer(("0.0.0.0", port), GovernanceHandler)
    print(f"Serving Governance Input Tool on http://localhost:{port}", flush=True)
    if STARTUP_ERROR:
        print(f"Startup database error: {STARTUP_ERROR}", flush=True)
    else:
        print(f"Lakebase database: {database_label()}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
