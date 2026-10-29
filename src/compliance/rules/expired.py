# A document whose expiry date has passed. Expiry == today is still valid (expiring soon, not expired).

from compliance.models import Flag
from compliance.rules_base import ComplianceRule, register


@register
class ExpiredRule(ComplianceRule):
    name = "expired"

    def evaluate(self, documents, parts, settings, today):
        return [
            Flag(self.name, doc.supplier_id, doc.document_type, doc.document_id, doc.expiry_date)
            for doc in documents
            if doc.expiry_date is not None and doc.expiry_date < today
        ]
