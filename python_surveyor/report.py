"""Render a ``ScanResult`` as text or JSON.

Text output groups findings by ``check_id``; each finding is shown as
``path:line:col -- message`` followed by labeled excerpts (with the line
range in the header) and note lines. Parse errors get their own leading
section. Excerpts are capped to ``--max-excerpt-lines`` with a truncation
note.

JSON output is a flat list of the same fields for programmatic use (excerpt
text is not included — only the line range, so consumers can lazy-load).
"""

import json
from pathlib import Path
from typing import TextIO

from python_surveyor.checks import CHECKS_BY_ID
from python_surveyor.scanner import ScanResult


def _read_excerpt_lines(
    path: Path, start: int, end: int, max_lines: int
) -> "tuple[list[str], str | None]":
    """Read ``[start, end]`` from ``path``, capping to ``max_lines``.

    Returns ``(lines, truncation_note)``.
    """
    try:
        all_lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ([], None)
    available_end = min(end, len(all_lines))
    if available_end < start:
        return ([], None)
    span = available_end - start + 1
    if span <= max_lines:
        return (all_lines[start - 1 : available_end], None)
    capped_end = start + max_lines - 1
    return (
        all_lines[start - 1 : capped_end],
        f"excerpt truncated at {max_lines} lines",
    )


def render_text(
    result: ScanResult,
    max_excerpt_lines: int,
    stream: TextIO,
) -> None:
    """Render ``result`` as human-readable text to ``stream``."""
    stream.write(f"# scan: {result.files_scanned} file(s) scanned\n\n")
    if result.parse_errors:
        stream.write("## parse errors\n\n")
        for err in result.parse_errors:
            stream.write(f"{err.path}:{err.line} -- {err.message}\n")
        stream.write("\n")
    current_check: str | None = None
    counter = 0
    for finding in result.findings:
        if finding.check_id != current_check:
            current_check = finding.check_id
            counter = 0
            stream.write(f"## {current_check}\n\n")
            spec = CHECKS_BY_ID.get(current_check)
            if spec is not None:
                stream.write(f"{spec.explanation}\n\n")
        counter += 1
        for excerpt in finding.excerpts:
            lines, truncation = _read_excerpt_lines(
                excerpt.path,
                excerpt.start_line,
                excerpt.end_line,
                max_excerpt_lines,
            )
            stream.write(
                f"({counter}) {excerpt.path}:"
                f"{excerpt.start_line}-{excerpt.end_line}\n"
            )
            for line in lines:
                stream.write(f"{line}\n")
            if truncation:
                stream.write(f"... {truncation}\n")
        for note in finding.notes:
            stream.write(f"  note: {note}\n")
        stream.write("\n")
    if not result.findings:
        stream.write("no findings.\n")


def render_json(
    result: ScanResult,
    max_excerpt_lines: int,
    stream: TextIO,
) -> None:
    """Render ``result`` as JSON to ``stream``.

    ``max_excerpt_lines`` is accepted for API symmetry with
    :func:`render_text`; JSON emits ranges only, not source text.
    """
    del max_excerpt_lines
    findings_payload = []
    for finding in result.findings:
        excerpts_payload = [
            {
                "label": excerpt.label,
                "path": str(excerpt.path),
                "start_line": excerpt.start_line,
                "end_line": excerpt.end_line,
            }
            for excerpt in finding.excerpts
        ]
        findings_payload.append(
            {
                "check_id": finding.check_id,
                "path": str(finding.path),
                "line": finding.line,
                "column": finding.column,
                "message": finding.message,
                "excerpts": excerpts_payload,
                "notes": list(finding.notes),
            }
        )
    parse_errors_payload = [
        {
            "path": str(err.path),
            "line": err.line,
            "message": err.message,
        }
        for err in result.parse_errors
    ]
    payload = {
        "files_scanned": result.files_scanned,
        "findings": findings_payload,
        "parse_errors": parse_errors_payload,
    }
    json.dump(payload, stream, indent=2)
    stream.write("\n")
