# 1.1.0: a clean document still awaiting approval. A warning only: never makes a part at risk.

from compliance.models import Flag
from compliance.rules_base import ComplianceRule, register


@register
class PendingDocumentRule(ComplianceRule):
    name = "pending"

    def evaluate(self, documents, parts, settings, today):
        return [
            Flag(self.name, doc.supplier_id, doc.document_type, doc.document_id, doc.expiry_date)
            for doc in documents
            if doc.status == "pending"
        ]
