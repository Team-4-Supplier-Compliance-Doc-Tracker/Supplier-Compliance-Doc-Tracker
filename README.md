# Supplier Compliance Document Tracker

A command-line tool, shipped in a Docker container, that tracks supplier compliance documents, flags the ones that are expired, expiring soon, or missing, marks the parts at risk, and keeps a history in SQLite.

**Team 4:** Dheepthi Reddy (intake, validation, rules) · Nikita Ravi (SQLite storage, report, CLI) · Vedanshu Daxesh Patel (Docker, release, CI, README)

Status: Week 3 team project, CoForge Associate FDE Training. Releases 1.0.0 and 1.1.0 ship Friday.

---

## The problem

A hardware maker buys parts from dozens of suppliers. Each supplier must keep compliance documents current — a quality certificate, a safety certificate, an environmental declaration. Today those documents sit in email attachments and shared folders. Certificates expire unnoticed, some were never received, and nobody can say which parts are affected until an auditor asks.

This tool reads one list of what is on file and answers three questions: which documents have problems, which parts are affected, and what did we know last time.

**The tool flags and reports. It never approves a supplier, blocks an order, or decides a part cannot be used. The compliance manager decides.**

Out of scope: reading emails, opening PDFs, extracting data from attachments. The tool starts from an already-extracted list.

---

## Shared decisions

Agreed Monday. Do not change without team consensus.

### 1. Input files

All three inputs are JSON. One parser, no CSV loader.

| File | Shape |
|---|---|
| `documents.json` | top-level **list** of flat objects |
| `parts.json` | top-level **list** of flat objects |
| `settings.json` | single object |

Two failure levels:
- **File-level** — the file is missing, is not valid JSON, or has the wrong top-level shape. Clear error naming the file, exit code 1, nothing processed.
- **Record-level** — the file parsed but one object has a bad value. That object is rejected with a reason; every other object still loads. A rejected record keeps its `supplier_id` when it has one, so the report can tie it to that supplier's flags (e.g. DOC-015 rejected → SUP-105 shows env_declaration missing).

### 2. Document record

```json
{
  "document_id": "DOC-005",
  "supplier_id": "SUP-102",
  "document_type": "safety_cert",
  "issue_date": "2025-06-01",
  "expiry_date": "2026-06-01",
  "status": "approved"
}
```

| Key | Type | Rule |
|---|---|---|
| `document_id` | string | required, unique |
| `supplier_id` | string | required; `""`, `null`, or absent key → rejected "missing supplier ID" |
| `document_type` | string | must be in `settings.document_types`, else rejected "unknown document type" |
| `issue_date` | `YYYY-MM-DD` string | required; unparseable or non-string → rejected "invalid date" |
| `expiry_date` | `YYYY-MM-DD` string or `null` | `null` allowed only when the type is **not** in `settings.expiring_types`; `null` on an expiring type, unparseable, or non-string → rejected "invalid date" |
| `status` | `"approved"` or `"pending"` | optional, defaults to `"approved"`; any other value → rejected "unknown status". Stored from 1.0.0, acted on by the 1.1.0 rule |

Records are flat. Documents are never nested under suppliers. Extra keys are ignored.

### 3. Part record

```json
{
  "part_number": "PRT-5002",
  "description": "Monitor power switch",
  "part_category": "electrical",
  "supplier_id": "SUP-102"
}
```

| Key | Type | Rule |
|---|---|---|
| `part_number` | string | required, unique |
| `description` | string | required |
| `part_category` | string | must be a key in `settings.required_documents`, else rejected "unknown part category" |
| `supplier_id` | string | required; same missing rule as documents |

### 4. Settings file

```json
{
  "today": "2026-10-26",
  "expiring_soon_days": 45,
  "document_types": ["quality_cert", "safety_cert", "env_declaration"],
  "expiring_types": ["safety_cert", "env_declaration"],
  "required_documents": {
    "cables":         ["quality_cert", "safety_cert", "env_declaration"],
    "mechanical":     ["quality_cert", "env_declaration"],
    "electrical":     ["quality_cert", "safety_cert", "env_declaration"],
    "semiconductors": ["quality_cert", "env_declaration"]
  }
}
```

All five keys are required. The compliance manager changes required documents, expiring types, or the warning window here, never in code.

- Safety certificates are required only for **cables** and **electrical**: mains-rated parts fall under UL 61058-1 / the CE Low Voltage Directive; mechanical parts and low-voltage logic do not.
- `expiring_types` leaves out `quality_cert` because the customer says quality certificates have no expiry. `safety_cert` is in the list pending Q8 (UL listings need annual factory audits, so we assume they expire).

### 5. How the tool knows today's date

Precedence, highest first:

1. `--today YYYY-MM-DD` on the command line
2. `today` in `settings.json`
3. The real system date

Tests always pass a fixed date, so results never change.

### 6. Flag definitions

With `today` resolved as above and `N = expiring_soon_days`. Rules that compare dates skip documents whose `expiry_date` is `null`.

