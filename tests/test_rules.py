from datetime import date, timedelta

from compliance.models import Part, SupplierDocument
from compliance.rules import ExpiredRule, ExpiringSoonRule, MissingDocumentRule, PendingDocumentRule
from compliance.rules_base import RULES, ComplianceRule


def test_rule_subclass_contract():
    for rule in RULES:
        assert isinstance(rule, ComplianceRule)
        assert isinstance(rule.name, str) and rule.name
        assert callable(rule.evaluate)


def flagged_ids(flags):
    return {flag.document_id for flag in flags}


def doc(document_id, document_type, expiry_date, supplier_id="SUP-900"):
    return SupplierDocument(document_id, supplier_id, document_type, expiry_date - timedelta(days=365), expiry_date)


# ExpiredRule

def test_expired_rule_flags_past_expiry(sample_docs, sample_parts, settings, today):
    flags = ExpiredRule().evaluate(sample_docs, sample_parts, settings, today)
    assert flagged_ids(flags) == {"DOC-005"}
    assert flags[0].supplier_id == "SUP-102"
    assert flags[0].document_type == "safety_cert"
    assert flags[0].expiry_date.isoformat() == "2026-06-01"


def test_expired_rule_ignores_today(sample_docs, sample_parts, settings, today):
    doc_008 = [document for document in sample_docs if document.document_id == "DOC-008"]
    assert doc_008[0].expiry_date == today
    assert ExpiredRule().evaluate(doc_008, sample_parts, settings, today) == []


def test_expired_rule_skips_null_expiry(sample_docs, sample_parts, settings, today):
    doc_001 = [document for document in sample_docs if document.document_id == "DOC-001"]
    assert doc_001[0].expiry_date is None
    assert ExpiredRule().evaluate(doc_001, sample_parts, settings, today) == []


# ExpiringSoonRule

def test_expiring_soon_within_window(sample_docs, sample_parts, settings, today):
    flags = ExpiringSoonRule().evaluate(sample_docs, sample_parts, settings, today)
    assert "DOC-006" in flagged_ids(flags)


def test_expiring_soon_includes_today(sample_docs, sample_parts, settings, today):
    flags = ExpiringSoonRule().evaluate(sample_docs, sample_parts, settings, today)
    assert "DOC-008" in flagged_ids(flags)
    assert flagged_ids(flags) == {"DOC-006", "DOC-008"}


def test_expiring_soon_excludes_beyond_window(sample_parts, settings, today):
    window = settings.expiring_soon_days
    documents = [
        doc("DOC-LAST-DAY", "env_declaration", today + timedelta(days=window)),
        doc("DOC-TOO-LATE", "env_declaration", today + timedelta(days=window + 1), supplier_id="SUP-901"),
    ]
    flags = ExpiringSoonRule().evaluate(documents, sample_parts, settings, today)
    assert flagged_ids(flags) == {"DOC-LAST-DAY"}


def test_expiring_soon_skips_null_expiry(sample_docs, sample_parts, settings, today):
    doc_001 = [document for document in sample_docs if document.document_id == "DOC-001"]
    assert ExpiringSoonRule().evaluate(doc_001, sample_parts, settings, today) == []


# MissingDocumentRule

def missing_pairs(flags):
    return {(flag.supplier_id, flag.document_type) for flag in flags}


def test_missing_rule_flags_absent_required_type(sample_docs, sample_parts, settings, today):
    flags = MissingDocumentRule().evaluate(sample_docs, sample_parts, settings, today)
    assert missing_pairs(flags) == {
        ("SUP-103", "safety_cert"),
        ("SUP-105", "safety_cert"),   # only one is DOC-013, which is pending
        ("SUP-105", "env_declaration"),
        ("SUP-106", "quality_cert"),
        ("SUP-106", "env_declaration"),
    }
    assert all(flag.document_id is None and flag.expiry_date is None for flag in flags)


def test_missing_rule_ignores_unrequired_type(sample_docs, sample_parts, settings, today):
    # SUP-103 has no safety_cert, but semiconductors do not require one.
    motherboard = [part for part in sample_parts if part.part_number == "PRT-5004"]
    assert MissingDocumentRule().evaluate(sample_docs, motherboard, settings, today) == []


