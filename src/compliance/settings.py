# Settings file loader. Implemented in DATA-02.

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Settings:
    today: date | None
    expiring_soon_days: int
    document_types: tuple[str, ...]
    expiring_types: tuple[str, ...]                  # types that must have an expiry_date
    required_documents: dict[str, tuple[str, ...]]   # part_category -> required document types


def load_settings(path) -> Settings:
    # Raises InputFileError on missing file, invalid JSON, non-object top level, or a missing key.
    raise NotImplementedError
