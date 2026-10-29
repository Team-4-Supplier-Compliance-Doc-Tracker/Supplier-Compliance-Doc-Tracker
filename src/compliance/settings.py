# Settings file loader. Implemented in DATA-02.

from dataclasses import dataclass
from datetime import date

from compliance.loader import read_json
from compliance.models import InputFileError

REQUIRED_KEYS = ("today", "expiring_soon_days", "document_types", "expiring_types", "required_documents")


@dataclass(frozen=True)
class Settings:
    today: date | None
    expiring_soon_days: int
    document_types: tuple[str, ...]
    expiring_types: tuple[str, ...]                  # types that must have an expiry_date
    required_documents: dict[str, tuple[str, ...]]   # part_category -> required document types


def load_settings(path) -> Settings:
    # Raises InputFileError on missing file, invalid JSON, non-object top level, or a missing key.
    content = read_json(path)
    if not isinstance(content, dict):
        raise InputFileError(path, "expected a JSON object")

    for key in REQUIRED_KEYS:
        if key not in content:
            raise InputFileError(path, f"missing required setting '{key}'")

    return Settings(
        today=_parse_today(path, content["today"]),
        expiring_soon_days=content["expiring_soon_days"],
        document_types=tuple(content["document_types"]),
        expiring_types=tuple(content["expiring_types"]),
        required_documents={
            category: tuple(types) for category, types in content["required_documents"].items()
        },
    )


def _parse_today(path, value):
    # null means "use the system date"; the CLI resolves it.
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise InputFileError(path, f"'today' is not a YYYY-MM-DD date: {value!r}") from None