def test_missing_rule_one_flag_per_supplier_type(sample_docs, sample_parts, settings, today):
    parts = sample_parts + [Part("PRT-7000", "Laptop speaker", "electrical", "SUP-103")]
    flags = MissingDocumentRule().evaluate(sample_docs, parts, settings, today)
    sup_103_safety = [flag for flag in flags if (flag.supplier_id, flag.document_type) == ("SUP-103", "safety_cert")]
    assert len(sup_103_safety) == 1


def test_missing_rule_treats_pending_as_absent(sample_docs, sample_parts, settings, today):
    # SUP-105's only safety_cert is DOC-013, still pending, so its electrical display panel lacks one.
    display_panel = [part for part in sample_parts if part.part_number == "PRT-5006"]
    flags = MissingDocumentRule().evaluate(sample_docs, display_panel, settings, today)
    assert ("SUP-105", "safety_cert") in missing_pairs(flags)


# PendingDocumentRule

def test_pending_rule_flags_pending_document(sample_docs, sample_parts, settings, today):
    flags = PendingDocumentRule().evaluate(sample_docs, sample_parts, settings, today)
    assert flagged_ids(flags) == {"DOC-013"}
    assert flags[0].supplier_id == "SUP-105"
    assert flags[0].document_type == "safety_cert"
    assert flags[0].expiry_date.isoformat() == "2027-09-01"


# Renewals: the old document stays on file for audit, only the newest one per supplier and type is judged

def renewal(document_id, document_type, issue_date, expiry_date, supplier_id="SUP-102"):
    return SupplierDocument(document_id, supplier_id, document_type, issue_date, expiry_date)


def test_renewal_clears_expired(sample_docs, sample_parts, settings, today):
    documents = sample_docs + [renewal("DOC-005-R1", "safety_cert", date(2026, 6, 1), date(2027, 6, 1))]
    assert ExpiredRule().evaluate(documents, sample_parts, settings, today) == []


def test_renewal_clears_expiring_soon(sample_docs, sample_parts, settings, today):
    documents = sample_docs + [renewal("DOC-006-R1", "env_declaration", date(2026, 10, 20), date(2027, 11, 20))]
    flags = ExpiringSoonRule().evaluate(documents, sample_parts, settings, today)
    assert flagged_ids(flags) == {"DOC-008"}


def test_renewal_that_is_expiring_soon_is_flagged(sample_docs, sample_parts, settings, today):
    # A short renewal replaces expired DOC-005 but itself runs out within the window.
    documents = sample_docs + [renewal("DOC-005-R1", "safety_cert", date(2026, 6, 1), date(2026, 11, 30))]
    assert ExpiredRule().evaluate(documents, sample_parts, settings, today) == []
    assert "DOC-005-R1" in flagged_ids(ExpiringSoonRule().evaluate(documents, sample_parts, settings, today))


def test_two_expired_documents_flag_only_the_newest(sample_docs, sample_parts, settings, today):
    documents = sample_docs + [renewal("DOC-005-OLD", "safety_cert", date(2024, 6, 1), date(2025, 6, 1))]
    flags = ExpiredRule().evaluate(documents, sample_parts, settings, today)
    assert flagged_ids(flags) == {"DOC-005"}


def test_pending_renewal_does_not_replace_approved_document(sample_docs, sample_parts, settings, today):
    # 1.1.0: DOC-005-R1 is not approved yet, so expired DOC-005 is still the cert SUP-102 relies on.
    pending_renewal = SupplierDocument("DOC-005-R1", "SUP-102", "safety_cert", date(2026, 6, 1), date(2027, 6, 1), "pending")
    documents = sample_docs + [pending_renewal]
    assert flagged_ids(ExpiredRule().evaluate(documents, sample_parts, settings, today)) == {"DOC-005"}
    assert "DOC-005-R1" in flagged_ids(PendingDocumentRule().evaluate(documents, sample_parts, settings, today))


# All rules

def test_each_rule_returns_only_its_own_flag_type(sample_docs, sample_parts, settings, today):
    for rule in (ExpiredRule(), ExpiringSoonRule(), MissingDocumentRule(), PendingDocumentRule()):
        flags = rule.evaluate(sample_docs, sample_parts, settings, today)
        assert flags, f"{rule.name} produced no flags on the sample data"
        assert {flag.flag_type for flag in flags} == {rule.name}
