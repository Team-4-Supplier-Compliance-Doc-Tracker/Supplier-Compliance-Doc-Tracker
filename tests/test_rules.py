from compliance.rules_base import RULES, ComplianceRule


def test_rule_subclass_contract():
    for rule in RULES:
        assert isinstance(rule, ComplianceRule)
        assert isinstance(rule.name, str) and rule.name
        assert callable(rule.evaluate)
