from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["GOVERNANCE_BACKEND"] = "sqlite"
        os.environ["GOVERNANCE_SQLITE_PATH"] = str(Path(tmpdir) / "smoke.sqlite")
        os.environ["GOVERNANCE_SEED_DEMO_DATA"] = "true"

        import server

        server.DB_PATH = Path(os.environ["GOVERNANCE_SQLITE_PATH"])
        server.APP_BACKEND = "sqlite"
        server.init_db()

        try:
            server.resolve_user_email({"X-User-Email": "kerem.seyid@syngenta.com"})
        except PermissionError:
            pass
        else:
            raise AssertionError("client X-User-Email must not be trusted")

        email, source = server.resolve_user_email({"X-Forwarded-Email": "kerem.seyid@syngenta.com"})
        assert email == "kerem.seyid@syngenta.com"
        assert source == "X-Forwarded-Email"

        with server.connect() as db:
            session = server.get_session(db, "kerem.seyid@syngenta.com")
            assert session["canAdmin"] is True

            restore_request = db.execute(
                "SELECT request_id FROM data_product_requests_new WHERE request_number = ?",
                ("00000007",),
            ).fetchone()["request_id"]
            db.execute("INSERT OR IGNORE INTO md_stages VALUES (?, ?, ?)", ("domain_ownership", "Domain Ownership", 2))
            db.execute(
                "UPDATE data_product_requests_new SET current_stage_id = ? WHERE request_id = ?",
                ("domain_ownership", restore_request),
            )
            db.execute(
                """
                INSERT INTO request_stage_answers (answer_id, request_id, requirement_id, answer_value, updated_at)
                VALUES (?, ?, ?, ?, ?), (?, ?, ?, ?, ?)
                """,
                (
                    "leftover-domain-answer",
                    restore_request,
                    "domain_ownership_jira_link",
                    "https://jira.example.com/browse/RESTORE",
                    "2026-01-01T00:00:00+00:00",
                    "leftover-owner-answer",
                    restore_request,
                    "domain_ownership_data_domain_owner_user_id",
                    "udo_anna",
                    "2026-01-01T00:00:00+00:00",
                ),
            )
            server.seed_master_data(db)
            server.seed_stage_requirements(db)

            master_data = server.get_master_data(db)
            assert [stage["id"] for stage in master_data["stages"]] == [
                "intake",
                "reuse_domain",
                "ownership",
                "requirements",
                "architecture_review",
                "build_validate",
                "publish",
                "operate",
            ]
            assert [stage["name"] for stage in master_data["stages"][:3]] == [
                "Intake",
                "Domain Ownership",
                "Estimation",
            ]
            restored = server.get_request_by_id(db, restore_request)
            assert restored["stageId"] == "ownership"
            assert not db.execute("SELECT 1 FROM md_stages WHERE stage_id = ?", ("domain_ownership",)).fetchone()
            assert db.execute(
                "SELECT 1 FROM request_stage_answers WHERE request_id = ? AND requirement_id = ?",
                (restore_request, "ownership_jira_link"),
            ).fetchone()
            assert db.execute(
                "SELECT 1 FROM request_stage_answers WHERE request_id = ? AND requirement_id = ?",
                (restore_request, "reuse_domain_data_domain_owner_user_id"),
            ).fetchone()

            dashboard = server.get_dashboard(db)
            assert dashboard["total"] >= 15

            created_at = (datetime.now(timezone.utc) - timedelta(days=9)).isoformat()
            created = server.insert_request(
                db,
                {
                    "title": "Smoke request",
                    "description": "Smoke test request",
                    "domain": "commercial",
                    "businessUnit": "cp",
                    "requester": "Smoke Tester",
                    "requesterEmail": "smoke.tester@syngenta.com",
                    "expectedDate": "2026-06-30",
                },
                timestamp=created_at,
            )
            assert created["stageId"] == "intake"
            assert created["id"] == "00000016"

            db.execute("DELETE FROM request_timeline WHERE request_id = ?", (created["requestId"],))
            created_without_timeline = server.get_request_by_id(db, created["requestId"])
            assert created_without_timeline["daysInStage"] >= 8
            assert created_without_timeline["currentStageEnteredAt"] == created_at[:10]

            workflow = server.save_workflow_answers(
                db,
                created["requestId"],
                {
                    "stageId": "intake",
                    "statusId": "in_review",
                    "updatedBy": "kerem.seyid@syngenta.com",
                    "answers": {
                        "intake_business_decision": "Support production smoke validation",
                        "intake_expected_date": "2026-06-30",
                        "intake_additional_comments": "Smoke stage completed",
                    },
                },
            )
            assert workflow["advanced"] is True
            assert workflow["request"]["stageId"] == "reuse_domain"

            workflow = server.save_workflow_answers(
                db,
                created["requestId"],
                {
                    "stageId": "reuse_domain",
                    "updatedBy": "kerem.seyid@syngenta.com",
                    "answers": {
                        "reuse_domain_lead_domain_id": "commercial",
                        "reuse_domain_lead_subdomain_id": "sales_commercial_transactions",
                        "reuse_domain_delivery_lead": "ddl_james",
                        "reuse_domain_data_domain_owner_user_id": "udo_anna",
                        "reuse_domain_domain_delivery_lead_user_id": "ddl_james",
                        "reuse_domain_lynx_pm_user_id": "pm_lynx_maya",
                    },
                },
            )
            assert workflow["advanced"] is True
            assert workflow["request"]["stageId"] == "ownership"

            try:
                server.save_workflow_answers(
                    db,
                    created["requestId"],
                    {
                        "stageId": "ownership",
                        "updatedBy": "kerem.seyid@syngenta.com",
                        "answers": {"ownership_jira_link": "javascript:alert(1)"},
                    },
                )
            except ValueError:
                pass
            else:
                raise AssertionError("unsafe Jira link must be rejected")

            db.commit()


if __name__ == "__main__":
    main()
