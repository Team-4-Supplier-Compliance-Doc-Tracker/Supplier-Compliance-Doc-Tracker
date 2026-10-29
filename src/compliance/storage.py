# SQLite storage. Implemented in DB-01 and DB-02.

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH_ENV = "COMPLIANCE_DB_PATH"
DEFAULT_DB_PATH = "./data/compliance.db"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(db_path=None) -> sqlite3.Connection:
    # Open a connection with PRAGMA foreign_keys = ON. Without an argument the path comes from
    # COMPLIANCE_DB_PATH, falling back to ./data/compliance.db. The parent directory is created.
    path = Path(db_path or os.environ.get(DB_PATH_ENV) or DEFAULT_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn) -> None:
    conn.executescript(SCHEMA_PATH.read_text())


def _iso(value):
    return value.isoformat() if value is not None else None


def save_documents(conn, documents) -> None:
    # Upsert suppliers and insert documents in one transaction; existing document_id is skipped.
    # Closes the connection on return.
    try:
        with conn:
            conn.executemany(
                "INSERT INTO suppliers (supplier_id) VALUES (?) ON CONFLICT DO NOTHING",
                [(doc.supplier_id,) for doc in documents],
            )
            conn.executemany(
                "INSERT INTO documents (document_id, supplier_id, document_type, issue_date, expiry_date, status)"
                " VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (document_id) DO NOTHING",
                [
                    (
                        doc.document_id,
                        doc.supplier_id,
                        doc.document_type,
                        _iso(doc.issue_date),
                        _iso(doc.expiry_date),
                        doc.status,
                    )
                    for doc in documents
                ],
            )
    finally:
        conn.close()


def save_parts(conn, parts) -> None:
    # Upsert suppliers and insert parts in one transaction; existing part_number is skipped.
    # Closes the connection on return.
    try:
        with conn:
            conn.executemany(
                "INSERT INTO suppliers (supplier_id) VALUES (?) ON CONFLICT DO NOTHING",
                [(part.supplier_id,) for part in parts],
            )
            conn.executemany(
                "INSERT INTO parts (part_number, description, part_category, supplier_id)"
                " VALUES (?, ?, ?, ?) ON CONFLICT (part_number) DO NOTHING",
                [(part.part_number, part.description, part.part_category, part.supplier_id) for part in parts],
            )
    finally:
        conn.close()


def save_check(conn, as_of, version, flags, at_risk) -> int:
    # Save one compliance check, its flags and its at-risk parts in one transaction. Returns check_id.
    # Suppliers referenced only by a flag are upserted first. Closes the connection on return.
    run_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        with conn:
            conn.executemany(
                "INSERT INTO suppliers (supplier_id) VALUES (?) ON CONFLICT DO NOTHING",
                [(item.supplier_id,) for item in [*flags, *at_risk]],
            )
            check_id = conn.execute(
                "INSERT INTO compliance_checks (run_at, as_of_date, tool_version) VALUES (?, ?, ?)",
                (run_at, _iso(as_of), version),
            ).lastrowid
            conn.executemany(
                "INSERT INTO flags (check_id, flag_type, supplier_id, document_id, document_type, expiry_date)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        check_id,
                        flag.flag_type,
                        flag.supplier_id,
                        flag.document_id,
                        flag.document_type,
                        _iso(flag.expiry_date),
                    )
                    for flag in flags
                ],
            )
            conn.executemany(
                "INSERT INTO at_risk_parts (check_id, part_number, supplier_id, reasons) VALUES (?, ?, ?, ?)",
                [(check_id, part.part_number, part.supplier_id, "; ".join(part.reasons)) for part in at_risk],
            )
        return check_id
    finally:
        conn.close()


def _query(conn, sql, params):
    # Run a read query and return plain dicts. Closes the connection on return.
    try:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(sql, params)]
    finally:
        conn.close()


def supplier_history(conn, supplier_id) -> list[dict]:
    # One dict per flag the supplier had, newest check first.
    return _query(
        conn,
        "SELECT c.check_id, c.run_at, c.as_of_date, c.tool_version,"
        " f.flag_type, f.document_type, f.document_id, f.expiry_date"
        " FROM flags f JOIN compliance_checks c ON c.check_id = f.check_id"
        " WHERE f.supplier_id = ?"
        " ORDER BY c.check_id DESC, f.flag_type, f.document_type",
        (supplier_id,),
    )


def parts_at_risk(conn) -> list[dict]:
    # At-risk parts from the latest check only, with the part description.
    return _query(
        conn,
        "SELECT a.check_id, a.part_number, p.description, a.supplier_id, a.reasons"
        " FROM at_risk_parts a JOIN parts p ON p.part_number = a.part_number"
        " WHERE a.check_id = (SELECT MAX(check_id) FROM compliance_checks)"
        " ORDER BY a.part_number",
        (),
    )
