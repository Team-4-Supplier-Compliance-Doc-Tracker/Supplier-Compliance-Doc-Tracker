# Base class for compliance rules and the registry the engine runs.

from compliance.models import Flag

RULES = []


class ComplianceRule:
    name: str

    def evaluate(self, documents, parts, settings, today) -> list[Flag]:
        raise NotImplementedError


def register(rule_class):
    # Class decorator: add one instance of the rule to RULES.
    RULES.append(rule_class())
    return rule_class
