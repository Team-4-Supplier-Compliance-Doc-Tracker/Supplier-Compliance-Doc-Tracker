from datetime import date

from compliance.models import AtRiskPart, Flag, RejectedRecord
from compliance.report import render_report


def _expired():
    return Flag("expired", "SUP-102", "safety_cert", "DOC-005", date(2026, 6, 1))


def _expiring():
    return Flag("expiring_soon", "SUP-102", "env_declaration", "DOC-006", date(2026, 11, 20))


def _missing():
    return Flag("missing", "SUP-103", "safety_cert")


def _lines(report):
    return [line.strip() for line in report.splitlines()]


def test_report_groups_flags_by_type():
    lines = _lines(render_report([_missing(), _expiring(), _expired()], [], []))
    expected = [
        "Expired",
        "SUP-102  safety_cert  2026-06-01  DOC-005",
        "Expiring soon",
        "SUP-102  env_declaration  2026-11-20  DOC-006",
        "Missing",
        "SUP-103  safety_cert  —",
    ]
    positions = [lines.index(line) for line in expected]
    assert positions == sorted(positions)


def test_report_lists_supplier_type_expiry():
    report = render_report([_expired()], [], [])
    assert "SUP-102  safety_cert  2026-06-01" in report


def test_report_shows_document_id_when_flag_has_one():
    lines = _lines(render_report([_expired(), _missing()], [], []))
    assert "SUP-102  safety_cert  2026-06-01  DOC-005" in lines
    assert "SUP-103  safety_cert  —" in lines


def test_report_shows_dash_for_null_expiry():
    report = render_report([_missing()], [], [])
    assert "SUP-103  safety_cert  —" in report


def test_report_sorts_by_supplier_then_type():
    flags = [
        Flag("missing", "SUP-106", "quality_cert"),
        Flag("missing", "SUP-103", "safety_cert"),
        Flag("missing", "SUP-106", "env_declaration"),
    ]
    lines = [line for line in _lines(render_report(flags, [], [])) if line.startswith("SUP-")]
    assert lines == [
        "SUP-103  safety_cert  —",
        "SUP-106  env_declaration  —",
        "SUP-106  quality_cert  —",
    ]


def test_report_lists_at_risk_parts():
    at_risk = [
        AtRiskPart("PRT-5005", "SUP-106", ("missing quality_cert", "missing env_declaration")),
        AtRiskPart("PRT-5003", "SUP-103", ("missing safety_cert",)),
    ]
    report = render_report([_missing()], at_risk, [])
    assert "Parts at risk" in report
    lines = _lines(report)
    assert "PRT-5003  SUP-103  missing safety_cert" in lines
    assert "PRT-5005  SUP-106  missing quality_cert; missing env_declaration" in lines
    assert lines.index("PRT-5003  SUP-103  missing safety_cert") < lines.index(
        "PRT-5005  SUP-106  missing quality_cert; missing env_declaration"
    )


def test_report_lists_rejected_records():
    rejected = [
        RejectedRecord("documents.json", 8, "DOC-009", "missing supplier ID"),
        RejectedRecord("parts.json", 6, "PRT-5099", "unknown part category"),
        RejectedRecord("documents.json", 9, "", "invalid date"),
    ]
    report = render_report([], [], rejected)
    lines = _lines(report)
    assert "Rejected records" in report
    assert "DOC-009  missing supplier ID" in lines
    assert "PRT-5099  unknown part category" in lines
    assert "documents.json[9]  invalid date" in lines


def test_report_no_flags():
    report = render_report([], [], [RejectedRecord("documents.json", 0, "DOC-009", "invalid date")])
    assert "No issues found" in report
    assert "Expired" not in report
    assert "Parts at risk" not in report
    assert "DOC-009  invalid date" in _lines(report)


def test_report_no_flags_and_nothing_rejected_still_prints_section():
    report = render_report([], [], [])
    assert "No issues found" in report
    assert "Rejected records" in report


def test_report_is_plain_text():
    report = render_report([_expired(), _missing()], [AtRiskPart("PRT-5002", "SUP-102", ("expired safety_cert",))], [])
    assert "\x1b" not in report
    assert isinstance(report, str)
    assert report.endswith("\n")


def test_report_tolerates_unknown_flag_type():
    flags = [_expired(), Flag("pending", "SUP-105", "safety_cert", "DOC-013", date(2027, 9, 1))]
    report = render_report(flags, [], [])
    assert "Other" in report
    assert "SUP-105  safety_cert  2027-09-01  DOC-013  (pending)" in _lines(report)
    assert report.index("Expired") < report.index("Other")
