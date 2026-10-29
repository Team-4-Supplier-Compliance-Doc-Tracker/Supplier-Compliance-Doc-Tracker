CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS parts (
    part_number   TEXT PRIMARY KEY,
    description   TEXT NOT NULL,
    part_category TEXT NOT NULL,
    supplier_id   TEXT NOT NULL REFERENCES suppliers (supplier_id)
);

CREATE TABLE IF NOT EXISTS documents (
    document_id   TEXT PRIMARY KEY,
    supplier_id   TEXT NOT NULL REFERENCES suppliers (supplier_id),
    document_type TEXT NOT NULL,
    issue_date    TEXT NOT NULL,
    expiry_date   TEXT,
    status        TEXT NOT NULL DEFAULT 'approved'
);

CREATE TABLE IF NOT EXISTS compliance_checks (
    check_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at       TEXT NOT NULL,
    as_of_date   TEXT NOT NULL,
    tool_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS flags (
    flag_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    check_id      INTEGER NOT NULL REFERENCES compliance_checks (check_id),
    flag_type     TEXT NOT NULL,
    supplier_id   TEXT NOT NULL REFERENCES suppliers (supplier_id),
    document_id   TEXT REFERENCES documents (document_id),
    document_type TEXT NOT NULL,
    expiry_date   TEXT
);

CREATE TABLE IF NOT EXISTS at_risk_parts (
    check_id    INTEGER NOT NULL REFERENCES compliance_checks (check_id),
    part_number TEXT NOT NULL REFERENCES parts (part_number),
    supplier_id TEXT NOT NULL REFERENCES suppliers (supplier_id),
    reasons     TEXT NOT NULL,
    PRIMARY KEY (check_id, part_number)
);
