# REL-01: full tool on synthetic files (generator → CLI → report + DB).
# Ticket called for xfail(strict=True) until CLI-01; CLI-01 is already on main, so this runs.

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from conftest import SETTINGS_JSON

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
GENERATE = ROOT / "scripts" / "generate_data.py"

# Edge-case sample on 2026-10-26: expired + expiring_soon + missing = 7 flags (filler suppliers are clean).
EXPECTED_FLAG_COUNT = 7


def test_full_tool_on_synthetic_files(tmp_path):
    out = tmp_path / "data"
    db_path = tmp_path / "compliance.db"
    (tmp_path / "settings.json").write_text(json.dumps(SETTINGS_JSON, indent=2))

    gen = subprocess.run(
        [sys.executable, str(GENERATE), "--out", str(out), "--seed", "42"],
        capture_output=True,
        text=True,
    )
    assert gen.returncode == 0, gen.stderr

    # Generator writes documents + parts only; settings come from the shared fixture shape.
    settings_path = tmp_path / "settings.json"
    env = {
        **os.environ,
        "PYTHONPATH": str(SRC),
        "COMPLIANCE_DB_PATH": str(db_path),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "compliance",
            "run",
            "--documents",
            str(out / "documents.json"),
            "--parts",
            str(out / "parts.json"),
            "--settings",
            str(settings_path),
            "--today",
            "2026-10-26",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    report = result.stdout

    assert "Expired" in report
    assert "Expiring soon" in report
    assert "Missing" in report
    assert "DOC-005" in report
    assert "PRT-5002" in report
    assert "PRT-5003" in report
    assert "PRT-5005" in report
    assert "PRT-5004" not in report.split("Parts at risk")[-1].split("Rejected records")[0]

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM compliance_checks").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM flags").fetchone()[0] == EXPECTED_FLAG_COUNT
        at_risk = {
            row[0] for row in conn.execute("SELECT part_number FROM at_risk_parts")
        }
    finally:
        conn.close()

    assert {"PRT-5002", "PRT-5003", "PRT-5005"} <= at_risk
    assert "PRT-5004" not in at_risk
