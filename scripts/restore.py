"""Restore a compliance SQLite backup over the live database path.

Verifies the backup with PRAGMA integrity_check before touching the live file.
If a live database already exists, copies it aside first as
compliance.db.before-restore-<UTC timestamp> so a bad restore cannot erase
auditor history.

    python scripts/restore.py BACKUP_PATH [--db PATH]
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = os.environ.get("COMPLIANCE_DB_PATH", "./data/compliance.db")


def _integrity_check(path: Path) -> str:
    try:
        conn = sqlite3.connect(path)
    except sqlite3.Error as error:
        raise RuntimeError(f"backup failed integrity_check: {error}") from error
    try:
        return conn.execute("PRAGMA integrity_check").fetchone()[0]
    except sqlite3.Error as error:
        raise RuntimeError(f"backup failed integrity_check: {error}") from error
    finally:
        conn.close()


def restore(backup_path: Path, db_path: Path) -> tuple[Path, Path | None]:
    """Copy a verified backup onto db_path.

    Returns (live_path, safety_copy_path_or_None).
    """
    if not backup_path.is_file():
        raise FileNotFoundError(f"backup not found: {backup_path}")

    result = _integrity_check(backup_path)
    if result != "ok":
        raise RuntimeError(f"backup failed integrity_check: {result}")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    safety: Path | None = None
    if db_path.is_file():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safety = db_path.with_name(f"{db_path.name}.before-restore-{stamp}")
        shutil.copy2(db_path, safety)

    shutil.copy2(backup_path, db_path)
    return db_path, safety


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("backup", type=Path, help="timestamped backup .db file")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(DEFAULT_DB),
        help=f"live database path to overwrite (default: {DEFAULT_DB})",
    )
    args = parser.parse_args(argv)

    try:
        dest, safety = restore(args.backup, args.db)
    except FileNotFoundError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except (RuntimeError, sqlite3.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if safety is not None:
        print(f"Live database saved aside as {safety}")
    print(f"Restored {args.backup} -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
