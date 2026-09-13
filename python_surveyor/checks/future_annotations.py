"""``future-annotations-import`` check.

Finds ``from __future__ import annotations``. No excerpt or notes — the fix
is always "delete the line", so there is nothing for the agent to judge.
"""

import ast
from typing import TYPE_CHECKING

from python_surveyor.model import Finding

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
                findings.append(
                    Finding(
                        check_id="future-annotations-import",
                        path=source.path,
                        line=node.lineno,
                        column=node.col_offset,
                        message="`from __future__ import annotations`",
                        excerpts=(),
                        notes=(),
                    )
                )
    return findings
