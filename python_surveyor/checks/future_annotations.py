"""``future-annotations-import`` check.

Finds ``from __future__ import annotations``. The import line is attached
as an excerpt (extended upward to include any justifying comment block),
but the fix is always "delete the line" so there is little else to judge.
"""

import ast
from typing import TYPE_CHECKING

from python_surveyor.checks._util import justifying_comment
from python_surveyor.model import Finding, SourceExcerpt

if TYPE_CHECKING:
    from python_surveyor.scanner import Corpus, SourceFile


def run(source: "SourceFile", _corpus: "Corpus") -> list[Finding]:
    """Find ``from __future__ import annotations`` directives."""
    findings: list[Finding] = []
    for node in source.tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "__future__":
            continue
        for alias in node.names:
            if alias.name == "annotations":
                jc = justifying_comment(source, node.lineno)
                start = jc[0].start_line if jc else node.lineno
                findings.append(
                    Finding(
                        check_id="future-annotations-import",
                        path=source.path,
                        line=node.lineno,
                        column=node.col_offset,
                        excerpts=(
                            SourceExcerpt(
                                path=source.path,
                                start_line=start,
                                end_line=node.lineno,
                            ),
                        ),
                        notes=(),
                    )
                )
    return findings
