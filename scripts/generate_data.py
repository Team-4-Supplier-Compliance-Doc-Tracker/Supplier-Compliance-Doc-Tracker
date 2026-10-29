"""Write synthetic documents.json and parts.json for the compliance tracker.

The edge cases from plan.md section 3.2 are written exactly, so tests and the
demo can name them. Faker then adds a few fully compliant filler suppliers,
seeded, so two runs with the same seed give byte-identical files.

    python scripts/generate_data.py --out data/ --seed 42
"""

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

# Generic part names per category, so filler parts read like real hardware.
PART_NAMES = {
    "cables": ["USB-C cable", "HDMI cable", "DC power cable", "Display ribbon cable"],
    "mechanical": ["Hinge bracket", "Keyboard frame", "Rubber foot", "Bezel clip"],
    "electrical": ["Power button switch", "Battery pack", "Power adapter", "Speaker assembly"],
    "semiconductors": ["Memory module", "SSD controller", "Wi-Fi chip", "Voltage regulator"],
}

# Every case the loader and rules must handle. Do not change IDs: tests use them.
EDGE_CASE_DOCUMENTS = [
    # SUP-101: clean supplier (R1). Quality cert has no expiry (R6).
    {"document_id": "DOC-001", "supplier_id": "SUP-101", "document_type": "quality_cert", "issue_date": "2024-01-15", "expiry_date": None},
    {"document_id": "DOC-002", "supplier_id": "SUP-101", "document_type": "safety_cert", "issue_date": "2026-03-01", "expiry_date": "2027-03-01"},
    {"document_id": "DOC-003", "supplier_id": "SUP-101", "document_type": "env_declaration", "issue_date": "2026-02-10", "expiry_date": "2027-02-10"},
    # SUP-102: expired safety cert (R2), env declaration expiring soon (R3).
    {"document_id": "DOC-004", "supplier_id": "SUP-102", "document_type": "quality_cert", "issue_date": "2023-06-01", "expiry_date": None},
    {"document_id": "DOC-005", "supplier_id": "SUP-102", "document_type": "safety_cert", "issue_date": "2025-06-01", "expiry_date": "2026-06-01"},
    {"document_id": "DOC-006", "supplier_id": "SUP-102", "document_type": "env_declaration", "issue_date": "2025-11-20", "expiry_date": "2026-11-20"},
    # SUP-103: no safety cert at all (R5), env declaration expires today (R4).
    {"document_id": "DOC-007", "supplier_id": "SUP-103", "document_type": "quality_cert", "issue_date": "2024-04-05", "expiry_date": None},
    {"document_id": "DOC-008", "supplier_id": "SUP-103", "document_type": "env_declaration", "issue_date": "2025-10-26", "expiry_date": "2026-10-26"},
    # Bad records: blank and absent supplier ID (R8).
    {"document_id": "DOC-009", "supplier_id": "", "document_type": "quality_cert", "issue_date": "2026-05-01", "expiry_date": None},
    {"document_id": "DOC-009b", "document_type": "quality_cert", "issue_date": "2026-05-01", "expiry_date": None},
    # Bad records: unknown type (R9), bad date string and non-string date (R10), null expiry on an expiring type (R7).
    {"document_id": "DOC-010", "supplier_id": "SUP-104", "document_type": "iso_badge", "issue_date": "2026-05-01", "expiry_date": "2027-05-01"},
    {"document_id": "DOC-011", "supplier_id": "SUP-104", "document_type": "safety_cert", "issue_date": "2026-13-45", "expiry_date": "2027-01-01"},
    {"document_id": "DOC-011b", "supplier_id": "SUP-104", "document_type": "safety_cert", "issue_date": "2026-01-01", "expiry_date": 20270101},
    {"document_id": "DOC-012", "supplier_id": "SUP-104", "document_type": "safety_cert", "issue_date": "2026-01-01", "expiry_date": None},
    # SUP-105: pending safety cert (R17, 1.1.0) and a bad status (R11).
    {"document_id": "DOC-013", "supplier_id": "SUP-105", "document_type": "safety_cert", "issue_date": "2026-09-01", "expiry_date": "2027-09-01", "status": "pending"},
    {"document_id": "DOC-014", "supplier_id": "SUP-105", "document_type": "quality_cert", "issue_date": "2024-09-01", "expiry_date": None},
    {"document_id": "DOC-015", "supplier_id": "SUP-105", "document_type": "env_declaration", "issue_date": "2026-09-01", "expiry_date": "2027-09-01", "status": "maybe"},
]

EDGE_CASE_PARTS = [
    {"part_number": "PRT-5001", "description": "AC power cord", "part_category": "cables", "supplier_id": "SUP-101"},
    {"part_number": "PRT-5002", "description": "Monitor power switch", "part_category": "electrical", "supplier_id": "SUP-102"},
    {"part_number": "PRT-5003", "description": "Laptop cooling fan", "part_category": "electrical", "supplier_id": "SUP-103"},
    {"part_number": "PRT-5004", "description": "Laptop motherboard", "part_category": "semiconductors", "supplier_id": "SUP-103"},
    # SUP-106 has no documents at all (R16).
    {"part_number": "PRT-5005", "description": "Chassis hinge", "part_category": "mechanical", "supplier_id": "SUP-106"},
    {"part_number": "PRT-5006", "description": "Display panel", "part_category": "electrical", "supplier_id": "SUP-105"},
    # Bad record: category not in settings (R12).
    {"part_number": "PRT-5099", "description": "Rubber gasket", "part_category": "seal", "supplier_id": "SUP-101"},
]

# Filler documents are issued in 2026 and valid for a year, so they expire
# after 2027-01-01: well past today (2026-10-26) + 45 days. They never flag.
FILLER_ISSUE_START = date(2026, 1, 2)
FILLER_ISSUE_END = date(2026, 9, 30)


def filler_records(fake, count):
    documents, parts = [], []
    for n in range(count):
        supplier_id = f"SUP-{201 + n}"
        issue = fake.date_between_dates(FILLER_ISSUE_START, FILLER_ISSUE_END)
        expiry = issue + timedelta(days=365)
        for offset, document_type in enumerate(["quality_cert", "safety_cert", "env_declaration"]):
            documents.append({
                "document_id": f"DOC-{101 + 3 * n + offset}",
                "supplier_id": supplier_id,
                "document_type": document_type,
                "issue_date": issue.isoformat(),
                "expiry_date": None if document_type == "quality_cert" else expiry.isoformat(),
            })
        category = fake.random_element(sorted(PART_NAMES))
        parts.append({
            "part_number": f"PRT-{6001 + n}",
            "description": fake.random_element(PART_NAMES[category]),
            "part_category": category,
            "supplier_id": supplier_id,
        })
    return documents, parts


def generate(seed, filler_suppliers):
    fake = Faker()
    fake.seed_instance(seed)
    documents, parts = filler_records(fake, filler_suppliers)
    return EDGE_CASE_DOCUMENTS + documents, EDGE_CASE_PARTS + parts


def write_json(path, records):
    path.write_text(json.dumps(records, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("data"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--filler-suppliers", type=int, default=3)
    args = parser.parse_args()

    documents, parts = generate(args.seed, args.filler_suppliers)
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / "documents.json", documents)
    write_json(args.out / "parts.json", parts)
    print(f"Wrote {len(documents)} documents and {len(parts)} parts to {args.out}")


if __name__ == "__main__":
    main()
