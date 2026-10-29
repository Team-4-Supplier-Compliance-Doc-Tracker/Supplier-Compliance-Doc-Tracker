# SQLite storage. Implemented in DB-01 and DB-02.

import os
import sqlite3
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
    raise NotImplementedError


def supplier_history(conn, supplier_id) -> list[dict]:
    raise NotImplementedError


def parts_at_risk(conn) -> list[dict]:
    raise NotImplementedError
