# Local web UI: `python -m compliance serve`. Standard library only, like the rest of the tool.
# The browser picks from fixed choices; it never sends a file path.

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
from datetime import date, timedelta
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import groupby
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from compliance import __version__, storage
from compliance.cli import _summary
from compliance.engine import run_rules
from compliance.loader import load_documents, load_parts, read_json_list
from compliance.models import InputFileError
from compliance.report import render_report
from compliance.settings import load_settings

INDEX_PATH = Path(__file__).with_name("static") / "index.html"
MAX_BODY_BYTES = 10_000
COOKIE_NAME = "compliance_session"
SESSION_SECONDS = 8 * 60 * 60
MAX_FAILED_LOGINS = 5
LOCK_SECONDS = 60
HASH_ROUNDS = 200_000
# The demo account for this machine. Only its salted hash is kept here, never the password.
DEFAULT_USER = "compliance.manager"
DEFAULT_SALT = "cf00191d15899dd380bee8a21ba156ee"
DEFAULT_HASH = "50a2d1e828146bad512c3abbf05cab9455d75b1a11a39b85dc6433c71e028958"
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
DOCUMENT_LABELS = {
    "quality_cert": "quality certificate",
    "safety_cert": "safety certificate",
    "env_declaration": "environmental declaration",
}
FLAG_TYPES = ["expired", "expiring_soon", "missing", "pending"]
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
DATASETS = {
    "sample": {
        "label": "Sample data",
        "description": "The full synthetic data set: every edge case from the plan, plus clean filler suppliers.",
        "documents": "documents.json",
        "parts": "parts.json",
        "can_save": True,
    },
    "renewal": {
        "label": "Sample + a renewal",
        "description": "Adds DOC-005-R1, a renewed safety certificate, next to the expired DOC-005. Preview only.",
        "documents": "scenarios/renewal_documents.json",
        "parts": "parts.json",
        "can_save": False,
    },
    "no_issues": {
        "label": "A day with no issues",
        "description": "Only SUP-101, which holds every document its part needs. Preview only.",
        "documents": "scenarios/no_issues_documents.json",
        "parts": "scenarios/no_issues_parts.json",
        "can_save": False,
    },
    "broken": {
        "label": "Broken input file",
        "description": "A documents file that is not valid JSON, to show the error handling. Preview only.",
        "documents": "scenarios/broken_documents.json",
        "parts": "parts.json",
        "can_save": False,
    },
}


class RequestError(Exception):
    # A problem with the request or its input; the message is safe to show in the browser.
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def _hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), HASH_ROUNDS).hex()


def load_credentials():
    # COMPLIANCE_UI_USER and COMPLIANCE_UI_PASSWORD replace the demo account. Returns (username, password check).
    password = os.environ.get("COMPLIANCE_UI_PASSWORD")
    if password:
        salt = secrets.token_hex(16)
        expected = _hash_password(password, salt)
    else:
        salt, expected = DEFAULT_SALT, DEFAULT_HASH
    username = os.environ.get("COMPLIANCE_UI_USER") or DEFAULT_USER
    return username, lambda attempt: hmac.compare_digest(_hash_password(attempt, salt), expected)


class Auth:
    # Sessions live in memory, so restarting the server signs everyone out.
    def __init__(self):
        self.username, self.check_password = load_credentials()
        self.lock = threading.Lock()
        self.sessions = {}
        self.failures = {}

    def sign_in(self, client, username, password):
        now = time.time()
        with self.lock:
            count, locked_until = self.failures.get(client, (0, 0))
            if now < locked_until:
                raise RequestError(429, "Too many failed attempts. Wait a minute, then try again.")
        valid_types = isinstance(username, str) and isinstance(password, str)
        matches = valid_types and self.check_password(password) and hmac.compare_digest(username.encode(), self.username.encode())
        with self.lock:
            if not matches:
                count = 1 if locked_until else count + 1
                self.failures[client] = (count, now + LOCK_SECONDS if count >= MAX_FAILED_LOGINS else 0)
                raise RequestError(401, "That username and password do not match.")
            self.failures.pop(client, None)
            token = secrets.token_urlsafe(32)
            self.sessions[token] = now + SESSION_SECONDS
        return token

    def is_signed_in(self, token):
        with self.lock:
            expires = self.sessions.get(token)
            if expires is None:
                return False
            if time.time() >= expires:
                del self.sessions[token]
                return False
            return True

    def sign_out(self, token):
        with self.lock:
            self.sessions.pop(token, None)


