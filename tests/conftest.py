# Shared fixtures. Sample data comes from plan.md sections 2.4 and 3.2.

import json
from datetime import date

import pytest

from compliance import storage
from compliance.models import Part, SupplierDocument
from compliance.settings import Settings

SETTINGS_JSON = {
    "today": "2026-10-26",
    "expiring_soon_days": 45,
    "document_types": ["quality_cert", "safety_cert", "env_declaration"],
    "expiring_types": ["safety_cert", "env_declaration"],
    "required_documents": {
        "cables": ["quality_cert", "safety_cert", "env_declaration"],
        "mechanical": ["quality_cert", "env_declaration"],
        "electrical": ["quality_cert", "safety_cert", "env_declaration"],
        "semiconductors": ["quality_cert", "env_declaration"],
    },
}

# DOC-009 to DOC-012 and DOC-015 are bad records; the rest are clean.
DOCUMENTS_JSON = [
    {"document_id": "DOC-001", "supplier_id": "SUP-101", "document_type": "quality_cert", "issue_date": "2024-01-15", "expiry_date": None},
    {"document_id": "DOC-002", "supplier_id": "SUP-101", "document_type": "safety_cert", "issue_date": "2026-03-01", "expiry_date": "2027-03-01"},
    {"document_id": "DOC-003", "supplier_id": "SUP-101", "document_type": "env_declaration", "issue_date": "2026-02-10", "expiry_date": "2027-02-10"},
    {"document_id": "DOC-004", "supplier_id": "SUP-102", "document_type": "quality_cert", "issue_date": "2023-06-01", "expiry_date": None},
    {"document_id": "DOC-005", "supplier_id": "SUP-102", "document_type": "safety_cert", "issue_date": "2025-06-01", "expiry_date": "2026-06-01"},
    {"document_id": "DOC-006", "supplier_id": "SUP-102", "document_type": "env_declaration", "issue_date": "2025-11-20", "expiry_date": "2026-11-20"},
    {"document_id": "DOC-007", "supplier_id": "SUP-103", "document_type": "quality_cert", "issue_date": "2024-04-05", "expiry_date": None},
    {"document_id": "DOC-008", "supplier_id": "SUP-103", "document_type": "env_declaration", "issue_date": "2025-10-26", "expiry_date": "2026-10-26"},
    {"document_id": "DOC-009", "supplier_id": "", "document_type": "quality_cert", "issue_date": "2026-05-01", "expiry_date": None},
    {"document_id": "DOC-009b", "document_type": "quality_cert", "issue_date": "2026-05-01", "expiry_date": None},
    {"document_id": "DOC-010", "supplier_id": "SUP-104", "document_type": "iso_badge", "issue_date": "2026-05-01", "expiry_date": "2027-05-01"},
    {"document_id": "DOC-011", "supplier_id": "SUP-104", "document_type": "safety_cert", "issue_date": "2026-13-45", "expiry_date": "2027-01-01"},
    {"document_id": "DOC-011b", "supplier_id": "SUP-104", "document_type": "safety_cert", "issue_date": "2026-01-01", "expiry_date": 20270101},
    {"document_id": "DOC-012", "supplier_id": "SUP-104", "document_type": "safety_cert", "issue_date": "2026-01-01", "expiry_date": None},
    {"document_id": "DOC-013", "supplier_id": "SUP-105", "document_type": "safety_cert", "issue_date": "2026-09-01", "expiry_date": "2027-09-01", "status": "pending"},
    {"document_id": "DOC-014", "supplier_id": "SUP-105", "document_type": "quality_cert", "issue_date": "2024-09-01", "expiry_date": None},
    {"document_id": "DOC-015", "supplier_id": "SUP-105", "document_type": "env_declaration", "issue_date": "2026-09-01", "expiry_date": "2027-09-01", "status": "maybe"},
]

# PRT-5099 is a bad record (unknown category "seal").
PARTS_JSON = [
    {"part_number": "PRT-5001", "description": "AC power cord", "part_category": "cables", "supplier_id": "SUP-101"},
    {"part_number": "PRT-5002", "description": "Monitor power switch", "part_category": "electrical", "supplier_id": "SUP-102"},
    {"part_number": "PRT-5003", "description": "Laptop cooling fan", "part_category": "electrical", "supplier_id": "SUP-103"},
    {"part_number": "PRT-5004", "description": "Laptop motherboard", "part_category": "semiconductors", "supplier_id": "SUP-103"},
    {"part_number": "PRT-5005", "description": "Chassis hinge", "part_category": "mechanical", "supplier_id": "SUP-106"},
    {"part_number": "PRT-5006", "description": "Display panel", "part_category": "electrical", "supplier_id": "SUP-105"},
    {"part_number": "PRT-5099", "description": "Rubber gasket", "part_category": "seal", "supplier_id": "SUP-101"},
]

CLEAN_DOCUMENT_IDS = {f"DOC-00{n}" for n in range(1, 9)} | {"DOC-013", "DOC-014"}
CLEAN_PART_NUMBERS = {f"PRT-500{n}" for n in range(1, 7)}


def _date_or_none(value):
    return date.fromisoformat(value) if value is not None else None


@pytest.fixture
def today():
    return date(2026, 10, 26)


@pytest.fixture
def settings():
    return Settings(
        today=date.fromisoformat(SETTINGS_JSON["today"]),
        expiring_soon_days=SETTINGS_JSON["expiring_soon_days"],
        document_types=tuple(SETTINGS_JSON["document_types"]),
        expiring_types=tuple(SETTINGS_JSON["expiring_types"]),
        required_documents={
            category: tuple(types)
            for category, types in SETTINGS_JSON["required_documents"].items()
        },
    )


@pytest.fixture
def sample_docs():
    return [
        SupplierDocument(
            document_id=record["document_id"],
            supplier_id=record["supplier_id"],
            document_type=record["document_type"],
            issue_date=date.fromisoformat(record["issue_date"]),
            expiry_date=_date_or_none(record["expiry_date"]),
            status=record.get("status", "approved"),
        )
        for record in DOCUMENTS_JSON
        if record["document_id"] in CLEAN_DOCUMENT_IDS
    ]


@pytest.fixture
def sample_parts():
    return [Part(**record) for record in PARTS_JSON if record["part_number"] in CLEAN_PART_NUMBERS]


@pytest.fixture
def tmp_db(tmp_path):
    conn = storage.connect(tmp_path / "test.db")
    storage.init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def data_dir(tmp_path):
    for name, content in [
        ("documents.json", DOCUMENTS_JSON),
        ("parts.json", PARTS_JSON),
        ("settings.json", SETTINGS_JSON),
    ]:
        (tmp_path / name).write_text(json.dumps(content, indent=2))
    return tmp_path
