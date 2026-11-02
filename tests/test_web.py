import json
import sqlite3
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from compliance import __version__
from compliance.cli import main
from compliance.web import build_server, load_credentials, serve

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
AS_OF = "2026-10-26"
TEST_USER = "tester"
TEST_PASSWORD = "only-for-these-tests"
session_cookie = {"value": None}


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "db" / "compliance.db"
    monkeypatch.setenv("COMPLIANCE_DB_PATH", str(path))
    monkeypatch.setenv("COMPLIANCE_UI_USER", TEST_USER)
    monkeypatch.setenv("COMPLIANCE_UI_PASSWORD", TEST_PASSWORD)
    session_cookie["value"] = None
    return path


@pytest.fixture
def url(db_path):
    server = build_server("127.0.0.1", 0, DATA_DIR)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    address = f"http://127.0.0.1:{server.server_address[1]}"
    _sign_in(address)
    yield address
    server.shutdown()
    server.server_close()
    thread.join()


def _sign_in(url, username=TEST_USER, password=TEST_PASSWORD):
    body = json.dumps({"username": username, "password": password}).encode()
    request = urllib.request.Request(url + "/api/login", data=body, headers={"Content-Type": "application/json"}, method="POST")
    status, raw, headers = _send(request)
    cookie = headers.get("Set-Cookie")
    if status == 200:
        session_cookie["value"] = cookie.split(";")[0]
    return status, json.loads(raw), cookie


def _send(request):
    if session_cookie["value"]:
        request.add_header("Cookie", session_cookie["value"])
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read(), response.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers


def _get(url, path):
    status, body, _ = _send(urllib.request.Request(url + path))
    return status, json.loads(body)


def _post(url, payload, headers=None):
    headers = {"Content-Type": "application/json", **(headers or {})}
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    status, raw, _ = _send(urllib.request.Request(url + "/api/run", data=body, headers=headers, method="POST"))
    return status, json.loads(raw)


def _run(url, dataset="sample", as_of=AS_OF, save=False):
    return _post(url, {"dataset": dataset, "as_of": as_of, "save": save})


def _count(path, table):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


# page and options


def test_index_serves_the_page(url):
    status, body, headers = _send(urllib.request.Request(url + "/"))
    assert status == 200
    assert headers["Content-Type"].startswith("text/html")
    assert b"Supplier Compliance" in body


def test_options_fill_every_dropdown(url):
    status, options = _get(url, "/api/options")
    assert status == 200
    assert options["version"] == __version__
    assert [d["id"] for d in options["datasets"]] == ["sample", "renewal", "no_issues", "broken"]
    assert options["default_as_of"] == AS_OF
    assert AS_OF in [d["value"] for d in options["dates"]]
    assert {"SUP-101", "SUP-104", "SUP-106"} <= set(options["suppliers"])
    assert options["flag_types"] == ["expired", "expiring_soon", "missing", "pending"]


def test_options_do_not_touch_the_database(url, db_path):
    _get(url, "/api/options")
    assert not db_path.exists()


# run


def test_preview_matches_the_expected_numbers_and_saves_nothing(url, db_path):
    status, result = _run(url)
    assert status == 200
    assert result["saved"] is False
    assert result["check_id"] is None
    assert result["counts"] == {
        "suppliers": 8, "clean_suppliers": 4, "parts": 9, "at_risk": 4, "flags": 9, "rejected": 8,
    }
    assert not db_path.exists()


def test_run_returns_rows_for_each_section(url):
    _, result = _run(url)
    expired = [f for f in result["flags"] if f["flag_type"] == "expired"]
    assert expired == [{
        "flag_type": "expired", "supplier_id": "SUP-102", "document_type": "safety_cert",
        "document_id": "DOC-005", "expiry_date": "2026-06-01", "days_until_expiry": -147,
    }]
    at_risk = {p["part_number"]: p for p in result["at_risk"]}
    assert at_risk["PRT-5005"]["description"] == "Chassis hinge"
    assert at_risk["PRT-5005"]["reasons"] == ["missing quality_cert", "missing env_declaration"]
    assert "PRT-5004" not in at_risk
    rejected = {r["id"]: r for r in result["rejected"]}
    assert rejected["DOC-015"]["supplier_id"] == "SUP-105"
    assert rejected["DOC-015"]["reason"] == "unknown status"
    assert rejected["DOC-015"]["source"] == "documents.json"


