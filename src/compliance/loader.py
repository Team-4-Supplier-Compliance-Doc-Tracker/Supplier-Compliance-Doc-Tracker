# JSON input loading: read_json_list and the record loaders. Implemented in DATA-02.

import json

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
    raise NotImplementedError


def load_parts(path, settings) -> tuple[list[Part], list[RejectedRecord]]:
    raise NotImplementedError
