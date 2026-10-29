# Runs every registered rule and works out at-risk parts. Implemented in RULE-02.

from compliance.models import AtRiskPart, Flag


def run_rules(documents, parts, settings, today) -> tuple[list[Flag], list[AtRiskPart]]:
    raise NotImplementedError
