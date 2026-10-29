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
| Where does the DB live in Docker? | `COMPLIANCE_DB_PATH=/data/compliance.db` on a named volume mounted at `/data` | Image is replaceable; history must outlive `docker rm` | Vedanshu | Agreed |
| Which Python base image? | `python:3.12-slim`; package via `PYTHONPATH=/app/src` (matches `pyproject.toml` pytest config) | Slim image keeps the container small; src-layout already used by the DATA-01 contract | Vedanshu | Agreed |
| Do faker/pytest go in the Docker image? | No — only `src/` + stdlib in the runtime image; CI installs `requirements.txt` for tests | Image is replaceable and stays small; generator and pytest run on the host / in CI, not in production runs | Vedanshu | Agreed |
| How are at-risk parts stored? | Own table `at_risk_parts` (check_id, part_number, supplier_id, reasons), one row per part per check; `flags` has no `part_number` | A flag is about a document or gap; at-risk is about a part and can have several reasons, so one `flags` row cannot hold it | Nikita | Open |
| What does `AtRiskPart.reasons` hold? | Strings `"<flag_type> <document_type>"` such as `"missing safety_cert"`, stored joined with `; ` and printed as is | Flag types alone ("missing", "missing") don't tell the manager which document is the problem | Nikita | Open |
| Who saves parts? | New `save_parts` in storage; the CLI saves documents and parts before running the rules | `at_risk_parts.part_number` is a foreign key to `parts`, and nothing else wrote parts | Nikita | Open |
| What happens when a document is re-sent with the same `document_id` but new dates (a renewal)? | The stored row keeps its old dates; the new ones are ignored because a duplicate `document_id` is skipped. A renewed certificate needs a new `document_id` to be stored. The same applies to parts (a changed description is ignored). Flags and reports are unaffected: rules run on the input file, and each flag stores its own expiry date | Follows from the skip-on-duplicate decision (2026-10-28); found in the PR #4 review by saving DOC-005 twice with different expiry dates | Nikita | Open |
