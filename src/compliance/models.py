# Shared data shapes. Every module codes and tests against these.

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SupplierDocument:
    document_id: str
    supplier_id: str
    document_type: str
    issue_date: date
    expiry_date: date | None    # None only for types not in settings.expiring_types
    status: str = "approved"    # "approved" | "pending"


@dataclass(frozen=True)
class Part:
    part_number: str
    description: str
    part_category: str
    supplier_id: str


@dataclass(frozen=True)
class RejectedRecord:
    source_file: str
    index: int              # position in the JSON list, 0-based
    raw_id: str             # document_id or part_number if present, else ""
    reason: str


class InputFileError(Exception):
    """File-level failure: missing, not valid JSON, or wrong top-level shape.
    Carries the file path. The CLI prints it and exits non-zero."""

    def __init__(self, path, message):
        self.path = str(path)
        super().__init__(f"{self.path}: {message}")


@dataclass(frozen=True)
class Flag:
    flag_type: str          # "expired" | "expiring_soon" | "missing" | "pending"
    supplier_id: str
    document_type: str
    document_id: str | None = None
    expiry_date: date | None = None


@dataclass(frozen=True)
class AtRiskPart:
    part_number: str
    supplier_id: str
    reasons: tuple[str, ...]   # one "<flag_type> <document_type>" per gap, e.g. "missing safety_cert"
