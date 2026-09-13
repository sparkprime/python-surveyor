"""``broad-except`` check.

Finds ``ExceptHandler`` nodes with no type, or with type
``Exception``/``BaseException`` (including tuples and ``except*`` via
``TryStar``). The handler's **body** is attached as an excerpt (not the
preceding lines) so the agent can see how the exception is actually handled.
"""

import ast
from typing import TYPE_CHECKING

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
    """Return ``(start, end)`` line range of the handler's body statements."""
    body = handler.body
    if not body:
        return handler.lineno, handler.lineno
    start = body[0].lineno
    last = body[-1]
    end = getattr(last, "end_lineno", None)
    if end is None:
        end = last.lineno
    end = max(end, start)
    return start, end


def run(source: "SourceFile", _corpus: "Corpus") -> list[Finding]:
    """Find broad ``except`` handlers and attach their bodies as excerpts."""
    findings: list[Finding] = []
    for node in ast.walk(source.tree):
        if isinstance(node, ast.Try):
            is_star = False
        elif isinstance(node, ast.TryStar):
            is_star = True
        else:
            continue
        for handler in node.handlers:
            if not _type_contains_broad(handler.type):
                continue
            start, end = _body_range(handler)
            has_type = handler.type is not None
            findings.append(
                Finding(
                    check_id="broad-except",
                    path=source.path,
                    line=handler.lineno,
                    column=handler.col_offset,
                    message=_handler_label(is_star, has_type),
                    excerpts=(
                        SourceExcerpt(
                            label="except body",
                            path=source.path,
                            start_line=start,
                            end_line=end,
                        ),
                    ),
                    notes=(),
                )
            )
    return findings
