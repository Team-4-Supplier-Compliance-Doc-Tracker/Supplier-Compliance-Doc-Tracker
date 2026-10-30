# REL-01: backup uses Connection.backup + integrity_check; restore copies the file back (R19).

import sqlite3
import subprocess
import sys
from pathlib import Path

from compliance import storage

ROOT = Path(__file__).resolve().parents[1]
BACKUP_SCRIPT = ROOT / "scripts" / "backup.py"
RESTORE_SCRIPT = ROOT / "scripts" / "restore.py"


def _seed_db(path, sample_docs):
    conn = storage.connect(path)
    storage.init_schema(conn)
    storage.save_documents(conn, sample_docs)


def _run(script, *args):
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
    )


def test_backup_passes_integrity_check(tmp_path, sample_docs):
    live = tmp_path / "compliance.db"
    _seed_db(live, sample_docs)
    out_dir = tmp_path / "backups"

    result = _run(BACKUP_SCRIPT, "--db", str(live), "--out-dir", str(out_dir))
    assert result.returncode == 0, result.stderr
    assert "integrity_check: ok" in result.stdout
    assert "10 years" in result.stdout

    backups = sorted(out_dir.glob("compliance-*.db"))
    assert len(backups) == 1
    conn = sqlite3.connect(backups[0])
    try:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        ids = {row[0] for row in conn.execute("SELECT document_id FROM documents")}
    finally:
        conn.close()
    assert "DOC-001" in ids
    assert "DOC-005" in ids


def test_restore_round_trip(tmp_path, sample_docs):
    live = tmp_path / "compliance.db"
    _seed_db(live, sample_docs)
    out_dir = tmp_path / "backups"

    assert _run(BACKUP_SCRIPT, "--db", str(live), "--out-dir", str(out_dir)).returncode == 0
    backup_file = next(out_dir.glob("compliance-*.db"))

    before = {
        row[0]
        for row in sqlite3.connect(live).execute("SELECT document_id FROM documents")
    }
    live.unlink()
    assert not live.exists()

    result = _run(RESTORE_SCRIPT, str(backup_file), "--db", str(live))
    assert result.returncode == 0, result.stderr
    assert live.exists()

    after = {
        row[0]
        for row in sqlite3.connect(live).execute("SELECT document_id FROM documents")
    }
    assert after == before
    assert sqlite3.connect(live).execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_restore_refuses_corrupt_backup_and_keeps_live(tmp_path, sample_docs):
    live = tmp_path / "compliance.db"
    _seed_db(live, sample_docs)
    before = live.read_bytes()

    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(before[:64])  # truncated → malformed SQLite file

    result = _run(RESTORE_SCRIPT, str(corrupt), "--db", str(live))
    assert result.returncode != 0
    assert "integrity_check" in result.stderr
    assert live.read_bytes() == before
    assert not list(tmp_path.glob("*.before-restore-*"))


def test_restore_saves_live_aside_before_overwrite(tmp_path, sample_docs):
    live = tmp_path / "compliance.db"
    _seed_db(live, sample_docs)
    out_dir = tmp_path / "backups"
    assert _run(BACKUP_SCRIPT, "--db", str(live), "--out-dir", str(out_dir)).returncode == 0
    backup_file = next(out_dir.glob("compliance-*.db"))

    # Change the live DB so the safety copy is distinguishable from the restore.
    conn = sqlite3.connect(live)
    conn.execute("DELETE FROM documents WHERE document_id = 'DOC-005'")
    conn.commit()
    conn.close()
    assert "DOC-005" not in {
        row[0] for row in sqlite3.connect(live).execute("SELECT document_id FROM documents")
    }

    result = _run(RESTORE_SCRIPT, str(backup_file), "--db", str(live))
    assert result.returncode == 0, result.stderr
    assert "before-restore" in result.stdout

    safety = next(tmp_path.glob("compliance.db.before-restore-*"))
    safety_ids = {
        row[0] for row in sqlite3.connect(safety).execute("SELECT document_id FROM documents")
    }
    restored_ids = {
        row[0] for row in sqlite3.connect(live).execute("SELECT document_id FROM documents")
    }
    assert "DOC-005" not in safety_ids
    assert "DOC-005" in restored_ids
