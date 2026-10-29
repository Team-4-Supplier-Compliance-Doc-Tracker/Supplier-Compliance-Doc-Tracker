# A renewal sits on file next to the document it replaces (kept for audit), so date rules judge only
# the current document per supplier and type: the newest issue_date, then the later expiry on a tie.

from datetime import date


def current_documents(documents):
    current = {}
    for doc in documents:
        key = (doc.supplier_id, doc.document_type)
        if key not in current or _newness(doc) > _newness(current[key]):
            current[key] = doc
    return list(current.values())


def _newness(doc):
    return doc.issue_date, doc.expiry_date or date.max   # no expiry outlasts any date
