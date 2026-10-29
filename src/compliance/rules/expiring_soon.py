# A document that expires today or within settings.expiring_soon_days. A warning only: never makes a part at risk.

from datetime import timedelta

from compliance.models import Flag
from compliance.rules_base import ComplianceRule, register


@register
class ExpiringSoonRule(ComplianceRule):
    name = "expiring_soon"

    def evaluate(self, documents, parts, settings, today):
        window_end = today + timedelta(days=settings.expiring_soon_days)
        return [
            Flag(self.name, doc.supplier_id, doc.document_type, doc.document_id, doc.expiry_date)
            for doc in documents
            if doc.expiry_date is not None and today <= doc.expiry_date <= window_end
        ]