def _dataset(dataset_id):
    if not isinstance(dataset_id, str) or dataset_id not in DATASETS:
        raise RequestError(400, "Unknown data set. Choose one from the list.")
    return DATASETS[dataset_id]


def _load(data_dir, dataset):
    settings = load_settings(data_dir / "settings.json")
    documents, rejected_documents = load_documents(data_dir / dataset["documents"], settings)
    parts, rejected_parts = load_parts(data_dir / dataset["parts"], settings)
    return settings, documents, parts, rejected_documents + rejected_parts


def _iso(value):
    return value.isoformat() if value is not None else None


def _rejected_json(rejected):
    return [
        {
            "id": record.raw_id or f"record {record.index}",
            "supplier_id": record.supplier_id,
            "source": Path(record.source_file).name,
            "reason": record.reason,
        }
        for record in rejected
    ]


def _document_label(document_type):
    return DOCUMENT_LABELS.get(document_type, document_type.replace("_", " "))


def _days(count):
    return f"{count} day" if count == 1 else f"{count} days"


def _part_list(parts):
    return ", ".join(f"{part['part_number']} ({part['description']})" for part in parts)


def _draft(supplier_id, subject, problem, request, parts):
    affected = f"\nThis affects: {_part_list(parts)}.\n" if parts else "\n"
    return f"Subject: {subject}\n\nHello {supplier_id},\n\n{problem}\n{affected}\n{request}\n\nThank you."


def _flag_reminder(flag, today, affected):
    label = _document_label(flag.document_type)
    title_label = label.capitalize()
    supplier = flag.supplier_id
    reference = f" ({flag.document_id})" if flag.document_id else ""
    days = (flag.expiry_date - today).days if flag.expiry_date else None
    parts_note = "puts parts at risk" if affected else "does not affect any listed part"
    if flag.flag_type == "expired":
        severity = "action"
        title = f"{title_label} expired {_days(-days)} ago"
        why = f"Past its expiry date, which {parts_note}."
        subject = f"Expired {label} for {supplier}"
        problem = f"Our records show your {label}{reference} expired on {flag.expiry_date.isoformat()}."
        request = f"Please send a current {label}."
    elif flag.flag_type == "missing":
        severity = "action"
        title = f"No {label} on file"
        why = f"A listed part requires this document and none is on file, which {parts_note}."
        subject = f"Missing {label} for {supplier}"
        problem = f"We do not have a current {label} on file for you."
        request = f"Please send your {label}."
    elif flag.flag_type == "expiring_soon":
        severity = "soon"
        when = "today" if days == 0 else f"in {_days(days)}"
        title = f"{title_label} expires {when}"
        why = "Still valid, so nothing is at risk yet. These parts will be at risk if it lapses." if affected else "Still valid. No listed part requires it."
        subject = f"Renewal needed: {label} for {supplier}"
        problem = f"Your {label}{reference} expires on {flag.expiry_date.isoformat()}."
        request = f"Please send the renewed {label} before that date."
    elif flag.flag_type == "pending":
        severity = "review"
        title = f"{title_label} is waiting for approval"
        why = "Received but not approved yet, so it does not count as on file."
        subject = problem = request = None
    else:
        severity = "review"
        title = f"{flag.flag_type.replace('_', ' ').capitalize()}: {label}"
        why = "A flag type this version does not explain."
        subject = problem = request = None
    return {
        "severity": severity,
        "kind": flag.flag_type,
        "supplier_id": supplier,
        "document_type": flag.document_type,
        "document_id": flag.document_id,
        "expiry_date": _iso(flag.expiry_date),
        "days_until_expiry": days,
        "title": title,
        "why": why,
        "affected_parts": affected,
        "draft": _draft(supplier, subject, problem, request, affected) if subject else None,
    }


