# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- (none)

## [1.1.0] — 2026-11-02

### Added
- **PendingDocumentRule**: a clean document with `status == "pending"` gets flag `pending`.
  Chosen because the customer asked for a pending / approved / missing view (Q6). It is a
  warning only and does not make a part at risk by itself.
- **MissingDocumentRule** (updated): a pending document counts as absent, so a supplier whose
  only safety cert is still pending also gets a `missing` flag (and that missing flag can put
  requiring parts at risk).
- Docker image `compliance-tracker:1.1.0`. Rollback to `1.0.0` keeps history on the same volume;
  1.0.0 prints `pending` under **Other**.

## [1.0.0] — 2026-10-30

### Added
- Load and validate `documents.json`, `parts.json`, and `settings.json` with clear file-level and record-level errors.
- Rules: expired, expiring soon, missing; per-part at-risk (only when the gap is on a type that part's category requires).
- SQLite history (`suppliers`, `parts`, `documents`, `compliance_checks`, `flags`, `at_risk_parts`) with foreign keys and transactional saves.
- Plain-text report and CLI (`run`, `history`); `status` stored on documents but unused by rules.
- CI workflow (`.github/workflows/ci.yml`) running `pytest -q` on every PR and push to `main`.
- Dockerfile + `.dockerignore` with `COMPLIANCE_DB_PATH=/data/compliance.db` and `VOLUME /data`.
- `scripts/backup.py` (`Connection.backup` + `PRAGMA integrity_check`) and safe `scripts/restore.py` (verify backup, side-copy live DB before overwrite).
- Integration test: generator → CLI on synthetic files.
- Docker image `compliance-tracker:1.0.0` with history on a named volume.

[Unreleased]: https://github.com/Team-4-Supplier-Compliance-Doc-Tracker/Supplier-Compliance-Doc-Tracker/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/Team-4-Supplier-Compliance-Doc-Tracker/Supplier-Compliance-Doc-Tracker/releases/tag/v1.1.0
[1.0.0]: https://github.com/Team-4-Supplier-Compliance-Doc-Tracker/Supplier-Compliance-Doc-Tracker/releases/tag/v1.0.0
