"""``suppression-comment`` check.

Finds ``# pylint: disable=...`` / ``# pyright: ignore`` directives via
``tokenize`` (not regex) so they aren't matched by strings or multi-line
constructs. The source line is attached as an excerpt (extended upward to
include any justifying comment block immediately above) so the reader can see
both the suppression and its justification in one contiguous block.

When a ``# pylint: disable=...`` is a standalone comment (not a trailing
comment on a code line), it applies to all lines below until a matching
``# pylint: enable=...`` or the end of the file. In that case the excerpt is
extended downward to show what code is being suppressed, capped at
``_MAX_SUPPRESSED_LINES`` lines.
"""

import re
import tokenize
from typing import TYPE_CHECKING

from python_surveyor.checks._util import justifying_comment
from python_surveyor.model import Finding, SourceExcerpt

if TYPE_CHECKING:
    from python_surveyor.scanner import Corpus, SourceFile

_SUPPRESSION_RE = re.compile(r"pylint:\s*disable[-\w]*\s*=|pyright:\s*ignore")
_ALREADY_COVERED_RE = re.compile(
    r"pylint:\s*disable[-\w]*\s*=\s*[\w,\s]*"
    r"(?:broad-exception-caught|redefined-outer-name)"
)
_ENABLE_RE = re.compile(r"pylint:\s*enable[-\w]*\s*=")
_MAX_SUPPRESSED_LINES = 10


def _is_standalone_comment(source: "SourceFile", row: int) -> bool:
    """True if the suppression comment is a whole-line comment, not trailing."""
    line = source.line_text(row)
    return line.strip().startswith("#")


def _find_enable_or_end(source: "SourceFile", row: int) -> int:
    """Return the last line covered by a standalone ``disable`` at ``row``.

    Walks downward from ``row + 1`` looking for ``# pylint: enable=...``.
    If found, returns the line before it. If not found, returns either
    ``row + _MAX_SUPPRESSED_LINES`` or the last line of the file,
    whichever comes first.
    """
    total = len(source.lines)
    limit = min(row + _MAX_SUPPRESSED_LINES, total)
    for candidate in range(row + 1, limit + 1):
        text = source.line_text(candidate)
        if _ENABLE_RE.search(text):
            return candidate - 1
    return limit


def run(source: "SourceFile", _corpus: "Corpus") -> list[Finding]:
    """Find suppression comments and attach source + justifying-comment context."""
    findings: list[Finding] = []
    for token in source.tokens:
        if token.type != tokenize.COMMENT:
            continue
        if not _SUPPRESSION_RE.search(token.string):
            continue
        if _ALREADY_COVERED_RE.search(token.string):
            continue
        row = token.start[0]
        jc = justifying_comment(source, row)
        start = jc[0].start_line if jc else row
        if _is_standalone_comment(source, row):
            end = _find_enable_or_end(source, row)
        else:
            end = row
        findings.append(
            Finding(
                check_id="suppression-comment",
                path=source.path,
                line=row,
                column=token.start[1],
                message="suppression comment (pylint: disable / pyright: ignore)",
                excerpts=(
                    SourceExcerpt(
                        label="source",
                        path=source.path,
                        start_line=start,
                        end_line=end,
                    ),
                ),
                notes=(),
            )
        )
    return findings