def _rejected_reminder(record):
    record_id = record.raw_id or f"Record {record.index}"
    source = Path(record.source_file).name
    is_document = source != "parts.json" and bool(record.supplier_id) and bool(record.raw_id)
    draft = None
    if is_document:
        draft = _draft(
            record.supplier_id,
            f"Please resend {record.raw_id}",
            f"We could not use a document you sent ({record.raw_id}). The reason: {record.reason}.",
            "Please send a corrected copy.",
            [],
        )
    return {
        "severity": "unreadable",
        "kind": "rejected",
        "supplier_id": record.supplier_id,
        "document_type": None,
        "document_id": record.raw_id or None,
        "expiry_date": None,
        "days_until_expiry": None,
        "title": f"{record_id} could not be used: {record.reason}",
        "why": f"This record in {source} was rejected and not saved. Fix or resend it.",
        "affected_parts": [],
        "draft": draft,
    }


def _reminders(flags, rejected, parts, settings, today):
    def affected(flag):
        return [
            {"part_number": part.part_number, "description": part.description}
            for part in parts
            if part.supplier_id == flag.supplier_id
            and flag.document_type in settings.required_documents.get(part.part_category, ())
        ]

    def urgency(reminder):
        days = reminder["days_until_expiry"]
        kind_rank = {"expired": 0, "missing": 1}.get(reminder["kind"], 0)
        return (kind_rank, days if days is not None else 0, reminder["supplier_id"], reminder["document_type"] or "")

    reminders = [_flag_reminder(flag, today, affected(flag)) for flag in flags]
    ordered = []
    for severity in ("action", "soon", "review"):
        ordered += sorted((r for r in reminders if r["severity"] == severity), key=urgency)
    return ordered + [_rejected_reminder(record) for record in rejected]


def options(data_dir):
    # What the dropdowns offer. Reads the input files only, never the database.
    settings = load_settings(data_dir / "settings.json")
    records = [
        *read_json_list(data_dir / DATASETS["sample"]["documents"]),
        *read_json_list(data_dir / DATASETS["sample"]["parts"]),
    ]
    suppliers = {record.get("supplier_id") for record in records if isinstance(record, dict)}
    base = settings.today or date.today()
    choices = [
        (base, "settings date"),
        (base - timedelta(days=180), "180 days earlier"),
        (base + timedelta(days=30), "30 days later"),
        (base + timedelta(days=60), "60 days later"),
        (base + timedelta(days=365), "1 year later"),
        (date.today(), "the real date today"),
    ]
    unique = {}
    for value, label in choices:
        unique.setdefault(value.isoformat(), label)
    return {
        "version": __version__,
        "datasets": [
            {"id": key, "label": d["label"], "description": d["description"], "can_save": d["can_save"]}
            for key, d in DATASETS.items()
        ],
        "dates": [{"value": value, "label": f"{value} ({label})"} for value, label in unique.items()],
        "default_as_of": base.isoformat(),
        "suppliers": sorted(s for s in suppliers if isinstance(s, str) and s.strip()),
        "flag_types": FLAG_TYPES,
    }


def _parse_as_of(value):
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        raise RequestError(400, "Choose a valid date from the list.")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise RequestError(400, "Choose a valid date from the list.") from None