| Flag | Definition | Example (today = 2026-10-26, N = 45) |
|---|---|---|
| **expired** | `expiry_date < today` | DOC-005, expiry 2026-06-01 |
| **expiring soon** | `today <= expiry_date <= today + N` | DOC-006, expiry 2026-11-20 |
| **missing** | a part's category requires a document type and the part's supplier has no clean document of that type (from 1.1.0: no clean, **approved** document) | SUP-103 supplies an electrical part but has no `safety_cert` |
| **pending** (1.1.0) | a clean document with `status == "pending"` | DOC-013 |
| **at risk** (part) | the part's supplier has an **expired** or **missing** document **of a type that part's category requires** | PRT-5003 (electrical, needs safety) is at risk; PRT-5004 (semiconductors, same supplier, no safety needed) is not |

**Expiry date equal to today → expiring soon, not expired.** A document is valid through its expiry date.

**A renewal replaces the document before it.** Expired and expiring soon judge only the newest document (latest `issue_date`) per supplier and type, so an old cert kept on file for audit is not flagged once it has been renewed.

**Expiring soon and pending never make a part at risk.** They are warnings only. (In 1.1.0 a supplier whose only safety cert is pending also gets a **missing** flag, and that missing flag does count.)

A **bad record** (broken object, rejected, never saved) is different from a **flagged document** (valid object, saved, with a compliance problem).

### 7. Database

Environment variable: **`COMPLIANCE_DB_PATH`**. Default `./data/compliance.db`. In Docker the directory is a mounted volume.

```
suppliers          supplier_id PK
parts              part_number PK, description, part_category, supplier_id FK→suppliers
documents          document_id PK, supplier_id FK→suppliers, document_type, issue_date,
                   expiry_date (NULL allowed), status
compliance_checks  check_id PK autoincrement, run_at, as_of_date, tool_version
flags              flag_id PK autoincrement, check_id FK→compliance_checks, flag_type,
                   supplier_id FK→suppliers, document_id FK→documents (NULL for missing),
                   document_type, expiry_date (NULL allowed)
at_risk_parts      check_id FK→compliance_checks, part_number FK→parts,
                   supplier_id FK→suppliers, reasons          PK (check_id, part_number)
```

- `PRAGMA foreign_keys = ON` at the start of every connection.
- Dates stored as ISO text.
- A batch of documents is saved in one transaction. A batch of parts is saved in one transaction. A compliance check, all of its flags, and all of its at-risk parts are saved in one transaction. A failure leaves nothing half-saved.
- A `document_id` that already exists on save is **skipped**: saving the same batch twice is a no-op (decided 2026-10-28). A `part_number` that already exists is skipped the same way.
- A flag describes one document or gap (`flags` has no part column). At-risk is a fact about a part, so it has its own table, one row per part per check. The CLI saves documents and parts before running the rules, so every at-risk row points at a saved part.
- `reasons` holds display-ready strings of the form `<flag_type> <document_type>`, joined with `; ` (for example `missing quality_cert; missing env_declaration`). The report prints them as stored.

### 8. Releases

- **1.0.0** — expired, expiring soon, missing; at risk per part; `status` stored but unused.
- **1.1.0** — adds one rule, **PendingDocumentRule**: a clean document with `status == "pending"` gets the flag `pending`, because the customer asked for a pending / approved / missing view (Q6). It is a flag, not a rejection, and does not make a part at risk.

### 9. Friday presentation

- Screen sharer and demo driver: **Vedanshu** (same person for both, so the screen never changes hands)
- Order: Title → Dheepthi (intake, validation, rules) → Nikita (storage, report, CLI) → Vedanshu (container, releases, CI) → live demo → questions.
- The page lives in `presentation/index.html`. Each person adds their section on their own branch and merges by PR.

---

## Repository structure