def test_saved_run_matches_the_cli_report(url, db_path, capsys):
    status, result = _run(url, save=True)
    assert status == 200
    assert result["saved"] is True
    assert result["check_id"] == 1
    args = ["--documents", str(DATA_DIR / "documents.json"), "--parts", str(DATA_DIR / "parts.json"),
            "--settings", str(DATA_DIR / "settings.json"), "--today", AS_OF]
    assert main(["run", *args]) == 0
    expected = capsys.readouterr().out.replace("check 2", "check 1")
    assert result["report_text"] == expected


def test_saving_twice_grows_history_not_inputs(url, db_path):
    _run(url, save=True)
    _, second = _run(url, save=True)
    assert second["check_id"] == 2
    assert _count(db_path, "compliance_checks") == 2
    assert _count(db_path, "flags") == 18
    assert _count(db_path, "documents") == 19


def test_a_later_date_changes_the_result(url):
    _, result = _run(url, as_of="2027-12-31")
    assert "DOC-002" in {f["document_id"] for f in result["flags"] if f["flag_type"] == "expired"}
    assert result["as_of"] == "2027-12-31"


def test_renewal_scenario_clears_the_old_flag(url, db_path):
    _, result = _run(url, dataset="renewal")
    assert result["counts"]["flags"] == 8
    assert result["counts"]["at_risk"] == 3
    assert "DOC-005" not in {f["document_id"] for f in result["flags"]}
    assert not db_path.exists()


def test_no_issues_scenario(url):
    _, result = _run(url, dataset="no_issues")
    assert result["counts"]["flags"] == 0
    assert "No issues found" in result["report_text"]


def test_broken_file_gives_a_clear_error_and_the_server_keeps_working(url, db_path):
    status, result = _run(url, dataset="broken")
    assert status == 400
    assert "broken_documents.json" in result["error"]
    assert "not valid JSON" in result["error"]
    assert result["error"].startswith("data/scenarios/")
    assert str(DATA_DIR) not in result["error"]
    assert not db_path.exists()
    assert _run(url)[0] == 200


@pytest.mark.parametrize("payload, message", [
    ({"dataset": "nope", "as_of": AS_OF}, "data set"),
    ({"dataset": "../../etc/passwd", "as_of": AS_OF}, "data set"),
    ({"dataset": ["sample"], "as_of": AS_OF}, "data set"),
    ({"dataset": "sample", "as_of": "26/10/2026"}, "date"),
    ({"dataset": "sample", "as_of": "20261026"}, "date"),
    ({"dataset": "sample", "as_of": "2026-13-45"}, "date"),
    ({"dataset": "sample", "as_of": 20261026}, "date"),
    ({"dataset": "sample", "as_of": AS_OF, "save": "yes"}, "save"),
    ({"dataset": "renewal", "as_of": AS_OF, "save": True}, "only the sample data"),
    ([1, 2], "JSON object"),
])
def test_bad_run_requests_are_refused(url, db_path, payload, message):
    status, result = _post(url, payload)
    assert status == 400
    assert message in result["error"]
    assert not db_path.exists()


def test_invalid_json_body_is_refused(url):
    status, result = _post(url, b"{not json")
    assert status == 400
    assert "JSON" in result["error"]


def test_wrong_content_type_is_refused(url):
    status, result = _post(url, {"dataset": "sample"}, {"Content-Type": "text/plain"})
    assert status == 415
    assert "application/json" in result["error"]


def test_request_from_another_site_is_refused(url):
    status, result = _post(url, {"dataset": "sample", "as_of": AS_OF}, {"Origin": "https://evil.example"})
    assert status == 403
    assert "another site" in result["error"]


def test_oversized_body_is_refused(url):
    status, result = _post(url, b" " * 20_000)
    assert status == 413
    assert "too large" in result["error"]


# history


def test_history_lists_checks_newest_first(url):
    _run(url, save=True)
    _run(url, as_of="2026-12-31", save=True)
    status, result = _get(url, "/api/history?supplier=SUP-103")
    assert status == 200
    assert result["status"] == "flags"
    assert [c["check_id"] for c in result["checks"]] == [2, 1]
    assert result["checks"][0]["as_of_date"] == "2026-12-31"
    assert {"flag_type": "missing", "document_type": "safety_cert", "document_id": None,
            "expiry_date": None} in result["checks"][1]["flags"]


def test_history_tells_clean_from_never_saved(url):
    _run(url, save=True)
    assert _get(url, "/api/history?supplier=SUP-101")[1]["status"] == "clean"
    assert _get(url, "/api/history?supplier=SUP-104")[1]["status"] == "not_saved"


