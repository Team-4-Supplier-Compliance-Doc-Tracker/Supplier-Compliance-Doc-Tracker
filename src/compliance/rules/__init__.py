# Importing this package registers every rule in compliance.rules_base.RULES.

from compliance.rules.expired import ExpiredRule
from compliance.rules.expiring_soon import ExpiringSoonRule
from compliance.rules.missing import MissingDocumentRule

__all__ = ["ExpiredRule", "ExpiringSoonRule", "MissingDocumentRule"]
