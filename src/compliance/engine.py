# Runs every registered rule and works out at-risk parts.

import compliance.rules  # noqa: F401  (importing the package registers every rule)
from compliance.models import AtRiskPart, Flag
from compliance.rules_base import RULES

# expiring_soon is only a warning: it never puts a part at risk.
AT_RISK_FLAG_TYPES = ("expired", "missing")


def run_rules(documents, parts, settings, today) -> tuple[list[Flag], list[AtRiskPart]]:
    flags = [flag for rule in RULES for flag in rule.evaluate(documents, parts, settings, today)]
    return flags, _at_risk_parts(flags, parts, settings)


def _at_risk_parts(flags, parts, settings):
    # A part is at risk when its supplier has a blocking flag on a type the part's category requires.
    at_risk = []
    for part in parts:
        required = settings.required_documents.get(part.part_category, ())
        reasons = [
            f"{flag.flag_type} {flag.document_type}"
            for flag in flags
            if flag.supplier_id == part.supplier_id
            and flag.flag_type in AT_RISK_FLAG_TYPES
            and flag.document_type in required
        ]
        if reasons:
            # dict.fromkeys drops repeats (two expired docs of one type) and keeps the order
            at_risk.append(AtRiskPart(part.part_number, part.supplier_id, tuple(dict.fromkeys(reasons))))
    return at_risk
