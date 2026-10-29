# Plain-text report. Implemented in RPT-01.

FLAG_SECTIONS = (
    ("expired", "Expired"),
    ("expiring_soon", "Expiring soon"),
    ("missing", "Missing"),
)
NO_EXPIRY = "—"


def _flag_line(flag, show_type=False):
    expiry = flag.expiry_date.isoformat() if flag.expiry_date is not None else NO_EXPIRY
    line = f"  {flag.supplier_id}  {flag.document_type}  {expiry}"
    if flag.document_id:
        line += f"  {flag.document_id}"
    return f"{line}  ({flag.flag_type})" if show_type else line


def _sorted_flags(flags):
    return sorted(flags, key=lambda flag: (flag.supplier_id, flag.document_type, flag.flag_type))


def _rejected_line(record):
    record_id = record.raw_id or f"{record.source_file}[{record.index}]"
    return f"  {record_id}  {record.reason}"


def render_report(flags, at_risk, rejected) -> str:
    known = {flag_type for flag_type, _ in FLAG_SECTIONS}
    lines = []

    if not flags:
        lines += ["No issues found", ""]

    for flag_type, heading in FLAG_SECTIONS:
        matching = _sorted_flags(flag for flag in flags if flag.flag_type == flag_type)
        if matching:
            lines += [heading, *(_flag_line(flag) for flag in matching), ""]

    other = _sorted_flags(flag for flag in flags if flag.flag_type not in known)
    if other:
        lines += ["Other", *(_flag_line(flag, show_type=True) for flag in other), ""]

    if at_risk:
        lines.append("Parts at risk")
        lines += [
            f"  {part.part_number}  {part.supplier_id}  {'; '.join(part.reasons)}"
            for part in sorted(at_risk, key=lambda p: p.part_number)
        ]
        lines.append("")

    lines.append("Rejected records")
    lines += [_rejected_line(record) for record in rejected] or ["  none"]

    return "\n".join(lines) + "\n"
