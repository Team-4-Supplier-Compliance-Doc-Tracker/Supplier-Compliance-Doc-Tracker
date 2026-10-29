"""Restore a compliance SQLite backup over the live database path.

Copies the backup file back to COMPLIANCE_DB_PATH (or --db). Does not run the
tool; the next `compliance run` or `history` uses the restored file.

Retention of other backups is unchanged — keep for 10 years (customer Q12).

    python scripts/restore.py BACKUP_PATH [--db PATH]
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

DEFAULT_DB = os.environ.get("COMPLIANCE_DB_PATH", "./data/compliance.db")


def restore(backup_path: Path, db_path: Path) -> Path:
    """Copy backup_path onto db_path, creating parent directories as needed."""
    if not backup_path.is_file():
        raise FileNotFoundError(f"backup not found: {backup_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, db_path)
    return db_path


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
        dest = restore(args.backup, args.db)
    except FileNotFoundError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Restored {args.backup} -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
