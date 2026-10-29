# Command-line entry point: `run` and `history <supplier_id>`.

import argparse
import sys
from datetime import date
from itertools import groupby

from compliance import __version__, storage
from compliance.engine import run_rules
from compliance.loader import load_documents, load_parts
from compliance.models import InputFileError
from compliance.report import NO_EXPIRY, render_report
from compliance.settings import load_settings


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.command(args)
    except InputFileError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def _parser():
    parser = argparse.ArgumentParser(prog="compliance", description="Supplier compliance document tracker.")
    commands = parser.add_subparsers(required=True, metavar="command")

    run = commands.add_parser("run", help="check the input files, save the result and print the report")
    run.add_argument("--documents", required=True, help="documents.json")
    run.add_argument("--parts", required=True, help="parts.json")
    run.add_argument("--settings", required=True, help="settings.json")
    run.add_argument("--today", type=_iso_date, help="YYYY-MM-DD; overrides today in settings.json")
    run.set_defaults(command=_run)

    history = commands.add_parser("history", help="print every saved check's flags for one supplier")
    history.add_argument("supplier_id")
    history.set_defaults(command=_history)
    return parser


def _iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value!r}") from None


def _run(args):
    # Read and validate every input before touching the database, so a bad file leaves no trace.
    settings = load_settings(args.settings)
    documents, rejected_documents = load_documents(args.documents, settings)
    parts, rejected_parts = load_parts(args.parts, settings)
    today = args.today or settings.today or date.today()

    conn = storage.connect()
    storage.init_schema(conn)
    # Each save closes its connection, so every call gets a fresh one.
    storage.save_documents(conn, documents)
    storage.save_parts(storage.connect(), parts)
    flags, at_risk = run_rules(documents, parts, settings, today)
    check_id = storage.save_check(storage.connect(), today, __version__, flags, at_risk)

    print(f"Compliance report as of {today.isoformat()} (tool {__version__}, check {check_id})")
    print(_summary(documents, parts, flags, at_risk, rejected_documents + rejected_parts))
    print()
    print(render_report(flags, at_risk, rejected_documents + rejected_parts), end="")
    return 0


def _count(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _summary(documents, parts, flags, at_risk, rejected):
    # One line so the reader sees the scope of the check, including suppliers that are fine.
    suppliers = {item.supplier_id for item in [*documents, *parts]}
    clean = suppliers - {flag.supplier_id for flag in flags}
    return (
        f"Checked {_count(len(suppliers), 'supplier')} and {_count(len(parts), 'part')}: "
        f"{_count(len(clean), 'supplier')} with no issues, {_count(len(at_risk), 'part')} at risk, "
        f"{_count(len(flags), 'flag')}, {_count(len(rejected), 'rejected record')}"
    )


def _history(args):
    conn = storage.connect()
    storage.init_schema(conn)
    rows = storage.supplier_history(conn, args.supplier_id)

    print(f"History for {args.supplier_id}")
    if not rows:
        known = storage.supplier_known(storage.connect(), args.supplier_id)
        print("  no flags in any saved check" if known else "  no saved record of this supplier (rejected documents are not stored)")
        return 0

    for check_id, check_rows in groupby(rows, key=lambda row: row["check_id"]):
        check_rows = list(check_rows)
        first = check_rows[0]
        print(f"Check {check_id}  as of {first['as_of_date']}  (tool {first['tool_version']}, run {first['run_at']})")
        for row in check_rows:
            line = f"  {row['flag_type']}  {row['document_type']}  {row['expiry_date'] or NO_EXPIRY}"
            print(f"{line}  {row['document_id']}" if row["document_id"] else line)
    return 0
