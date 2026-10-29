# A document type a part's category requires that the part's supplier has no clean document of. Implemented next.

from compliance.rules_base import ComplianceRule, register


@register
class MissingDocumentRule(ComplianceRule):
    name = "missing"

    def evaluate(self, documents, parts, settings, today):
        raise NotImplementedError
