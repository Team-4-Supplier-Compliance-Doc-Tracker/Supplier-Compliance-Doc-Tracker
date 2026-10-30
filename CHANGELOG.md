# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- (nothing yet — 1.1.0 PendingDocumentRule lands after RULE-03 merges)

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

## [1.1.0] — TBD (REL-04)

### Added
- **PendingDocumentRule**: a clean document with `status == "pending"` gets flag `pending` (customer Q6 — pending / approved / missing view). Pending does not make a part at risk by itself; MissingDocumentRule treats pending as absent so the gap still surfaces.

[Unreleased]: https://github.com/Team-4-Supplier-Compliance-Doc-Tracker/Supplier-Compliance-Doc-Tracker/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Team-4-Supplier-Compliance-Doc-Tracker/Supplier-Compliance-Doc-Tracker/releases/tag/v1.0.0
[1.1.0]: https://github.com/Team-4-Supplier-Compliance-Doc-Tracker/Supplier-Compliance-Doc-Tracker/releases/tag/v1.1.0
