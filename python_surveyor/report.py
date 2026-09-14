"""Render a ``ScanResult`` as text.

Text output groups findings by ``check_id``; each finding is shown as
``path:line:col`` followed by excerpts (with the line range in the header)
and note lines. Parse errors get their own leading section. Excerpts are
capped to ``--max-excerpt-lines`` with a truncation note.
"""

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
        prev_path: Path | None = None
        prev_end: int | None = None
        for excerpt in finding.excerpts:
            lines, truncation = _read_excerpt_lines(
                excerpt.path,
                excerpt.start_line,
                excerpt.end_line,
                max_excerpt_lines,
            )
            is_continuation = (
                prev_path == excerpt.path
                and prev_end is not None
                and excerpt.start_line > prev_end + 1
            )
            if is_continuation:
                stream.write(
                    f"... (redacted until lines "
                    f"{excerpt.start_line}-{excerpt.end_line}) ...\n"
                )
            else:
                stream.write(
                    f"({counter}) {excerpt.path}:"
                    f"{excerpt.start_line}-{excerpt.end_line}\n"
                )
            for line in lines:
                stream.write(f"{line}\n")
            if truncation:
                stream.write(f"... {truncation}\n")
            prev_path = excerpt.path
            prev_end = excerpt.end_line
        for note in finding.notes:
            stream.write(f"  note: {note}\n")
        stream.write("\n")
    if not result.findings:
        stream.write("no findings.\n")
