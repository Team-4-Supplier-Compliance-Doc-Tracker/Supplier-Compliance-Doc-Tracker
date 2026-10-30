# Release, rollback, backup, and restore

Owner: Vedanshu Daxesh Patel. Follow this for REL-03 (`v1.0.0`) and REL-04 (`v1.1.0`).

## Version bump

Bump the version in **both** places so the CLI header and package metadata match:

1. `src/compliance/__init__.py` → `__version__ = "X.Y.Z"`
2. `pyproject.toml` → `version = "X.Y.Z"`

Add a dated section under that version in `CHANGELOG.md`. Move items out of **Unreleased** as needed.

## Git tag (you run these)

After the release PR is merged to `main` and CI is green:

```bash
git checkout main
git pull
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0
```

Use `v1.1.0` the same way for the second release. Do **not** retag; fix forward with a new version if something is wrong.

## Docker image with a pinned tag

```bash
docker build -t compliance-tracker:1.0.0 .
# later:
docker build -t compliance-tracker:1.1.0 .
```

Always run with the named volume so history outlives the image:

```bash
docker run --rm \
  -v compliance-data:/data \
  -v "$PWD/data":/input \
  compliance-tracker:1.0.0 \
  run --documents /input/documents.json \
      --parts /input/parts.json \
      --settings /input/settings.json \
      --today 2026-10-26
```

## Rollback

Rollback means **run the previous image tag against the same volume**. The database schema is additive; older images can still read history written by newer ones (unknown flag types print under **Other** in the report).

```bash
# After using 1.1.0 for a while, roll back to 1.0.0:
docker run --rm -v compliance-data:/data compliance-tracker:1.0.0 history SUP-103
```

Confirm:

1. `history` still lists every check (including ones created under 1.1.0).
2. `PRAGMA integrity_check` on a backup of the volume DB returns `ok`.
3. For the Friday demo (R18): 1.0.0’s report prints a `pending` flag under **Other**.

## Backup

Prefer writing backups to a **host** folder, not only the data volume.

Local:

```bash
python scripts/backup.py --db data/compliance.db --out-dir data/backups
```

Docker:

```bash
mkdir -p "$PWD/backups"
docker run --rm \
  -v compliance-data:/data \
  -v "$PWD/backups":/backups \
  --entrypoint python \
  compliance-tracker:1.0.0 \
  /app/scripts/backup.py --db /data/compliance.db --out-dir /backups
```

The script uses `sqlite3.Connection.backup()`, runs `PRAGMA integrity_check` on the copy, and exits non-zero unless the result is `ok`. **Retention: keep backups 10 years** (customer Q12); the script never prunes.

## Restore

Restore verifies the backup with `integrity_check` first. If a live DB exists, it is copied aside as `*.before-restore-<timestamp>` before overwrite.

```bash
python scripts/restore.py data/backups/compliance-YYYYMMDDTHHMMSSZ.db --db data/compliance.db
```

## Release 1.0.0 status (REL-03, 2026-10-30)

- Version **1.0.0** set in `src/compliance/__init__.py` and `pyproject.toml`.
- `CHANGELOG.md` dated **2026-10-30** for 1.0.0.
- Full suite green: **115 passed** (integration test not xfailed — CLI-01 already on main).
- Image built: `compliance-tracker:1.0.0` (reports `compliance.__version__ == "1.0.0"`).
- **You still create and push the git tag** after this PR merges:

```bash
git checkout main && git pull
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0
```

Then comment on Linear **RULE-03** that the 1.1.0 rule may merge (see paste text in the REL-03 PR).

## Throwaway-tag rehearsal (REL-02, 2026-10-30)

Image-tag rollback was rehearsed locally without touching git:

```text
$ docker build -t compliance-tracker:rel02-rehearsal .
$ docker build -t compliance-tracker:1.0.0 .

$ docker run --rm -v compliance-data:/data -v "$PWD/data":/input \
    compliance-tracker:1.0.0 \
    run --documents /input/documents.json --parts /input/parts.json \
        --settings /input/settings.json --today 2026-10-26
Compliance report as of 2026-10-26 (tool 0.1.0, check 1)
...

$ docker run --rm -v compliance-data:/data compliance-tracker:rel02-rehearsal history SUP-103
History for SUP-103
Check 1  as of 2026-10-26  (tool 0.1.0, run 2026-10-30T18:07:54+00:00)
  expiring_soon  env_declaration  2026-10-26  DOC-008
  missing  safety_cert  —

$ docker run --rm -v compliance-data:/data compliance-tracker:1.0.0 history SUP-103
History for SUP-103
Check 1  as of 2026-10-26  (tool 0.1.0, run 2026-10-30T18:07:54+00:00)
  expiring_soon  env_declaration  2026-10-26  DOC-008
  missing  safety_cert  —
```

Same volume, two image tags, history unchanged → this is the rollback pattern for Friday.
