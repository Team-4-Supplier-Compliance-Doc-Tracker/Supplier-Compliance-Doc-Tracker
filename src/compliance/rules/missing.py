# A document type a part's category requires that the part's supplier has no clean document of.
# One flag per (supplier, type), however many parts need it. Status is ignored until 1.1.0.

from compliance.models import Flag
from compliance.rules_base import ComplianceRule, register


@register
class MissingDocumentRule(ComplianceRule):
    name = "missing"

    def evaluate(self, documents, parts, settings, today):
        on_file = {(doc.supplier_id, doc.document_type) for doc in documents}
        gaps = {}   # dict keeps the order parts were listed in, with no duplicates
        for part in parts:
            for document_type in settings.required_documents.get(part.part_category, ()):
                key = (part.supplier_id, document_type)
                if key not in on_file:
                    gaps[key] = Flag(self.name, part.supplier_id, document_type)
        return list(gaps.values())
