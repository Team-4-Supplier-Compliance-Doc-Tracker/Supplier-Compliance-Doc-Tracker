# Assumptions log

Every decision the brief does not specify, what we assumed, where it came from, and who decided. Customer answers are recorded here too. Update this file the same day as any decision.

Status: **Confirmed** (customer said so) · **Open** (our assumption, awaiting an answer) · **Changed** (customer answer replaced our assumption) · **Agreed** (team decision, no client input needed).

| Decision | What we assumed | Source or reason | Who decided | Status |
|---|---|---|---|---|
| Which part categories does the tool model? | Cables, mechanical, electrical, semiconductors | Customer named misc, electrical (switches with differing requirements), motherboards, computer parts at the 2026-10-28 check-in; we mapped these to four categories | Nikita | Open |
| Do quality certificates expire? | No: `expiry_date` may be `null`, and `quality_cert` is not in `expiring_types` | Customer check-in 2026-10-28 | Dheepthi | Confirmed |
| How often do environmental declarations renew? | Yearly; synthetic env declarations are 1-year | Customer check-in 2026-10-28 | Dheepthi | Confirmed |
| Do safety certificates expire? | Yes: `safety_cert` is in `expiring_types` | UL listings require annual factory audits; customer has not answered (Q8) | Dheepthi | Open |
| Which part categories require a safety certificate? | Only cables and electrical | Mains-rated parts fall under UL 61058-1 / CE Low Voltage Directive; mechanical parts and low-voltage logic do not | Nikita | Open |
| How many days ahead counts as expiring soon? | 45 (`expiring_soon_days`) | Customer: warn at least 45 days before expiry (check-in 2026-10-28) | Dheepthi | Confirmed |
| What happens when the expiry date is today? | Expiring soon, not expired | A document is valid through its expiry date | Dheepthi | Confirmed |
| Which parts are at risk when a supplier has a gap? | Only parts whose own category requires the expired or missing document type | Customer (Q5) | Nikita | Confirmed |
| Do expiring-soon or pending documents make a part at risk? | No, they are warnings only | The tool flags and reports; the compliance manager decides | Nikita | Agreed |
| What if a document has no `status`? | Defaults to `"approved"`; any value other than approved / pending is rejected "unknown status" | Existing lists have no status column, so absent means already accepted | Vedanshu | Open |
| What if an expiring document type has no expiry date? | Rejected "invalid date" | A safety cert or env declaration without an expiry cannot be checked, so the record is broken | Vedanshu | Agreed |
| What happens when a `document_id` already exists on save? | Skipped; saving the same batch twice is a no-op | Weekly runs re-read the same list; skipping keeps reruns safe | Vedanshu | Agreed |
| What if a supplier appears only through a part? | Both save functions upsert suppliers, so the supplier still has a row | Needed to store missing flags for suppliers with no documents (R16) | Nikita | Open |
| What is the Release 1.1.0 rule? | PendingDocumentRule (flag `pending`); in 1.1.0 a pending document counts as absent for the missing rule | Customer wants a pending / approved / missing view (Q6). Alternative kept: expiry-before-issue → `invalid_validity_window` | Dheepthi | Confirmed |
| How long is history kept? | Never pruned; backups kept 10 years | Customer (Q12) | Vedanshu | Confirmed |
| What is out of scope? | Notifications and per-shipment paperwork (certificates of conformance, test reports) | Customer mentioned soft alerts "later"; per-shipment paperwork is a different workflow | Vedanshu | Confirmed |
