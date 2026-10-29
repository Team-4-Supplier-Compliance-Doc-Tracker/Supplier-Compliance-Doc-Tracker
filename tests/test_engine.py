from datetime import date

from compliance.engine import run_rules
from compliance.models import SupplierDocument


def at_risk_by_part(at_risk):
    return {part.part_number: part for part in at_risk}


def test_collects_flags_from_all_rules(sample_docs, sample_parts, settings, today):
    flags, _ = run_rules(sample_docs, sample_parts, settings, today)
    assert {flag.flag_type for flag in flags} == {"expired", "expiring_soon", "missing", "pending"}
    assert len(flags) == 9   # 1 expired + 2 expiring soon + 5 missing + 1 pending


def test_at_risk_from_expired(sample_docs, sample_parts, settings, today):
    _, at_risk = run_rules(sample_docs, sample_parts, settings, today)
    # SUP-102's safety_cert (DOC-005) expired, and electrical parts require one.
    assert at_risk_by_part(at_risk)["PRT-5002"].reasons == ("expired safety_cert",)


def test_at_risk_from_missing_only_for_requiring_category(sample_docs, sample_parts, settings, today):
    # SUP-103 has no safety_cert: the electrical fan needs one, the semiconductor motherboard does not.
    _, at_risk = run_rules(sample_docs, sample_parts, settings, today)
    parts = at_risk_by_part(at_risk)
    assert parts["PRT-5003"].reasons == ("missing safety_cert",)
    assert "PRT-5004" not in parts


def test_expiring_soon_does_not_make_at_risk(sample_docs, sample_parts, settings, today):
    # SUP-103's env_declaration (DOC-008) expires today: a warning, not a gap.
    motherboard = [part for part in sample_parts if part.part_number == "PRT-5004"]
    flags, at_risk = run_rules(sample_docs, motherboard, settings, today)
    assert any(flag.flag_type == "expiring_soon" and flag.supplier_id == "SUP-103" for flag in flags)
    assert at_risk == []


def test_pending_does_not_make_at_risk(sample_docs, sample_parts, settings, today):
    # SUP-101 already holds an approved safety_cert, so a second, pending one is only a warning.
    renewal = SupplierDocument("DOC-900", "SUP-101", "safety_cert", date(2026, 10, 1), date(2027, 10, 1), "pending")
    sup_101_docs = [document for document in sample_docs if document.supplier_id == "SUP-101"] + [renewal]
    power_cord = [part for part in sample_parts if part.part_number == "PRT-5001"]
    flags, at_risk = run_rules(sup_101_docs, power_cord, settings, today)
    assert [flag.flag_type for flag in flags] == ["pending"]
    assert at_risk == []


def test_clean_supplier_not_at_risk(sample_docs, sample_parts, settings, today):
    _, at_risk = run_rules(sample_docs, sample_parts, settings, today)
    assert "PRT-5001" not in at_risk_by_part(at_risk)


def test_at_risk_reasons_listed(sample_docs, sample_parts, settings, today):
    _, at_risk = run_rules(sample_docs, sample_parts, settings, today)
    parts = at_risk_by_part(at_risk)
    assert set(parts) == {"PRT-5002", "PRT-5003", "PRT-5005", "PRT-5006"}
    assert parts["PRT-5005"].supplier_id == "SUP-106"
    assert parts["PRT-5005"].reasons == ("missing quality_cert", "missing env_declaration")
    assert parts["PRT-5006"].reasons == ("missing safety_cert", "missing env_declaration")


def test_no_flags_day(sample_docs, sample_parts, settings, today):
    # SUP-101 holds every document a cable needs, none expired or expiring soon.
    sup_101_docs = [document for document in sample_docs if document.supplier_id == "SUP-101"]
    power_cord = [part for part in sample_parts if part.part_number == "PRT-5001"]
    assert run_rules(sup_101_docs, power_cord, settings, today) == ([], [])


def test_supplier_known_only_via_part_gets_missing_flags(sample_docs, sample_parts, settings, today):
    # SUP-106 has no documents at all; it appears only as the supplier of PRT-5005.
    flags, _ = run_rules(sample_docs, sample_parts, settings, today)
    sup_106 = {(flag.flag_type, flag.document_type) for flag in flags if flag.supplier_id == "SUP-106"}
    assert sup_106 == {("missing", "quality_cert"), ("missing", "env_declaration")}