def run_check(data_dir, body, db_lock):
    if not isinstance(body, dict):
        raise RequestError(400, "The request must be a JSON object.")
    dataset = _dataset(body.get("dataset"))
    save = body.get("save", False)
    if not isinstance(save, bool):
        raise RequestError(400, "The save option must be true or false.")
    if save and not dataset["can_save"]:
        raise RequestError(400, "Scenarios are preview only: only the sample data can be saved to history.")
    as_of = _parse_as_of(body["as_of"]) if body.get("as_of") is not None else None

    settings, documents, parts, rejected = _load(data_dir, dataset)
    today = as_of or settings.today or date.today()
    flags, at_risk = run_rules(documents, parts, settings, today)

    check_id = None
    if save:
        with db_lock:
            conn = storage.connect()
            storage.init_schema(conn)
            storage.save_documents(conn, documents)
            storage.save_parts(storage.connect(), parts)
            check_id = storage.save_check(storage.connect(), today, __version__, flags, at_risk)

    where = f"check {check_id}" if save else "preview, not saved"
    report_text = (
        f"Compliance report as of {today.isoformat()} (tool {__version__}, {where})\n"
        f"{_summary(documents, parts, flags, at_risk, rejected)}\n\n"
        f"{render_report(flags, at_risk, rejected)}"
    )
    suppliers = {item.supplier_id for item in [*documents, *parts]}
    parts_by_number = {part.part_number: part for part in parts}
    return {
        "as_of": today.isoformat(),
        "version": __version__,
        "saved": save,
        "check_id": check_id,
        "counts": {
            "suppliers": len(suppliers),
            "clean_suppliers": len(suppliers - {flag.supplier_id for flag in flags}),
            "parts": len(parts),
            "at_risk": len(at_risk),
            "flags": len(flags),
            "rejected": len(rejected),
        },
        "flags": [
            {
                "flag_type": flag.flag_type,
                "supplier_id": flag.supplier_id,
                "document_type": flag.document_type,
                "document_id": flag.document_id,
                "expiry_date": _iso(flag.expiry_date),
                "days_until_expiry": (flag.expiry_date - today).days if flag.expiry_date else None,
            }
            for flag in sorted(flags, key=lambda f: (f.supplier_id, f.document_type, f.flag_type))
        ],
        "at_risk": [
            {
                "part_number": part.part_number,
                "description": parts_by_number[part.part_number].description,
                "part_category": parts_by_number[part.part_number].part_category,
                "supplier_id": part.supplier_id,
                "reasons": list(part.reasons),
            }
            for part in sorted(at_risk, key=lambda p: p.part_number)
        ],
        "rejected": _rejected_json(rejected),
        "reminders": _reminders(flags, rejected, parts, settings, today),
        "report_text": report_text,
    }


def supplier_history(supplier_id, db_lock):
    if not supplier_id:
        raise RequestError(400, "Choose a supplier.")
    with db_lock:
        conn = storage.connect()
        storage.init_schema(conn)
        rows = storage.supplier_history(conn, supplier_id)
        known = rows or storage.supplier_known(storage.connect(), supplier_id)
    checks = []
    for check_id, check_rows in groupby(rows, key=lambda row: row["check_id"]):
        check_rows = list(check_rows)
        first = check_rows[0]
        checks.append({
            "check_id": check_id,
            "as_of_date": first["as_of_date"],
            "run_at": first["run_at"],
            "tool_version": first["tool_version"],
            "flags": [
                {key: row[key] for key in ("flag_type", "document_type", "document_id", "expiry_date")}
                for row in check_rows
            ],
        })
    status = "flags" if rows else ("clean" if known else "not_saved")
    return {"supplier_id": supplier_id, "status": status, "checks": checks}


def input_data(data_dir, dataset_id):
    settings, documents, parts, rejected = _load(data_dir, _dataset(dataset_id))
    return {
        "documents": [
            {
                "document_id": doc.document_id,
                "supplier_id": doc.supplier_id,
                "document_type": doc.document_type,
                "issue_date": _iso(doc.issue_date),
                "expiry_date": _iso(doc.expiry_date),
                "status": doc.status,
            }
            for doc in documents
        ],
        "parts": [
            {
                "part_number": part.part_number,
                "description": part.description,
                "part_category": part.part_category,
                "supplier_id": part.supplier_id,
            }
            for part in parts
        ],
        "rejected": _rejected_json(rejected),
        "settings": {
            "today": _iso(settings.today),
            "expiring_soon_days": settings.expiring_soon_days,
            "expiring_types": list(settings.expiring_types),
            "required_documents": {key: list(value) for key, value in settings.required_documents.items()},
        },
    }


def _short_path_message(error, data_dir):
    # Names the file from the data folder down, so a shared screen does not show someone's home folder.
    return str(error).replace(str(data_dir), data_dir.name, 1)


