# A document that expires today or within settings.expiring_soon_days. Implemented next.

from compliance.rules_base import ComplianceRule, register


@register
class ExpiringSoonRule(ComplianceRule):
    name = "expiring_soon"

    def evaluate(self, documents, parts, settings, today):
        raise NotImplementedError
