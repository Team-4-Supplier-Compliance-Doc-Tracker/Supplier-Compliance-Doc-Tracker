import dataclasses
import sqlite3
from datetime import date, datetime

import pytest

from compliance import storage
from compliance.models import AtRiskPart, Flag

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


# save_check / supplier_history / parts_at_risk

AS_OF = date(2026, 10, 26)

# Expected 1.0.0 output for the sample data on 2026-10-26 (plan.md section 3.2).
CHECK_FLAGS = [
    Flag("expired", "SUP-102", "safety_cert", "DOC-005", date(2026, 6, 1)),
    Flag("expiring_soon", "SUP-102", "env_declaration", "DOC-006", date(2026, 11, 20)),
    Flag("expiring_soon", "SUP-103", "env_declaration", "DOC-008", date(2026, 10, 26)),
    Flag("missing", "SUP-103", "safety_cert"),
    Flag("missing", "SUP-105", "env_declaration"),
    Flag("missing", "SUP-106", "quality_cert"),
    Flag("missing", "SUP-106", "env_declaration"),
]
CHECK_AT_RISK = [
    AtRiskPart("PRT-5002", "SUP-102", ("expired safety_cert",)),
    AtRiskPart("PRT-5003", "SUP-103", ("missing safety_cert",)),
    AtRiskPart("PRT-5005", "SUP-106", ("missing quality_cert", "missing env_declaration")),
    AtRiskPart("PRT-5006", "SUP-105", ("missing env_declaration",)),
]


@pytest.fixture
def seeded_path(tmp_db, sample_docs, sample_parts):
    path = _db_path(tmp_db)
    storage.save_documents(tmp_db, sample_docs)
    storage.save_parts(storage.connect(path), sample_parts)
    return path


def _save_check(path, flags=CHECK_FLAGS, at_risk=CHECK_AT_RISK, as_of=AS_OF, version="1.0.0"):
    return storage.save_check(storage.connect(path), as_of, version, flags, at_risk)


def test_save_check_stores_flags(seeded_path):
    check_id = _save_check(seeded_path)
    rows = _fetch(
        seeded_path,
        f"SELECT flag_type, supplier_id, document_type, document_id, expiry_date FROM flags WHERE check_id = {check_id}",
    )
    assert sorted(rows, key=str) == sorted(
        [
            (f.flag_type, f.supplier_id, f.document_type, f.document_id, f.expiry_date and f.expiry_date.isoformat())
            for f in CHECK_FLAGS
        ],
        key=str,
    )


def test_check_records_version_and_as_of(seeded_path):
    check_id = _save_check(seeded_path, version="1.1.0")
    [(as_of, version, run_at)] = _fetch(
        seeded_path, f"SELECT as_of_date, tool_version, run_at FROM compliance_checks WHERE check_id = {check_id}"
    )
    assert (as_of, version) == ("2026-10-26", "1.1.0")
    assert datetime.fromisoformat(run_at)


def test_missing_flag_has_null_document_id(seeded_path):
    _save_check(seeded_path)
    rows = _fetch(seeded_path, "SELECT document_id, expiry_date FROM flags WHERE flag_type = 'missing'")
    assert rows and all(row == (None, None) for row in rows)


def test_at_risk_parts_saved_per_check(seeded_path):
    first = _save_check(seeded_path)
    second = _save_check(seeded_path, at_risk=CHECK_AT_RISK[:1])
    rows = _fetch(seeded_path, "SELECT check_id, part_number, supplier_id FROM at_risk_parts ORDER BY check_id, part_number")
    assert rows == [
        (first, "PRT-5002", "SUP-102"),
        (first, "PRT-5003", "SUP-103"),
        (first, "PRT-5005", "SUP-106"),
        (first, "PRT-5006", "SUP-105"),
        (second, "PRT-5002", "SUP-102"),
    ]


def test_at_risk_part_with_two_reasons(seeded_path):
    _save_check(seeded_path)
    rows = _fetch(seeded_path, "SELECT reasons FROM at_risk_parts WHERE part_number = 'PRT-5005'")
    assert rows == [("missing quality_cert; missing env_declaration",)]


def test_save_check_upserts_supplier_from_flag(seeded_path):
    _save_check(seeded_path, flags=[Flag("missing", "SUP-999", "quality_cert")], at_risk=[])
    assert ("SUP-999",) in _fetch(seeded_path, "SELECT supplier_id FROM suppliers")


def test_failed_check_save_rolls_back(seeded_path):
    unsaved_part = AtRiskPart("PRT-NOPE", "SUP-102", ("expired safety_cert",))
    with pytest.raises(sqlite3.IntegrityError):
        _save_check(seeded_path, at_risk=CHECK_AT_RISK + [unsaved_part])
    assert _fetch(seeded_path, "SELECT COUNT(*) FROM compliance_checks") == [(0,)]
    assert _fetch(seeded_path, "SELECT COUNT(*) FROM flags") == [(0,)]
    assert _fetch(seeded_path, "SELECT COUNT(*) FROM at_risk_parts") == [(0,)]


def test_save_check_closes_connection(seeded_path):
    conn = storage.connect(seeded_path)
    storage.save_check(conn, AS_OF, "1.0.0", CHECK_FLAGS, CHECK_AT_RISK)
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_supplier_history_returns_all_checks_newest_first(seeded_path):
    first = _save_check(seeded_path)
    second = _save_check(seeded_path, flags=[Flag("missing", "SUP-103", "safety_cert")], at_risk=[], as_of=date(2026, 10, 27))
    history = storage.supplier_history(storage.connect(seeded_path), "SUP-103")
    assert [row["check_id"] for row in history] == [second, first, first]
    assert history[0] == {
        "check_id": second,
        "run_at": history[0]["run_at"],
        "as_of_date": "2026-10-27",
        "tool_version": "1.0.0",
        "flag_type": "missing",
        "document_type": "safety_cert",
        "document_id": None,
        "expiry_date": None,
    }
    assert {row["flag_type"] for row in history if row["check_id"] == first} == {"expiring_soon", "missing"}


def test_supplier_history_unknown_supplier_is_empty(seeded_path):
    _save_check(seeded_path)
    assert storage.supplier_history(storage.connect(seeded_path), "SUP-404") == []


def test_parts_at_risk_reflects_latest_check_only(seeded_path):
    _save_check(seeded_path)
    _save_check(seeded_path, at_risk=[CHECK_AT_RISK[1]])
    rows = storage.parts_at_risk(storage.connect(seeded_path))
    assert [(row["part_number"], row["description"], row["supplier_id"], row["reasons"]) for row in rows] == [
        ("PRT-5003", "Laptop cooling fan", "SUP-103", "missing safety_cert")
    ]


def test_parts_at_risk_empty_before_any_check(seeded_path):
    assert storage.parts_at_risk(storage.connect(seeded_path)) == []


def test_query_functions_close_connection(seeded_path):
    _save_check(seeded_path)
    for query in (lambda c: storage.supplier_history(c, "SUP-103"), storage.parts_at_risk):
        conn = storage.connect(seeded_path)
        query(conn)
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")
