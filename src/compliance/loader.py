# JSON input loading: read_json_list and the record loaders. Implemented in DATA-02.

from compliance.models import Part, RejectedRecord, SupplierDocument


def read_json_list(path) -> list[dict]:
    # Raises InputFileError on missing file, invalid JSON, or non-list top level.
    raise NotImplementedError


def load_documents(path, settings) -> tuple[list[SupplierDocument], list[RejectedRecord]]:
    raise NotImplementedError


def load_parts(path, settings) -> tuple[list[Part], list[RejectedRecord]]:
    raise NotImplementedError
