"""Backup the live compliance SQLite database.

Copies with sqlite3.Connection.backup(), then runs PRAGMA integrity_check on the
copy. Exits non-zero unless the check returns ok.

Retention: keep backups for 10 years (customer Q12). This script never prunes.

    python scripts/backup.py [--db PATH] [--out-dir PATH]
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = os.environ.get("COMPLIANCE_DB_PATH", "./data/compliance.db")
DEFAULT_OUT = Path("./data/backups")


def backup(db_path: Path, out_dir: Path) -> Path:
    """Copy db_path into out_dir as compliance-<UTC timestamp>.db and verify it."""
    if not db_path.is_file():
        raise FileNotFoundError(f"database not found: {db_path}")

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = out_dir / f"compliance-{stamp}.db"

    source = sqlite3.connect(db_path)
    try:
        copy = sqlite3.connect(dest)
        try:
            source.backup(copy)
        finally:
            copy.close()
    finally:
        source.close()

    check = sqlite3.connect(dest)
    try:
        result = check.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        check.close()

    if result != "ok":
        raise RuntimeError(f"integrity_check failed for {dest}: {result}")
    return dest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(DEFAULT_DB),
        help=f"live database (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT,
        help=f"directory for timestamped backups (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args(argv)

    try:
        dest = backup(args.db, args.out_dir)
    except FileNotFoundError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Backup written to {dest}")
    print("integrity_check: ok")
    print("Retention: keep backups for 10 years (customer Q12); this script does not prune.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
