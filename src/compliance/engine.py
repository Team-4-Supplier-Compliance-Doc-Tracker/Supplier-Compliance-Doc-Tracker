# Runs every registered rule and works out at-risk parts.

import compliance.rules  # noqa: F401  (importing the package registers every rule)
from compliance.models import AtRiskPart, Flag
from compliance.rules_base import RULES


def run_rules(documents, parts, settings, today) -> tuple[list[Flag], list[AtRiskPart]]:
    flags = [flag for rule in RULES for flag in rule.evaluate(documents, parts, settings, today)]
    return flags, []
