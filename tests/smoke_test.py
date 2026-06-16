from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import server  # noqa: E402


def main() -> None:
    try:
        server.resolve_user_email({"X-User-Email": "kerem.seyid@syngenta.com"})
    except PermissionError:
        pass
    else:
        raise AssertionError("client-controlled X-User-Email must not be trusted")

    email, source = server.resolve_user_email({"X-Forwarded-Email": "kerem.seyid@syngenta.com"})
    assert email == "kerem.seyid@syngenta.com"
    assert source == "X-Forwarded-Email"

    assert server.normalize_request_number("155") == "00000155"
    assert server.normalize_request_number("REQ-155") == "00000155"
    assert server.request_number_sort_value("00000155") == 155
    assert server.request_number_sort_value("REQ-155") == 155
    assert server.request_number_sort_value("DP-00000155") == 155

    assert server.clean_email("Kerem.Seyid@Syngenta.com") == "kerem.seyid@syngenta.com"
    assert server.slug_id("Commercial Domain") == "commercial_domain"
    assert server.describe_workflow_changes(
        None,
        [
            {
                "label": "Business value",
                "input_type": "textarea",
                "master_data_type": None,
                "old": "",
                "new": "Faster commercial decision making",
            }
        ],
    ) == "Business value: empty -> Faster commercial decision making"
    assert server.describe_workflow_changes(None, []) == "Submitted with no field changes."

    try:
        server.clean_http_url("javascript:alert(1)", "Jira link")
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe URLs must be rejected")


if __name__ == "__main__":
    main()
