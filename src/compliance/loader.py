# JSON input loading: read_json_list and the record loaders. Implemented in DATA-02.

import json
import re
from datetime import date

from compliance.models import InputFileError, Part, RejectedRecord, SupplierDocument


def read_json(path):
    # Parse one JSON file. Raises InputFileError naming the file when it is missing or not valid JSON.
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        raise InputFileError(path, "file not found") from None
    except json.JSONDecodeError as error:
        raise InputFileError(path, f"not valid JSON (line {error.lineno}, column {error.colno})") from None


def read_json_list(path) -> list[dict]:
    # Raises InputFileError on missing file, invalid JSON, or non-list top level.
    content = read_json(path)
    if not isinstance(content, list):
        raise InputFileError(path, "expected a JSON list of records")
    return content


def load_documents(path, settings) -> tuple[list[SupplierDocument], list[RejectedRecord]]:
    # Each record becomes a SupplierDocument or a RejectedRecord with the first reason it fails.
    return _load_records(path, "document_id", lambda record: _to_document(record, settings))


def load_parts(path, settings) -> tuple[list[Part], list[RejectedRecord]]:
    return _load_records(path, "part_number", lambda record: _to_part(record, settings))


class _Reject(Exception):
    pass


DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
STATUSES = ("approved", "pending")


def _load_records(path, id_key, convert):
    clean, rejected = [], []
    for index, record in enumerate(read_json_list(path)):
        raw_id = _text_or_blank(record, id_key)
        supplier_id = _text_or_blank(record, "supplier_id")
        try:
            if not isinstance(record, dict):
                raise _Reject("not a JSON object")
            clean.append(convert(record))
        except _Reject as reason:
            rejected.append(RejectedRecord(str(path), index, raw_id, str(reason), supplier_id))
    return clean, rejected


def _text_or_blank(record, key):
    # For labelling a rejected record: the value if it is a string, else "".
    value = record.get(key) if isinstance(record, dict) else None
    return value if isinstance(value, str) else ""


def _to_document(record, settings):
    document_id = _required_text(record, "document_id", "missing document ID")
    supplier_id = _required_text(record, "supplier_id", "missing supplier ID")

    document_type = record.get("document_type")
    if document_type not in settings.document_types:
        raise _Reject("unknown document type")

    issue_date = _parse_date(record.get("issue_date"))
    expiry_value = record.get("expiry_date")
    if expiry_value is None and document_type not in settings.expiring_types:
        expiry_date = None
    else:
        expiry_date = _parse_date(expiry_value)

    status = record.get("status", "approved")
    if status not in STATUSES:
        raise _Reject("unknown status")

    return SupplierDocument(document_id, supplier_id, document_type, issue_date, expiry_date, status)


def _to_part(record, settings):
    part_number = _required_text(record, "part_number", "missing part number")
    description = _required_text(record, "description", "missing description")
    supplier_id = _required_text(record, "supplier_id", "missing supplier ID")

    part_category = record.get("part_category")
    if part_category not in settings.required_documents:
        raise _Reject("unknown part category")

    return Part(part_number, description, part_category, supplier_id)


def _required_text(record, key, reason):
    # "", null, a non-string, or an absent key all count as missing.
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _Reject(reason)
    return value


def _parse_date(value):
    # Only YYYY-MM-DD strings. date.fromisoformat alone would also accept forms like "20260101".
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        raise _Reject("invalid date")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise _Reject("invalid date") from None
