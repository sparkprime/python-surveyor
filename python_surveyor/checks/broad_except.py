"""``broad-except`` check.

Finds ``ExceptHandler`` nodes with no type, or with type
``Exception``/``BaseException`` (including tuples and ``except*`` via
``TryStar``). The handler's ``except`` line plus body is attached as an
excerpt so the agent can see how the exception is actually handled, and any
justifying comment above the ``try`` is attached as well.
"""

import ast
from typing import TYPE_CHECKING

from python_surveyor.checks._util import justifying_comment
from python_surveyor.model import Finding, SourceExcerpt

if TYPE_CHECKING:
    from python_surveyor.scanner import Corpus, SourceFile

_BROAD_NAMES = {"Exception", "BaseException"}


def _type_contains_broad(node: ast.expr | None) -> bool:
    if node is None:
        return True
    if isinstance(node, ast.Name):
        return node.id in _BROAD_NAMES
    if isinstance(node, ast.Tuple):
        return any(_type_contains_broad(elt) for elt in node.elts)
    return False


def _handler_label(is_star: bool, has_type: bool) -> str:
    keyword = "except*" if is_star else "except"
    if not has_type:
        return f"bare {keyword}:"
    return f"broad {keyword}: Exception/BaseException"


def _body_range(handler: ast.ExceptHandler) -> "tuple[int, int]":
    """Return ``(start, end)`` line range of the handler (except line + body)."""
    body = handler.body
    if not body:
        return handler.lineno, handler.lineno
    start = handler.lineno
    last = body[-1]
    end = getattr(last, "end_lineno", None)
    if end is None:
        end = last.lineno
    end = max(end, start)
    return start, end


def run(source: "SourceFile", _corpus: "Corpus") -> list[Finding]:
    """Find broad ``except`` handlers and attach body + justifying-comment context."""
    findings: list[Finding] = []
    for node in ast.walk(source.tree):
        if isinstance(node, ast.Try):
            is_star = False
        elif isinstance(node, ast.TryStar):
            is_star = True
        else:
            continue
        jc = justifying_comment(source, node.lineno)
        jc_start = jc[0].start_line if jc else None
        for handler in node.handlers:
            if not _type_contains_broad(handler.type):
                continue
            body_start, body_end = _body_range(handler)
            has_type = handler.type is not None
            if jc_start is not None:
                excerpt_start = jc_start
            else:
                excerpt_start = body_start
            findings.append(
                Finding(
                    check_id="broad-except",
                    path=source.path,
                    line=handler.lineno,
                    column=handler.col_offset,
                    message=_handler_label(is_star, has_type),
                    excerpts=(
                        SourceExcerpt(
                            label="source",
                            path=source.path,
                            start_line=excerpt_start,
                            end_line=body_end,
                        ),
                    ),
                    notes=(),
                )
            )
    return findings