def test_history_before_any_check_is_empty_not_an_error(url):
    status, result = _get(url, "/api/history?supplier=SUP-103")
    assert status == 200
    assert result["status"] == "not_saved"


def test_history_is_safe_with_odd_supplier_values(url):
    odd = urllib.parse.quote("x' OR '1'='1")
    assert _get(url, f"/api/history?supplier={odd}")[1]["status"] == "not_saved"
    status, result = _get(url, "/api/history")
    assert status == 400
    assert "supplier" in result["error"]


# input data


def test_data_shows_clean_and_rejected_records(url):
    status, result = _get(url, "/api/data?dataset=sample")
    assert status == 200
    assert len(result["documents"]) == 19
    assert len(result["parts"]) == 9
    assert len(result["rejected"]) == 8
    assert result["settings"]["expiring_soon_days"] == 45
    assert result["settings"]["required_documents"]["mechanical"] == ["quality_cert", "env_declaration"]
    doc_001 = next(d for d in result["documents"] if d["document_id"] == "DOC-001")
    assert doc_001["expiry_date"] is None
    assert doc_001["status"] == "approved"


def test_data_rejects_unknown_data_set(url):
    status, result = _get(url, "/api/data?dataset=nope")
    assert status == 400
    assert "data set" in result["error"]


def test_data_on_a_broken_file_is_a_clear_error(url):
    status, result = _get(url, "/api/data?dataset=broken")
    assert status == 400
    assert "broken_documents.json" in result["error"]


# routing


@pytest.mark.parametrize("path", ["/nope", "/api/nope", "/../../etc/passwd", "/static/../cli.py"])
def test_unknown_paths_are_404_json(url, path):
    status, result = _get(url, path)
    assert status == 404
    assert "error" in result


def test_get_on_run_is_not_allowed(url):
    status, result = _get(url, "/api/run")
    assert status == 405
    assert "error" in result


def test_missing_data_dir_gives_a_clear_error(db_path, tmp_path):
    server = build_server("127.0.0.1", 0, tmp_path / "nope")
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        address = f"http://127.0.0.1:{server.server_address[1]}"
        _sign_in(address)
        status, result = _get(address, "/api/options")
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    assert status == 400
    assert "settings.json" in result["error"]


# scenario data stays honest


def test_renewal_scenario_is_the_sample_plus_one_renewal():
    sample = json.loads((DATA_DIR / "documents.json").read_text())
    renewal = json.loads((DATA_DIR / "scenarios" / "renewal_documents.json").read_text())
    assert renewal[:-1] == sample
    assert renewal[-1]["document_id"] == "DOC-005-R1"


# signing in


@pytest.mark.parametrize("path", ["/api/options", "/api/history?supplier=SUP-103", "/api/data?dataset=sample"])
def test_data_needs_a_session(url, path):
    session_cookie["value"] = None
    status, result = _get(url, path)
    assert status == 401
    assert "Sign in" in result["error"]


def test_running_a_check_needs_a_session(url, db_path):
    session_cookie["value"] = None
    status, _ = _run(url, save=True)
    assert status == 401
    assert not db_path.exists()


def test_page_is_public_but_holds_no_data(url):
    session_cookie["value"] = None
    status, body, _ = _send(urllib.request.Request(url + "/"))
    assert status == 200
    assert b"SUP-1" not in body
    assert TEST_PASSWORD.encode() not in body


def test_session_endpoint(url):
    assert _get(url, "/api/session") == (200, {"authenticated": True, "username": TEST_USER})
    session_cookie["value"] = None
    assert _get(url, "/api/session") == (200, {"authenticated": False})


def test_sign_in_sets_a_protected_cookie(url):
    status, result, cookie = _sign_in(url)
    assert status == 200
    assert result["username"] == TEST_USER
    assert "HttpOnly" in cookie
    assert "SameSite=Strict" in cookie
    assert TEST_PASSWORD not in cookie


@pytest.mark.parametrize("username, password", [
    (TEST_USER, "wrong"),
    ("someone", TEST_PASSWORD),
    ("", ""),
    (["x"], {"y": 1}),
])
def test_bad_credentials_are_refused_with_one_message(url, username, password):
    session_cookie["value"] = None
    status, result, cookie = _sign_in(url, username, password)
    assert status == 401
    assert result["error"] == "That username and password do not match."
    assert cookie is None


def test_too_many_failures_lock_sign_in(url):
    session_cookie["value"] = None
    for _ in range(5):
        assert _sign_in(url, password="wrong")[0] == 401
    status, result, _ = _sign_in(url)
    assert status == 429
    assert "Too many" in result["error"]


