import json
import os
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from compliance import __version__
from compliance.cli import main
from conftest import SETTINGS_JSON

SRC = Path(__file__).resolve().parents[1] / "src"


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "db" / "compliance.db"
    monkeypatch.setenv("COMPLIANCE_DB_PATH", str(path))
    return path


def _run_args(data_dir, *extra):
    return [
        "run",
        "--documents", str(data_dir / "documents.json"),
        "--parts", str(data_dir / "parts.json"),
        "--settings", str(data_dir / "settings.json"),
        *extra,
    ]


def _fetch(path, sql):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


# run


def test_run_end_to_end_writes_db_and_prints_report(data_dir, db_path, capsys):
    assert main(_run_args(data_dir)) == 0
    out = capsys.readouterr().out
    assert f"Compliance report as of 2026-10-26 (tool {__version__}, check 1)" in out
    assert "SUP-102  safety_cert  2026-06-01  DOC-005" in out
    assert "PRT-5005  SUP-106  missing quality_cert; missing env_declaration" in out
    assert "PRT-5099  unknown part category" in out
    assert _fetch(db_path, "SELECT as_of_date, tool_version FROM compliance_checks") == [("2026-10-26", __version__)]
    assert _fetch(db_path, "SELECT COUNT(*) FROM flags") == [(7,)]
    parts = {row[0] for row in _fetch(db_path, "SELECT part_number FROM at_risk_parts")}
    assert parts == {"PRT-5002", "PRT-5003", "PRT-5005", "PRT-5006"}


def test_run_prints_summary_line_under_header(data_dir, db_path, capsys):
    main(_run_args(data_dir))
    lines = capsys.readouterr().out.splitlines()
    assert lines[1] == "Checked 5 suppliers and 6 parts: 1 supplier with no issues, 4 parts at risk, 7 flags, 8 rejected records"


def test_run_summary_on_a_day_with_no_issues(data_dir, db_path, capsys):
    # Only SUP-101, which holds every document a cable needs: nothing to flag, nothing rejected.
    documents = json.loads((data_dir / "documents.json").read_text())
    parts = json.loads((data_dir / "parts.json").read_text())
    (data_dir / "documents.json").write_text(json.dumps([d for d in documents if d.get("supplier_id") == "SUP-101"]))
    (data_dir / "parts.json").write_text(json.dumps([p for p in parts if p["part_number"] == "PRT-5001"]))
    main(_run_args(data_dir))
    out = capsys.readouterr().out
    assert "Checked 1 supplier and 1 part: 1 supplier with no issues, 0 parts at risk, 0 flags, 0 rejected records" in out
    assert "No issues found" in out


def test_run_twice_keeps_one_copy_of_inputs_and_two_checks(data_dir, db_path, capsys):
    assert main(_run_args(data_dir)) == 0
    assert main(_run_args(data_dir)) == 0
    assert _fetch(db_path, "SELECT COUNT(*) FROM compliance_checks") == [(2,)]
    assert _fetch(db_path, "SELECT COUNT(*) FROM documents") == [(10,)]
    assert _fetch(db_path, "SELECT COUNT(*) FROM parts") == [(6,)]


def test_run_respects_env_db_path(data_dir, tmp_path, monkeypatch, capsys):
    target = tmp_path / "elsewhere" / "custom.db"
    monkeypatch.setenv("COMPLIANCE_DB_PATH", str(target))
    assert main(_run_args(data_dir)) == 0
    assert target.exists()


def test_today_precedence(data_dir, db_path, capsys):
    # --today beats settings.today, which beats the system date.
    assert main(_run_args(data_dir, "--today", "2026-01-01")) == 0
    assert main(_run_args(data_dir)) == 0
    (data_dir / "settings.json").write_text(json.dumps({**SETTINGS_JSON, "today": None}))
    assert main(_run_args(data_dir)) == 0
    rows = _fetch(db_path, "SELECT as_of_date FROM compliance_checks ORDER BY check_id")
    assert rows == [("2026-01-01",), ("2026-10-26",), (date.today().isoformat(),)]


def test_invalid_today_option_is_a_usage_error(data_dir, db_path, capsys):
    with pytest.raises(SystemExit) as error:
        main(_run_args(data_dir, "--today", "26/10/2026"))
    assert error.value.code == 2


def test_missing_input_file_exits_nonzero(data_dir, db_path, capsys):
    missing = data_dir / "nope.json"
    args = _run_args(data_dir)
    args[args.index("--documents") + 1] = str(missing)
    assert main(args) == 1
    assert str(missing) in capsys.readouterr().err
    assert not db_path.exists()


def test_invalid_json_exits_nonzero(data_dir, db_path, capsys):
    (data_dir / "parts.json").write_text('[{"part_number": "PRT-5001",}')
    assert main(_run_args(data_dir)) == 1
    assert "parts.json" in capsys.readouterr().err
    assert not db_path.exists()


# history


def test_history_subcommand(data_dir, db_path, capsys):
    main(_run_args(data_dir))
    main(_run_args(data_dir, "--today", "2026-12-31"))
    capsys.readouterr()
    assert main(["history", "SUP-103"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "History for SUP-103"
    checks = [line for line in lines if line.startswith("Check ")]
    assert [line.split()[1] for line in checks] == ["2", "1"]
    assert "as of 2026-12-31" in checks[0]
    assert "  missing  safety_cert  —" in lines
    assert "  expiring_soon  env_declaration  2026-10-26  DOC-008" in lines


def test_history_known_supplier_without_flags(data_dir, db_path, capsys):
    main(_run_args(data_dir))
    capsys.readouterr()
    assert main(["history", "SUP-101"]) == 0
    assert capsys.readouterr().out == "History for SUP-101\n  no flags in any saved check\n"


def test_history_unknown_supplier(db_path, capsys):
    assert main(["history", "SUP-404"]) == 0
    assert capsys.readouterr().out == (
        "History for SUP-404\n  no saved record of this supplier (rejected documents are not stored)\n"
    )


def test_history_supplier_whose_documents_were_all_rejected(data_dir, db_path, capsys):
    # SUP-104 is in documents.json, but every one of its documents is rejected, so nothing is saved.
    main(_run_args(data_dir))
    capsys.readouterr()
    assert main(["history", "SUP-104"]) == 0
    assert "no saved record of this supplier (rejected documents are not stored)" in capsys.readouterr().out


# entry point


def test_module_entry_point_forwards_args(data_dir, db_path):
    env = {**os.environ, "PYTHONPATH": str(SRC), "COMPLIANCE_DB_PATH": str(db_path)}
    result = subprocess.run(
        [sys.executable, "-m", "compliance", *_run_args(data_dir, "--today", "2026-10-26")],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "Parts at risk" in result.stdout