class Handler(BaseHTTPRequestHandler):
    server_version = "compliance"
    sys_version = ""

    def log_message(self, format, *args):
        pass    # keep the terminal clean during a demo; failures are printed in _guarded

    def _send(self, status, body, content_type, cookie=None):
        self.send_response(status)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, payload, cookie=None):
        self._send(status, json.dumps(payload).encode(), "application/json; charset=utf-8", cookie)

    def _session_token(self):
        cookies = SimpleCookie()
        try:
            cookies.load(self.headers.get("Cookie", ""))
        except Exception:
            return None
        morsel = cookies.get(COOKIE_NAME)
        return morsel.value if morsel else None

    def _signed_in(self):
        return self.server.auth.is_signed_in(self._session_token())

    def _require_session(self):
        if not self._signed_in():
            raise RequestError(401, "Sign in to continue.")

    def _guarded(self, handle):
        # Every failure becomes a JSON message, so the page can show it and carry on.
        try:
            handle()
        except RequestError as error:
            self._json(error.status, {"error": str(error)})
        except InputFileError as error:
            self._json(400, {"error": _short_path_message(error, self.server.data_dir)})
        except sqlite3.Error as error:
            print(f"database error: {error}", file=sys.stderr)
            self._json(500, {"error": f"The database could not be used: {error}"})
        except (BrokenPipeError, ConnectionResetError):
            pass    # the browser went away
        except Exception as error:
            print(f"unexpected error: {error!r}", file=sys.stderr)
            self._json(500, {"error": "Something went wrong on the server. See the terminal for details."})

    def _read_json_body(self):
        content_type = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type != "application/json":
            raise RequestError(415, "Requests must use application/json.")
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.headers.get("Host"):
            raise RequestError(403, "Requests from another site are not allowed.")
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            raise RequestError(411, "The request has no length.") from None
        if length > MAX_BODY_BYTES:
            raise RequestError(413, "The request is too large.")
        try:
            return json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            raise RequestError(400, "The request is not valid JSON.") from None

    def do_GET(self):
        self._guarded(self._handle_get)

    def do_POST(self):
        self._guarded(self._handle_post)

    def _handle_get(self):
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        data_dir, db_lock = self.server.data_dir, self.server.db_lock
        if url.path == "/":
            self._send(200, INDEX_PATH.read_bytes(), "text/html; charset=utf-8")
            return
        if url.path == "/api/session":
            signed_in = self._signed_in()
            self._json(200, {"authenticated": True, "username": self.server.auth.username} if signed_in else {"authenticated": False})
            return
        if url.path in ("/api/options", "/api/history", "/api/data"):
            self._require_session()
        if url.path == "/api/options":
            self._json(200, options(data_dir))
        elif url.path == "/api/history":
            self._json(200, supplier_history(query.get("supplier", [""])[0], db_lock))
        elif url.path == "/api/data":
            self._json(200, input_data(data_dir, query.get("dataset", [""])[0]))
        elif url.path == "/api/run":
            raise RequestError(405, "Use POST to run a check.")
        else:
            raise RequestError(404, "Not found.")

    def _handle_post(self):
        path = urlsplit(self.path).path
        if path == "/api/login":
            body = self._read_json_body()
            if not isinstance(body, dict):
                raise RequestError(400, "The request must be a JSON object.")
            auth = self.server.auth
            token = auth.sign_in(self.client_address[0], body.get("username"), body.get("password"))
            cookie = f"{COOKIE_NAME}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}"
            self._json(200, {"authenticated": True, "username": auth.username}, cookie)
        elif path == "/api/logout":
            self._read_json_body()
            self.server.auth.sign_out(self._session_token())
            self._json(200, {"authenticated": False}, f"{COOKIE_NAME}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
        elif path == "/api/run":
            self._require_session()
            self._json(200, run_check(self.server.data_dir, self._read_json_body(), self.server.db_lock))
        else:
            raise RequestError(404, "Not found.")


def build_server(host, port, data_dir):
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.data_dir = Path(data_dir)
    server.db_lock = threading.Lock()
    server.auth = Auth()
    return server


def serve(host, port, data_dir) -> int:
    if host not in LOOPBACK_HOSTS and not os.environ.get("COMPLIANCE_UI_PASSWORD"):
        print("error: to listen beyond this machine, set your own COMPLIANCE_UI_PASSWORD first", file=sys.stderr)
        return 1
    try:
        server = build_server(host, port, data_dir)
    except OSError as error:
        print(f"error: cannot start on {host}:{port}: {error}", file=sys.stderr)
        return 1
    print(f"Compliance UI running at http://{host}:{server.server_address[1]}  (press Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        server.server_close()
    return 0