def test_sign_out_ends_the_session(url):
    request = urllib.request.Request(url + "/api/logout", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    assert _send(request)[0] == 200
    assert _get(url, "/api/options")[0] == 401


def test_session_expires(url, monkeypatch):
    monkeypatch.setattr("compliance.web.SESSION_SECONDS", -1)
    _sign_in(url)
    status, _ = _get(url, "/api/options")
    assert status == 401


def test_serving_beyond_this_machine_needs_your_own_password(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("COMPLIANCE_UI_PASSWORD", raising=False)
    assert serve("0.0.0.0", 0, tmp_path) == 1
    assert "COMPLIANCE_UI_PASSWORD" in capsys.readouterr().err


def test_default_account_refuses_a_wrong_password(monkeypatch):
    monkeypatch.delenv("COMPLIANCE_UI_USER", raising=False)
    monkeypatch.delenv("COMPLIANCE_UI_PASSWORD", raising=False)
    username, check = load_credentials()
    assert username == "compliance.manager"
    assert not check("wrong")


# reminders


def _reminders(url, dataset="sample", as_of=AS_OF):
    return _run(url, dataset, as_of)[1]["reminders"]


def test_reminders_are_ordered_by_urgency(url):
    severities = [r["severity"] for r in _reminders(url)]
    order = ["action", "soon", "review", "unreadable"]
    assert severities == sorted(severities, key=order.index)
    assert severities.count("action") == 6     # 1 expired + 5 missing
    assert severities.count("soon") == 2
    assert severities.count("review") == 1
    assert severities.count("unreadable") == 8


def test_expired_reminder_says_how_long_and_who_is_affected(url):
    reminder = next(r for r in _reminders(url) if r["document_id"] == "DOC-005")
    assert reminder["title"] == "Safety certificate expired 147 days ago"
    assert reminder["affected_parts"] == [{"part_number": "PRT-5002", "description": "Monitor power switch"}]
    assert "DOC-005" in reminder["draft"]
    assert "2026-06-01" in reminder["draft"]
    assert "PRT-5002" in reminder["draft"]


def test_expiring_reminder_counts_down(url):
    reminders = {r["document_id"]: r for r in _reminders(url) if r["document_id"]}
    assert reminders["DOC-006"]["title"] == "Environmental declaration expires in 25 days"
    assert reminders["DOC-008"]["title"] == "Environmental declaration expires today"
    assert [r["document_id"] for r in _reminders(url) if r["severity"] == "soon"] == ["DOC-008", "DOC-006"]
    assert {p["part_number"] for p in reminders["DOC-008"]["affected_parts"]} == {"PRT-5003", "PRT-5004"}


def test_a_day_later_the_title_uses_the_singular(url):
    reminder = next(r for r in _reminders(url, as_of="2026-10-25") if r["document_id"] == "DOC-008")
    assert reminder["title"] == "Environmental declaration expires in 1 day"


def test_missing_and_pending_reminders(url):
    reminders = _reminders(url)
    missing = next(r for r in reminders if r["supplier_id"] == "SUP-106" and r["document_type"] == "quality_cert")
    assert missing["title"] == "No quality certificate on file"
    assert missing["affected_parts"][0]["part_number"] == "PRT-5005"
    pending = next(r for r in reminders if r["severity"] == "review")
    assert pending["document_id"] == "DOC-013"
    assert pending["title"] == "Safety certificate is waiting for approval"


def test_rejected_reminder_has_a_reason_and_handles_no_supplier(url):
    reminders = [r for r in _reminders(url) if r["severity"] == "unreadable"]
    with_supplier = next(r for r in reminders if r["document_id"] == "DOC-015")
    assert with_supplier["title"] == "DOC-015 could not be used: unknown status"
    assert with_supplier["draft"]
    no_supplier = next(r for r in reminders if r["document_id"] == "DOC-009")
    assert no_supplier["supplier_id"] == ""
    assert no_supplier["draft"] is None


def test_no_issues_means_no_reminders(url):
    assert _reminders(url, "no_issues") == []


# command line


def test_serve_rejects_a_bad_port(capsys):
    with pytest.raises(SystemExit) as error:
        main(["serve", "--port", "70000"])
    assert error.value.code == 2


def test_serve_reports_a_port_already_in_use(db_path, capsys):
    server = build_server("127.0.0.1", 0, DATA_DIR)
    try:
        port = str(server.server_address[1])
        assert main(["serve", "--port", port, "--data-dir", str(DATA_DIR)]) == 1
        assert port in capsys.readouterr().err
    finally:
        server.server_close()
