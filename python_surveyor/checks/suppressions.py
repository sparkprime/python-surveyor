"""``suppression-comment`` check.

Finds ``# pylint: disable=...`` / ``# pyright: ignore`` directives via
``tokenize`` (not regex) so they aren't matched by strings or multi-line
constructs. The preceding contiguous ``#``-comment block is attached as an
excerpt so the agent can judge whether it's a real justification; if there
is no preceding comment block, a note says so.
"""

import re
import tokenize
from typing import TYPE_CHECKING

from python_surveyor.checks._util import preceding_comment_excerpt
from python_surveyor.model import Finding

if TYPE_CHECKING:
    from python_surveyor.scanner import Corpus, SourceFile

_SUPPRESSION_RE = re.compile(r"pylint:\s*disable[-\w]*\s*=|pyright:\s*ignore")


def run(source: "SourceFile", _corpus: "Corpus") -> list[Finding]:
    """Find suppression comments and attach preceding-comment context."""
    findings: list[Finding] = []
    for token in source.tokens:
        if token.type != tokenize.COMMENT:
            continue
        if not _SUPPRESSION_RE.search(token.string):
            continue
        row = token.start[0]
        col = token.start[1]
        excerpts = preceding_comment_excerpt(source, row)
        if excerpts:
            notes: tuple[str, ...] = ()
        else:
            notes = ("no preceding comment found",)
        findings.append(
            Finding(
                check_id="suppression-comment",
                path=source.path,
                line=row,
                column=col,
                message="suppression comment (pylint: disable / pyright: ignore)",
                excerpts=excerpts,
                notes=notes,
            )
        )
    return findings
