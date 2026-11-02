# Customer questions — Team 4

Questions brought to the instructor (as the hardware maker) and answers recorded for the assumptions log. Every member asked at least one. Check-in: **2026-10-28**.

| # | Question (owner) | Answer | Effect on the tool |
|---|---|---|---|
| Q1 | Which part categories should we model? (Nikita) | Customer named misc, electrical (switches with differing requirements), motherboards, computer parts. | Mapped to **cables, mechanical, electrical, semiconductors** in `settings.required_documents`. |
| Q2 | Do quality certificates expire? (Dheepthi) | No. | `quality_cert` is not in `expiring_types`; `expiry_date` may be `null`. |
| Q3 | How often do environmental declarations renew? (Dheepthi) | Yearly. | Synthetic env declarations are 1-year windows. |
| Q4 | Warn how far ahead of expiry? (Dheepthi) | At least **45 days**. Soft alerts by notification later (out of scope). | `expiring_soon_days: 45`. |
| Q5 | If a supplier has a gap, which parts are at risk? (Nikita) | Only parts whose **own category** requires that document type — not every part from that supplier. | Per-part at-risk in the engine. |
| Q6 | What view does the manager want of document status? (Dheepthi) | Pending / approved / missing. | Stored `status` in 1.0.0; **PendingDocumentRule** in 1.1.0: a pending document gets a `pending` flag (never at-risk), does not count as on file for the missing rule, and does not replace an approved document. |
| Q7 | How often will they run the tool? (Vedanshu) | Weekly. | Reruns must be safe; duplicate `document_id` on save is skipped. |
| Q8 | Do safety certificates expire? (Dheepthi) | Yes (answered after the check-in). | `safety_cert` is in `expiring_types`: it must have an `expiry_date` (a safety cert with none is rejected "invalid date"), and it is flagged expired or expiring soon like the env declaration. Fits UL Follow-Up Services, which keep inspecting after certification. |
| Q9 | What is out of scope for this tool? (Vedanshu) | Soft alerts “later”; per-shipment paperwork (certificates of conformance, test reports); reading email/PDFs. | Tool starts from an already-extracted JSON list; flags and reports only. |
| Q10 | Does expiry equal to today count as expired? (Dheepthi) | Document is valid through its expiry date. | Expiry == today → **expiring soon**, not expired. |
| Q11 | What happens to a renewed certificate with the same id? (Nikita) | (Team decision after review, not a customer answer.) | A renewal arrives with a **new** `document_id`; a duplicate id is skipped on save. The old document stays on file for audit, and only the newest **approved** document per supplier and type is judged, so a renewal clears the old expired flag. |
| Q12 | How long must history be kept for auditors? (Vedanshu) | **10 years.** | Never prune the SQLite history; backups retained 10 years; DB on a Docker volume. |

## Sources for follow-up (not customer answers)

- ISO 9001:2015 §8.4 — control of externally provided processes / supplier records: https://www.iso.org/standard/62085.html
- ASQ overview of ISO 9001 purchasing / external providers: https://asq.org/quality-resources/iso-9001
