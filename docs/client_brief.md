# Client brief — Supplier Compliance Document Tracker

**Team 4:** Dheepthi Reddy · Nikita Ravi · Vedanshu Daxesh Patel  
**Customer:** hardware maker (laptops, monitors, computer hardware) buying cables, mechanical parts, electrical assemblies, and semiconductors from many suppliers.

This one-page brief records who the users are, how work is done today, where it fails, the terms they use, and the rules that apply. Each section names its author. Cite original sources, not AI summaries.

---

## Who the users are

*Researched and written by: **Dheepthi Reddy** (DOCS-01).*

Four groups touch supplier documents, and responsibility is shared between them: quality owns technical approvals and audit evidence, while procurement owns supplier selection and contract records ([Racklify, AVL compliance and audit](https://racklify.com/encyclopedia/approved-vendor-list-compliance-and-audit-roles-evidence-and-inspector-expectations/)).

| User | What they do with supplier documents | What they need from the tool |
|---|---|---|
| **Compliance manager** | Owns the supplier document file on the quality side; decides whether a gap blocks use of a part | One list of every expired, expiring and missing document. The tool flags; the manager decides (course brief) |
| **Buyers** (procurement) | Choose suppliers and order parts against the approved supplier list | Which **parts** are at risk before they order, not just which suppliers |
| **Suppliers** | Send their quality, safety and environmental documents; today by email and shared folders (customer problem statement) | A clear reason when a document they sent is rejected |
| **Auditors** | Trace a part back to its supplier record and check the evidence; "commonly cite expired certificates left on supplier records" ([Racklify](https://racklify.com/encyclopedia/approved-vendor-list-compliance-and-audit-roles-evidence-and-inspector-expectations/)) | A dated history of what was known on each check (see "The rules that apply") |

What this changed in what I built:

- **Flags, never decisions.** Every rule returns a flag; nothing approves or blocks a supplier, because that call belongs to the compliance manager.
- **At risk per part, for the buyer.** A gap only makes a part at risk when that part's own category needs the document (Q5), so a buyer is not told to stop ordering parts that are fine.
- **A reason on every rejection, for the supplier.** A bad record is rejected with one plain reason (`invalid date`, `unknown document type`), and the loader keeps its supplier ID so the rejection can be traced back to whoever sent it.

### The terms they use

*Also DOCS-01 (Dheepthi).*

| Term | What it means | How the tool uses it | Source |
|---|---|---|---|
| **Quality certificate** (`quality_cert`) | Shows the supplier runs a certified quality management system, e.g. ISO 9001, issued by a certification body after an audit | No expiry date: the customer said quality certificates do not expire in their records (Q2), so `expiry_date` may be `null` for this type only | [ISO 9001](https://www.iso.org/standard/62085.html); customer Q2 |
| **Safety certificate** (`safety_cert`) | Shows a product meets electrical safety requirements. In the EU, the Low Voltage Directive covers equipment from 50 to 1000 V AC and 75 to 1500 V DC, and CE marking is affixed only after a conformity assessment. In the US, a UL Mark is kept up by follow-up factory inspections after certification | Required for cables and electrical parts only. Expires (`expiring_types`): the customer confirmed this (Q8), and it fits UL inspections continuing after certification | [EU Low Voltage Directive](https://single-market-economy.ec.europa.eu/sectors/electrical-and-electronic-engineering-industries-eei/low-voltage-directive-lvd_en); [UL Follow-Up Services](https://www.ul.com/resources/follow-up-services); customer Q8 |
| **Environmental declaration** (`env_declaration`) | States which restricted substances a part contains. RoHS restricts 10 hazardous substances in electrical and electronic equipment, such as lead, cadmium and mercury; REACH is the EU regulation on chemicals | Required for every category. Renews yearly (Q3), so synthetic declarations run one year | [EU RoHS](https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en); [ECHA REACH](https://echa.europa.eu/regulations/reach/understanding-reach); customer Q3 |
| **Approved supplier list** (AVL) | The list of suppliers procurement may buy from; auditors trace parts back to it | Context only: the tool reports gaps, it does not edit the list | [Racklify](https://racklify.com/encyclopedia/approved-vendor-list-compliance-and-audit-roles-evidence-and-inspector-expectations/) |
| **Required documents** | The document types each part category must have on file | `settings.required_documents`, editable without code; four categories (Q1) | Customer Q1, Q5 |
| **Expiry date** | The last day a document is valid | Expiry equal to today is still valid, so it is "expiring soon", not "expired" (Q10) | Customer Q10 |
| **Expiring soon** | Valid now, but due to lapse within the warning window | `expiring_soon_days: 45`: the customer wants at least 45 days' notice (Q4) | Customer Q4 |
| **Pending / approved** | Whether the compliance manager has accepted a received document yet | `status` field; from 1.1.0 a pending document gets a `pending` flag and does not count as on file (Q6) | Customer Q6 |
| **Renewal** | A new certificate that replaces an older one of the same type | Arrives with a new `document_id`; only the newest approved document is judged, and the old one stays on file for audit | Team decision (assumptions log) |
| **At risk** | A part whose supplier has an expired or missing document **that this part's category requires** | Per-part at-risk list, with a reason per gap such as `missing safety_cert` | Customer Q5 |

**Open question for the customer.** Certification bodies describe ISO 9001 certificates as "valid for three years" with annual surveillance audits ([Citation ISO Certification](https://www.qmsuk.com/news/how-long-does-iso-9001-certification-last)). The customer told us quality certificates do not expire in their records (Q2), so we built to that answer. If they want the certificate's own validity date tracked, it is a settings change: add `quality_cert` to `expiring_types`.

#### Sources (this section)

| Source | Link | Used for |
|---|---|---|
| Racklify, Approved Vendor List compliance and audit | https://racklify.com/encyclopedia/approved-vendor-list-compliance-and-audit-roles-evidence-and-inspector-expectations/ | Who owns what; what auditors check |
| ISO 9001:2015 | https://www.iso.org/standard/62085.html | Quality certificate |
| Citation ISO Certification, How long does ISO 9001 certification last? | https://www.qmsuk.com/news/how-long-does-iso-9001-certification-last | Three-year validity (open question) |
| European Commission, Low Voltage Directive | https://single-market-economy.ec.europa.eu/sectors/electrical-and-electronic-engineering-industries-eei/low-voltage-directive-lvd_en | Safety certificate, voltage ranges, CE marking |
| UL Solutions, Follow-Up Services | https://www.ul.com/resources/follow-up-services | Safety certificate kept up by inspections |
| European Commission, RoHS Directive | https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en | Environmental declaration, restricted substances |
| ECHA, Understanding REACH | https://echa.europa.eu/regulations/reach/understanding-reach | Environmental declaration |
| Customer check-in, 2026-10-28 | `docs/customer_questions.md` (Q1–Q6, Q8, Q10) | Every customer answer above |

---

## How they do this work today

*Researched and written by: **Nikita Ravi** (DOCS-02). Skeleton assembled by Vedanshu for DOCS-03 — Nikita merges her final text here via PR.*

Today, supplier certificates live in **email attachments** and **shared folders**, often tracked in spreadsheets or approved-vendor lists. Expiry is a passive cell. Suppliers do not always volunteer renewals. Filing can happen without a compliance review. When an auditor asks “what did you know on date X?”, the trail is incomplete.

### Where it goes wrong

*Also DOCS-02 (Nikita).*

- Certificates expire unnoticed.
- A missing **safety certificate** is the gap that puts a part at risk in our sample: electrical and cable parts need one, and SUP-103 has none (PRT-5003).
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

- Electrical safety expectations for mains-rated parts (e.g. [UL Follow-Up Services](https://www.ul.com/resources/follow-up-services), [EU Low Voltage Directive](https://single-market-economy.ec.europa.eu/sectors/electrical-and-electronic-engineering-industries-eei/low-voltage-directive-lvd_en)) — why safety certs are required for **cables** and **electrical**, not mechanical / semiconductors.
- Environmental substance regimes ([RoHS](https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en), [REACH](https://echa.europa.eu/regulations/reach/understanding-reach)) — why every part category needs an environmental declaration; the customer says they renew yearly (Q3).

### Sources (this section)

| Source | Link |
|---|---|
| ISO 9001:2015 | https://www.iso.org/standard/62085.html |
| ASQ — ISO 9001 overview | https://asq.org/quality-resources/iso-9001 |
| UL Solutions, Follow-Up Services | https://www.ul.com/resources/follow-up-services |
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
