# SQLite storage. Implemented in DB-01 and DB-02.

import sqlite3


def connect(db_path) -> sqlite3.Connection:
    # Open a connection with PRAGMA foreign_keys = ON.
    raise NotImplementedError


def init_schema(conn) -> None:
    raise NotImplementedError


def save_documents(conn, documents) -> None:
    # Upsert suppliers and insert documents in one transaction; existing document_id is skipped.
    raise NotImplementedError


def save_check(conn, as_of, version, flags, at_risk) -> int:
    # Save one compliance check and all its flags in one transaction. Returns check_id.
    raise NotImplementedError


def supplier_history(conn, supplier_id) -> list[dict]:
    raise NotImplementedError


def parts_at_risk(conn) -> list[dict]:
    raise NotImplementedError
