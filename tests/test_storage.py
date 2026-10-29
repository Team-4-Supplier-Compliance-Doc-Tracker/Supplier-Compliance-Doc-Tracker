import dataclasses
import sqlite3

import pytest

from compliance import storage

TABLES = {"suppliers", "parts", "documents", "compliance_checks", "flags", "at_risk_parts"}


def _db_path(conn):
    return conn.execute("PRAGMA database_list").fetchone()[2]


def _fetch(path, sql):
    conn = storage.connect(path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def _table_names(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
    return {row[0] for row in rows}


# connect / init_schema


def test_schema_creates_all_tables(tmp_db):
    assert _table_names(tmp_db) == TABLES


def test_schema_is_idempotent(tmp_db):
    storage.init_schema(tmp_db)
    storage.init_schema(tmp_db)
    assert _table_names(tmp_db) == TABLES


def test_foreign_keys_enabled(tmp_db):
    assert tmp_db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        tmp_db.execute(
            "INSERT INTO parts (part_number, description, part_category, supplier_id) VALUES ('P', 'd', 'c', 'NOPE')"
        )


def test_connect_uses_env_path(tmp_path, monkeypatch):
    target = tmp_path / "from_env.db"
    monkeypatch.setenv("COMPLIANCE_DB_PATH", str(target))
    storage.connect().close()
    assert target.exists()


def test_connect_defaults_to_data_dir_and_creates_it(tmp_path, monkeypatch):
    monkeypatch.delenv("COMPLIANCE_DB_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    storage.connect().close()
    assert (tmp_path / "data" / "compliance.db").exists()


# save_documents


def test_save_documents_inserts_batch(tmp_db, sample_docs):
    path = _db_path(tmp_db)
    storage.save_documents(tmp_db, sample_docs)
    assert _fetch(path, "SELECT COUNT(*) FROM documents") == [(len(sample_docs),)]
    suppliers = {row[0] for row in _fetch(path, "SELECT supplier_id FROM suppliers")}
    assert suppliers == {"SUP-101", "SUP-102", "SUP-103", "SUP-105"}


def test_save_documents_stores_iso_dates(tmp_db, sample_docs):
    path = _db_path(tmp_db)
    storage.save_documents(tmp_db, sample_docs)
    rows = _fetch(path, "SELECT issue_date, expiry_date FROM documents WHERE document_id = 'DOC-002'")
    assert rows == [("2026-03-01", "2027-03-01")]


def test_save_documents_stores_null_expiry(tmp_db, sample_docs):
    path = _db_path(tmp_db)
    storage.save_documents(tmp_db, sample_docs)
    rows = _fetch(path, "SELECT expiry_date FROM documents WHERE document_id = 'DOC-001'")
    assert rows == [(None,)]


def test_save_documents_stores_status(tmp_db, sample_docs):
    path = _db_path(tmp_db)
    storage.save_documents(tmp_db, sample_docs)
    rows = dict(_fetch(path, "SELECT document_id, status FROM documents WHERE document_id IN ('DOC-001', 'DOC-013')"))
    assert rows == {"DOC-001": "approved", "DOC-013": "pending"}


def test_save_documents_skips_duplicate_id(tmp_db, sample_docs):
    path = _db_path(tmp_db)
    storage.save_documents(tmp_db, sample_docs)
    again = storage.connect(path)
    storage.save_documents(again, sample_docs + sample_docs[:2])
    assert _fetch(path, "SELECT COUNT(*) FROM documents") == [(len(sample_docs),)]


def test_failed_document_save_rolls_back(tmp_db, sample_docs):
    path = _db_path(tmp_db)
    broken = dataclasses.replace(sample_docs[0], document_id="DOC-BAD", issue_date=None)
    with pytest.raises(sqlite3.IntegrityError):
        storage.save_documents(tmp_db, sample_docs[:2] + [broken])
    assert _fetch(path, "SELECT COUNT(*) FROM documents") == [(0,)]
    assert _fetch(path, "SELECT COUNT(*) FROM suppliers") == [(0,)]


def test_connection_closed_after_save(tmp_db, sample_docs):
    storage.save_documents(tmp_db, sample_docs)
    with pytest.raises(sqlite3.ProgrammingError):
        tmp_db.execute("SELECT 1")


# save_parts


def test_save_parts_inserts_batch(tmp_db, sample_parts):
    path = _db_path(tmp_db)
    storage.save_parts(tmp_db, sample_parts)
    assert _fetch(path, "SELECT COUNT(*) FROM parts") == [(len(sample_parts),)]
    rows = _fetch(path, "SELECT description, part_category, supplier_id FROM parts WHERE part_number = 'PRT-5003'")
    assert rows == [("Laptop cooling fan", "electrical", "SUP-103")]


def test_save_parts_upserts_supplier_known_only_via_part(tmp_db, sample_parts):
    path = _db_path(tmp_db)
    storage.save_parts(tmp_db, sample_parts)
    assert ("SUP-106",) in _fetch(path, "SELECT supplier_id FROM suppliers")


def test_save_parts_skips_duplicate_part_number(tmp_db, sample_parts):
    path = _db_path(tmp_db)
    storage.save_parts(tmp_db, sample_parts)
    again = storage.connect(path)
    storage.save_parts(again, sample_parts + sample_parts[:2])
    assert _fetch(path, "SELECT COUNT(*) FROM parts") == [(len(sample_parts),)]


def test_save_parts_rolls_back(tmp_db, sample_parts):
    path = _db_path(tmp_db)
    broken = dataclasses.replace(sample_parts[0], part_number="PRT-BAD", description=None)
    with pytest.raises(sqlite3.IntegrityError):
        storage.save_parts(tmp_db, sample_parts[:2] + [broken])
    assert _fetch(path, "SELECT COUNT(*) FROM parts") == [(0,)]
    assert _fetch(path, "SELECT COUNT(*) FROM suppliers") == [(0,)]


def test_save_parts_closes_connection(tmp_db, sample_parts):
    storage.save_parts(tmp_db, sample_parts)
    with pytest.raises(sqlite3.ProgrammingError):
        tmp_db.execute("SELECT 1")
