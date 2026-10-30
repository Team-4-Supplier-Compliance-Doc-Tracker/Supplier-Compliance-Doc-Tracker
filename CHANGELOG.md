# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- CI workflow (`.github/workflows/ci.yml`) running `pytest -q` on every PR and push to `main`.
- Dockerfile + `.dockerignore` with `COMPLIANCE_DB_PATH=/data/compliance.db` and `VOLUME /data`.
- `scripts/backup.py` (`Connection.backup` + `PRAGMA integrity_check`) and safe `scripts/restore.py` (verify backup, side-copy live DB before overwrite).
- Integration test: generator → CLI on synthetic files.

## [1.0.0] — TBD (REL-03)

### Added
- Load and validate `documents.json`, `parts.json`, and `settings.json`.
- Rules: expired, expiring soon, missing; per-part at-risk.
- SQLite history (`suppliers`, `parts`, `documents`, `compliance_checks`, `flags`, `at_risk_parts`).
- Plain-text report and CLI (`run`, `history`).
- Docker image `compliance-tracker:1.0.0` with history on a named volume.
- `status` stored on documents but unused by rules.

## [1.1.0] — TBD (REL-04)

### Added
- **PendingDocumentRule**: a clean document with `status == "pending"` gets flag `pending` (customer Q6 — pending / approved / missing view). Pending does not make a part at risk by itself; MissingDocumentRule treats pending as absent so the gap still surfaces.

[Unreleased]: https://github.com/Team-4-Supplier-Compliance-Doc-Tracker/Supplier-Compliance-Doc-Tracker/compare/HEAD...HEAD
[1.0.0]: https://github.com/Team-4-Supplier-Compliance-Doc-Tracker/Supplier-Compliance-Doc-Tracker/releases/tag/v1.0.0
[1.1.0]: https://github.com/Team-4-Supplier-Compliance-Doc-Tracker/Supplier-Compliance-Doc-Tracker/releases/tag/v1.1.0
