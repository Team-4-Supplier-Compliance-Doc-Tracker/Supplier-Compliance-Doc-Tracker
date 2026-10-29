import json
from datetime import date

import pytest

from compliance.loader import load_documents, load_parts, read_json_list
from compliance.models import InputFileError, Part, SupplierDocument
from conftest import DOCUMENTS_JSON, PARTS_JSON


def write_json(tmp_path, content, name="documents.json"):
    path = tmp_path / name
    path.write_text(json.dumps(content))
    return path


def load_sample_documents(data_dir, settings):
    return load_documents(data_dir / "documents.json", settings)


def reasons_by_id(rejected):
    return {record.raw_id: record.reason for record in rejected}


# File-level failures

def test_documents_missing_file_raises(tmp_path):
    path = tmp_path / "missing.json"
    with pytest.raises(InputFileError) as error:
        read_json_list(path)
    assert str(path) in str(error.value)


def test_documents_invalid_json_raises(tmp_path):
    path = tmp_path / "documents.json"
    path.write_text('[{"document_id": "DOC-001",}')
    with pytest.raises(InputFileError) as error:
        read_json_list(path)
    assert str(path) in str(error.value)


def test_documents_wrong_top_level_shape_raises(tmp_path):
    path = write_json(tmp_path, {"document_id": "DOC-001"})
    with pytest.raises(InputFileError) as error:
        read_json_list(path)
    assert str(path) in str(error.value)


# Documents

def test_loads_clean_documents(data_dir, settings):
    clean, _ = load_sample_documents(data_dir, settings)
    by_id = {document.document_id: document for document in clean}
    for n in range(1, 9):
        assert f"DOC-00{n}" in by_id
    assert all(isinstance(document, SupplierDocument) for document in clean)
    assert by_id["DOC-005"].issue_date == date(2025, 6, 1)
    assert by_id["DOC-005"].expiry_date == date(2026, 6, 1)


def test_null_expiry_on_non_expiring_type_is_clean(data_dir, settings):
    clean, _ = load_sample_documents(data_dir, settings)
    doc_001 = next(document for document in clean if document.document_id == "DOC-001")
    assert doc_001.expiry_date is None


def test_null_expiry_on_expiring_type_is_rejected(data_dir, settings):
    _, rejected = load_sample_documents(data_dir, settings)
    assert reasons_by_id(rejected)["DOC-012"] == "invalid date"


def test_rejects_blank_supplier_id(data_dir, settings):
    _, rejected = load_sample_documents(data_dir, settings)
    assert reasons_by_id(rejected)["DOC-009"] == "missing supplier ID"


def test_rejects_null_and_absent_supplier_id(tmp_path, settings):
    base = {"document_type": "quality_cert", "issue_date": "2026-05-01", "expiry_date": None}
    path = write_json(tmp_path, [
        {"document_id": "DOC-NULL", "supplier_id": None, **base},
        {"document_id": "DOC-ABSENT", **base},
    ])
    clean, rejected = load_documents(path, settings)
    assert clean == []
    assert reasons_by_id(rejected) == {
        "DOC-NULL": "missing supplier ID",
        "DOC-ABSENT": "missing supplier ID",
    }


def test_rejects_unknown_document_type(data_dir, settings):
    _, rejected = load_sample_documents(data_dir, settings)
    assert reasons_by_id(rejected)["DOC-010"] == "unknown document type"


def test_rejects_invalid_date_string(data_dir, settings):
    _, rejected = load_sample_documents(data_dir, settings)
    assert reasons_by_id(rejected)["DOC-011"] == "invalid date"


def test_rejects_non_string_date(data_dir, settings):
    _, rejected = load_sample_documents(data_dir, settings)
    assert reasons_by_id(rejected)["DOC-011b"] == "invalid date"


def test_rejects_unknown_status(data_dir, settings):
    _, rejected = load_sample_documents(data_dir, settings)
    assert reasons_by_id(rejected)["DOC-015"] == "unknown status"


def test_status_defaults_to_approved(data_dir, settings):
    clean, _ = load_sample_documents(data_dir, settings)
    statuses = {document.document_id: document.status for document in clean}
    assert statuses["DOC-001"] == "approved"
    assert statuses["DOC-013"] == "pending"


def test_rejected_record_carries_index_and_id(data_dir, settings):
    _, rejected = load_sample_documents(data_dir, settings)
    doc_010 = next(record for record in rejected if record.raw_id == "DOC-010")
    assert doc_010.index == 10
    assert doc_010.source_file.endswith("documents.json")


def test_clean_and_rejected_counts_add_up(data_dir, settings):
    clean, rejected = load_sample_documents(data_dir, settings)
    assert len(clean) == 10
    assert len(rejected) == 7
    assert len(clean) + len(rejected) == len(DOCUMENTS_JSON)


# Parts

def test_loads_parts(data_dir, settings):
    clean, _ = load_parts(data_dir / "parts.json", settings)
    assert [part.part_number for part in clean] == [f"PRT-500{n}" for n in range(1, 7)]
    assert clean[1] == Part("PRT-5002", "Monitor power switch", "electrical", "SUP-102")
    assert len(PARTS_JSON) == 7


def test_rejects_part_with_unknown_category(data_dir, settings):
    _, rejected = load_parts(data_dir / "parts.json", settings)
    assert reasons_by_id(rejected) == {"PRT-5099": "unknown part category"}