```
supplier-compliance-tracker/
├── README.md                     ← this file
├── CHANGELOG.md
├── pyproject.toml                ← package metadata, version, pytest config
├── requirements.txt              ← faker, pytest
├── Dockerfile
├── .dockerignore
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml                ← pytest on every PR and push to main
├── src/
│   └── compliance/
│       ├── __init__.py           ← __version__
│       ├── __main__.py           ← `python -m compliance` → cli.main()
│       ├── models.py             ← SupplierDocument, Part, RejectedRecord, Flag, AtRiskPart, InputFileError
│       ├── rules_base.py         ← ComplianceRule base class + rule registry
│       ├── rules/
│       │   ├── __init__.py
│       │   ├── expired.py        ← ExpiredRule
│       │   ├── expiring_soon.py  ← ExpiringSoonRule
│       │   ├── missing.py        ← MissingDocumentRule
│       │   └── validity_window.py ← ExpiryBeforeIssueRule (1.1.0)
│       ├── settings.py           ← load_settings()
│       ├── loader.py             ← read_json_list(), load_documents(), load_parts()
│       ├── engine.py             ← run_rules()
│       ├── storage.py            ← connect(), init_schema(), save_documents(), save_parts(), save_check(), supplier_history(), parts_at_risk()
│       ├── schema.sql
│       ├── report.py             ← render_report()
│       └── cli.py                ← main(): `run`, `history`
├── scripts/
│   ├── generate_data.py          ← synthetic data, seeded
│   ├── backup.py                 ← Connection.backup + PRAGMA integrity_check
│   └── restore.py
├── data/                         ← generated inputs (committed); *.db ignored
│   ├── documents.json
│   ├── parts.json
│   └── settings.json
├── tests/
│   ├── conftest.py               ← shared fixtures: today, settings, sample_docs, sample_parts, tmp_db, data_dir
│   ├── test_generator.py
│   ├── test_settings.py
│   ├── test_loader.py
│   ├── test_rules.py
│   ├── test_engine.py
│   ├── test_storage.py
│   ├── test_report.py
│   ├── test_cli.py
│   ├── test_backup.py
│   └── test_integration.py
├── docs/
│   ├── plan.md                   ← full plan: edge cases, contracts, test plan, timeline
│   ├── linear_issues.md          ← ticket definitions (source of truth for the board)
│   └── release.md                ← release, rollback, backup, restore procedure
└── presentation/
    └── index.html                ← Friday web page
```

Ownership:

| Path | Owner |
|---|---|
| `models.py`, `rules_base.py`, `conftest.py` | shared, created in the contract PR |
| `settings.py`, `loader.py`, `rules/`, `engine.py`, `scripts/generate_data.py`, their tests | Dheepthi |
| `storage.py`, `schema.sql`, `report.py`, `cli.py`, `__main__.py`, their tests | Nikita |
| `Dockerfile`, `.dockerignore`, `.github/`, `scripts/backup.py`, `scripts/restore.py`, `CHANGELOG.md`, `docs/release.md`, `test_integration.py`, `test_backup.py` | Vedanshu |

---

## Ground rules for data

Synthetic data only. Every supplier, part, document, and date is generated by `scripts/generate_data.py`. No real company names, certificates, or contract information, even in tests.

---

## Build and run (Docker)

The image is replaceable; the SQLite history lives on a named volume at `/data`.

```bash
docker build -t compliance-tracker:1.0.0 .

docker run --rm \
  -v compliance-data:/data \
  -v "$PWD/data":/input \
  compliance-tracker:1.0.0 \
  run --documents /input/documents.json --parts /input/parts.json --settings /input/settings.json
```

`COMPLIANCE_DB_PATH` defaults to `/data/compliance.db` inside the container. Locally, the same env var defaults to `./data/compliance.db`.

### History survives `docker rm`

The named volume keeps the database after the container is removed. Verify by writing a marker under `/data`, removing the container (`--rm`), then reading it back from a new container on the same volume:

```bash
docker volume create compliance-data
docker build -t compliance-tracker:1.0.0 .

docker run --rm -v compliance-data:/data --entrypoint sh compliance-tracker:1.0.0 \
  -c 'printf "history-check\n" > /data/volume-check.txt && cat /data/volume-check.txt'

docker run --rm -v compliance-data:/data --entrypoint sh compliance-tracker:1.0.0 \
  -c 'cat /data/volume-check.txt'
```

Both runs must print `history-check`. A temporary `--entrypoint sh` is used until CLI-01 lands; after that, the same volume holds `compliance.db` across `docker rm`.

**Hand-check output** (2026-10-29):

```text
$ docker volume create compliance-data
compliance-data

$ docker build -t compliance-tracker:1.0.0 .
...
Successfully tagged compliance-tracker:1.0.0

$ docker run --rm -v compliance-data:/data --entrypoint sh compliance-tracker:1.0.0 \
    -c 'printf "history-check\n" > /data/volume-check.txt && cat /data/volume-check.txt'
history-check

$ docker run --rm -v compliance-data:/data --entrypoint sh compliance-tracker:1.0.0 \
    -c 'cat /data/volume-check.txt'
history-check
```

---

## CI

Every pull request and every push to `main` runs `.github/workflows/ci.yml`: install `requirements.txt`, then `pytest -q`. A failing test turns the check red.

**Branch protection (required for Friday):** on GitHub → Settings → Branches → protect `main` → require status check **`CI / pytest`** before merge. No direct commits to `main`.

---

## Development workflow

Matches the course rules graded under technical work:

- Feature branch per ticket: `<name>/<ticket>-desc` (example: `vedanshu/CI-01-ci-docker`).
- Merge by pull request only. Put your name in every commit message (and use your git user name).
- Paste the PR link into the matching Linear ticket.
- Pull `main` daily; resolve conflicts on your branch before asking for review.
- Synthetic data only. No secrets in the repo (`.env` stays gitignored if keys ever appear).
- Shared decisions in this README change only by team consensus; judgment calls go in `docs/assumptions_log.md` the same day.