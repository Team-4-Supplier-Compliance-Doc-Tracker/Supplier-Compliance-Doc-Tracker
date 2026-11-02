# Client brief — Supplier Compliance Document Tracker

**Team 4:** Dheepthi Reddy · Nikita Ravi · Vedanshu Daxesh Patel  
**Customer:** hardware maker (laptops, monitors, computer hardware) buying cables, mechanical parts, electrical assemblies, and semiconductors from many suppliers.

This one-page brief records who the users are, how work is done today, where it fails, the terms they use, and the rules that apply. Each section names its author. Cite original sources, not AI summaries.

---

## Who the users are

*Researched and written by: **Dheepthi Reddy** (DOCS-01). Skeleton assembled by Vedanshu for DOCS-03 — Dheepthi merges her final text here via PR.*

- **Compliance manager** — owns the supplier document file; decides whether a gap blocks use of a part. The tool flags; the manager decides.
- **Buyers** — order parts against the approved vendor list; need to know which parts are at risk before a build.
- **Suppliers** — send quality, safety, and environmental documents (today: email and shared folders).
- **Auditors** — ask what was known on a given date and how far back records go.

### The terms they use

*Also DOCS-01 (Dheepthi).*

| Term | Meaning (working definition) | Typical source |
|---|---|---|
| Quality certificate | Evidence of a quality management system (e.g. ISO 9001) | https://www.iso.org/standard/62085.html |
| Safety certificate | Evidence the part meets electrical safety (e.g. UL / CE LVD) | https://www.ul.com/services/ul-certification ; https://single-market-economy.ec.europa.eu/sectors/electrical-and-electronic-engineering-industries-eei/low-voltage-directive-lvd_en |
| Environmental declaration | Substance / environmental statement (e.g. RoHS / REACH) | https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en ; https://echa.europa.eu/regulations/reach/understanding-reach |
| Expiry / expiring soon | End of validity; warning window (≥ 45 days per customer) | Customer check-in 2026-10-28 |
| Required documents | Types each part category must have on file | Customer + `settings.required_documents` |
| At risk | Part whose supplier lacks a required type that **that category** needs | Customer Q5 |

---

## How they do this work today

*Researched and written by: **Nikita Ravi** (DOCS-02). Skeleton assembled by Vedanshu for DOCS-03 — Nikita merges her final text here via PR.*

Today, supplier certificates live in **email attachments** and **shared folders**, often tracked in spreadsheets or approved-vendor lists. Expiry is a passive cell. Suppliers do not always volunteer renewals. Filing can happen without a compliance review. When an auditor asks “what did you know on date X?”, the trail is incomplete.

### Where it goes wrong

*Also DOCS-02 (Nikita).*

- Certificates expire unnoticed.
- The document most often missing is the **safety certificate** (customer check-in).
- Nobody can say which **parts** are affected until an auditor asks.
- Spreadsheets record expiring environmental declarations but do not surface them weekly.

---

## The rules that apply

*Researched and written by: **Vedanshu Daxesh Patel** (DOCS-03).*

Supplier compliance documents are **quality records** about externally provided products. Under **ISO 9001:2015 §8.4** (*Control of externally provided processes, products and services*), the organisation must ensure that externally provided products meet requirements and must retain documented information as evidence of that control ([ISO 9001:2015](https://www.iso.org/standard/62085.html); overview: [ASQ — ISO 9001](https://asq.org/quality-resources/iso-9001)).

What that means for this tool:

1. **Dated state** — An auditor asks what was known on a given date. Every `compliance run` writes a dated check (`as_of_date`, `run_at`, `tool_version`) plus its flags. That is the audit trail, not a live-only dashboard.
2. **Retention** — The customer requires history kept **10 years** (Q12). The tool **never prunes** SQLite history; backups are kept 10 years and verified with `PRAGMA integrity_check`.
3. **Replaceable software, durable records** — The Docker **image** is replaceable; the database lives on a **named volume** (`COMPLIANCE_DB_PATH=/data/compliance.db`) so history survives `docker rm` and version rollback (1.1.0 → 1.0.0).
4. **No silent approval** — The tool flags and reports. It never approves a supplier or blocks an order. The compliance manager decides (ISO 9001 still expects human control of the process).

Related product rules that shape *which* documents matter (not implemented as legal engines — encoded in `settings.json`):

- Electrical safety expectations for mains-rated parts (e.g. [UL certification](https://www.ul.com/services/ul-certification), [EU Low Voltage Directive](https://single-market-economy.ec.europa.eu/sectors/electrical-and-electronic-engineering-industries-eei/low-voltage-directive-lvd_en)) — why safety certs are required for **cables** and **electrical**, not mechanical / semiconductors.
- Environmental substance regimes ([RoHS](https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en), [REACH](https://echa.europa.eu/regulations/reach/understanding-reach)) — why environmental declarations renew yearly.

### Sources (this section)

| Source | Link |
|---|---|
| ISO 9001:2015 | https://www.iso.org/standard/62085.html |
| ASQ — ISO 9001 overview | https://asq.org/quality-resources/iso-9001 |
| UL certification services | https://www.ul.com/services/ul-certification |
| EU Low Voltage Directive | https://single-market-economy.ec.europa.eu/sectors/electrical-and-electronic-engineering-industries-eei/low-voltage-directive-lvd_en |
| EU RoHS | https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en |
| ECHA REACH | https://echa.europa.eu/regulations/reach/understanding-reach |
| Customer check-in answers | `docs/customer_questions.md` (Q5, Q6, Q12, …) |

---

## Section ownership

| Section | Author |
|---|---|
| Who the users are / The terms they use | Dheepthi Reddy |
| How they do this work today / Where it goes wrong | Nikita Ravi |
| The rules that apply | Vedanshu Daxesh Patel |
| Brief assembly + source list check | Vedanshu Daxesh Patel |
