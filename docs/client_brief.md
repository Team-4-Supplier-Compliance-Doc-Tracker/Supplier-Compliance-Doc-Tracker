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

*Researched and written by: **Nikita Ravi** (DOCS-02). I did this research before our first customer call.*

Supplier certificates arrive by **email** and sit in **shared folders** (customer problem statement). The usual record of them is a spreadsheet or an **approved vendor list (AVL)**, where the expiry date is just a cell.

The paperwork comes in two kinds with different lifecycles:

| Kind | Examples | Belongs to | How it is collected |
|---|---|---|---|
| **Supplier credentials** | Quality certificate, safety certificate, environmental declaration | The supplier | Once, then renewed |
| **Shipment evidence** | Certificate of conformance, material test report, heat or lot number | One delivery | With or before each delivery ([Standards Navigator](https://thestandardsnavigator.com/2026/04/18/supplier-quality-requirements/)) |

This tool covers supplier credentials only. Shipment paperwork is a different workflow and is out of scope (Q9).

Expiry also works differently by document. RoHS and REACH declarations often have no official expiry ([CR4 discussion](https://cr4.globalspec.com/thread/55713/How-long-is-a-RoHS-Certificate-Valid-for)), so companies set a refresh policy, commonly every 12 months ([GreenSoft](https://greensofttech.com/blog-2026-compliance-data-mgmt-in-practice-pt-1-refreshing-compliance-declarations/)). Our customer renews them yearly (Q3), so the `expiry_date` on a declaration is best read as its refresh-due date.

### Where it goes wrong

*Also DOCS-02 (Nikita).*

- **Expiry cells are passive.** When a certificate lapses, an Excel-based AVL "records the expiry date in a cell", and nothing else happens ([LeanLinking](https://leanlinking.com/blogs/what-is-an-approved-supplier-list/)).
- **Suppliers do not volunteer renewals.** They "rarely update" REACH declarations "unless asked" ([GreenSoft](https://greensofttech.com/blog-2026-compliance-data-mgmt-in-practice-pt-1-refreshing-compliance-declarations/)).
- **Documents get filed without review.** "Receiving a certificate and filing it without reviewing it" is not inspection ([Standards Navigator](https://thestandardsnavigator.com/2026/04/18/supplier-quality-requirements/)).
- **Safety certificates go missing.** The document most often missing is the safety certificate (customer check-in).
- **Nobody can say which parts are affected** until an auditor asks (customer problem statement).

**What an auditor asks.** ISO 9001 §8.4 expects retained evidence about suppliers ([ISO 9001 Checklist](https://www.iso-9001-checklist.co.uk/8.4-control-of-externally-provided-processes-products-services.htm)), but sets no retention period, so each company chooses one ([Quality Systems](https://qualitysystems.com/support/learning/records-required-by-iso-90012015/)). The hard question is not "what is expired today?" but "what did you know on date X?". A spreadsheet that gets overwritten cannot answer that.

### How the research scoped the customer call

Before the call, I compared our plan with how real teams and tools handle this, including [SKU.io](https://www.sku.io/docs/guides/manufacturing/lot-compliance/track-supplier-certificates/) and [SAP Supplier Lifecycle Management](https://help.sap.com/saphelp_slc200/helpdata/en/de/64bbd332d14155ad51166ddbecd26e/content.htm). That showed which of our assumptions had no source, so we knew what to ask instead of guessing.

| What the research found | What we had assumed | Outcome | What the tool does now |
|---|---|---|---|
| Our part categories and required documents had no source | Fastener, electrical, seal | Customer named their categories (Q1) | Four categories, editable in settings |
| Warning windows vary: SAP uses 30 days, SKU.io alerts from 90 | 30 days | Customer: at least 45 days (Q4) | `expiring_soon_days: 45` |
| ISO certificates run on a three-year cycle | Every document type expires | Customer: quality certificates do not expire in their records (Q2) | `expiry_date` may be `null` for quality certificates |
| SAP holds a supplier upload as pending until a purchaser approves it | A document is present or missing | Customer wants a pending / approved / missing view (Q6) | `status` field; `pending` flag in 1.1.0 |
| Real systems set requirements by category or supplier | Every gap affects all of a supplier's parts | Customer: only parts whose category requires the document (Q5) | At risk is worked out per part |
| ISO sets no retention period | History kept with no stated period | Customer: 10 years (Q12) | History is never pruned |
| Paperwork comes in two kinds | Documents attach to suppliers, never to shipments | Shipment paperwork is out of scope (Q9) | Supplier credentials only |
| SKU.io stores a renewal as a new document and keeps the old one, so an old row could keep flagging a renewed supplier | One active document per supplier and type | Team decision, not a customer answer (Q11) | Only the newest approved document is judged; the old one stays on file |

**What research did not get right.** I expected quality certificates to expire, and the customer said otherwise for their records. We built to the customer's answer. Dheepthi's section records this as an open question.

**Known limits.** The research also found things real systems have that this tool deliberately does not: the certificate's issuer and reference number, a supplier name (reports show the ID), days overdue, who reviewed a document, more than one supplier per part, and scheduled runs (the customer runs weekly, started by hand).

### Test cases for the demo

Each case below uses the committed synthetic data and comes from a real run of version 1.1.0 with `today` = 2026-10-26. On 1.0.0 the same data gives 7 flags, because the pending rule does not exist yet.

```bash
export PYTHONPATH=src COMPLIANCE_DB_PATH=/tmp/demo/compliance.db
python -m compliance run --documents data/documents.json --parts data/parts.json --settings data/settings.json
python -m compliance history SUP-103
```

The first run prints this summary: `Checked 8 suppliers and 9 parts: 4 suppliers with no issues, 4 parts at risk, 9 flags, 8 rejected records`.

| # | What it shows | Where to look | Expected |
|---|---|---|---|
| 1 | Clean supplier | `history SUP-101` | `no flags in any saved check` |
| 2 | Expired document | SUP-102 in the report | DOC-005 expired; `PRT-5002  SUP-102  expired safety_cert` |
| 3 | Expires today | DOC-008 in the report | Under **Expiring soon**, not Expired |
| 4 | At risk per part | SUP-103 in the report | PRT-5003 is at risk (`missing safety_cert`); PRT-5004, same supplier, is not |
| 5 | Supplier known only through a part | SUP-106 in the report | `PRT-5005  SUP-106  missing quality_cert; missing env_declaration` |
| 6 | Pending document (1.1.0) | SUP-105 in the report | DOC-013 `(pending)` under **Other**; `missing safety_cert` is added to PRT-5006 |
| 7 | Bad records | **Rejected records**; `history SUP-104` | 8 rejected, each with a reason; SUP-104 has `no saved record of this supplier` |
| 8 | History builds up | Run the same command twice | Header says `check 2`; documents stay at 19; flags go from 9 to 18 |
| 9 | Missing input file | `run --documents data/nope.json …` | `error: data/nope.json: file not found`, exit 1, no database created |
| 10 | Failed save leaves nothing | `pytest tests/test_storage.py::test_failed_check_save_rolls_back` | Passes: an at-risk part that was never saved makes the save fail, and no check or flags remain |
| 11 | Renewal clears the old flag | `pytest tests/test_engine.py::test_renewal_clears_at_risk` | Passes: with DOC-005-R1 added, DOC-005 is not flagged and PRT-5002 is not at risk |
| 12 | A day with no issues | `pytest tests/test_cli.py::test_run_summary_on_a_day_with_no_issues` | Passes: SUP-101's documents and PRT-5001 alone print `No issues found` |

Case 12 uses a clean subset on purpose. Changing `--today` alone does not give a clean report, because a missing document stays missing on any date.

#### Sources (this section)

| Source | Link | Used for |
|---|---|---|
| The Standards Navigator, Supplier Quality Requirements | https://thestandardsnavigator.com/2026/04/18/supplier-quality-requirements/ | Shipment evidence; filing without review |
| LeanLinking, Approved Supplier List | https://leanlinking.com/blogs/what-is-an-approved-supplier-list/ | Passive expiry cells in an AVL |
| GreenSoft, Refreshing Compliance Declarations | https://greensofttech.com/blog-2026-compliance-data-mgmt-in-practice-pt-1-refreshing-compliance-declarations/ | Suppliers not updating; refresh policy |
| CR4 / GlobalSpec, How long is a RoHS Certificate Valid for? | https://cr4.globalspec.com/thread/55713/How-long-is-a-RoHS-Certificate-Valid-for | No official expiry on RoHS declarations (forum discussion) |
| SKU.io, Track supplier certificates | https://www.sku.io/docs/guides/manufacturing/lot-compliance/track-supplier-certificates/ | Renewal as a new document; alert lead times |
| SAP Supplier Lifecycle Management, Certificate Status | https://help.sap.com/saphelp_slc200/helpdata/en/de/64bbd332d14155ad51166ddbecd26e/content.htm | Pending approval; 30-day warning |
| ISO 9001 Checklist, §8.4 | https://www.iso-9001-checklist.co.uk/8.4-control-of-externally-provided-processes-products-services.htm | What auditors look for |
| Quality Systems, Records required by ISO 9001:2015 | https://qualitysystems.com/support/learning/records-required-by-iso-90012015/ | No set retention period |
| Customer check-in | `docs/customer_questions.md` (Q1–Q6, Q9, Q11, Q12) | Every customer answer above |

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
