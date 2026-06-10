from __future__ import annotations

import os
import sys
import tempfile
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

            dashboard = server.get_dashboard(db)
            assert dashboard["total"] >= 15

            created = server.insert_request(
                db,
                {
                    "title": "Smoke request",
                    "description": "Smoke test request",
                    "domain": "commercial",
                    "businessUnit": "cp",
                    "productType": "structured",
                    "platform": "databricks",
                    "priority": "p2",
                    "scope": "global",
                    "requester": "Smoke Tester",
                    "requesterEmail": "smoke.tester@syngenta.com",
                    "expectedDate": "2026-06-30",
                    "additionalComments": "Created by smoke test",
                },
            )
            assert created["stageId"] == "intake"

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

            try:
                server.save_workflow_answers(
                    db,
                    created["requestId"],
                    {
                        "stageId": "reuse_domain",
                        "updatedBy": "kerem.seyid@syngenta.com",
                        "answers": {"reuse_domain_jira_link": "javascript:alert(1)"},
                    },
                )
            except ValueError:
                pass
            else:
                raise AssertionError("unsafe Jira link must be rejected")

            db.commit()


if __name__ == "__main__":
    main()
