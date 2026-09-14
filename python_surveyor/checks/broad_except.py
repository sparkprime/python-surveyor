"""``broad-except`` check.

Finds ``ExceptHandler`` nodes with no type, or with type
``Exception``/``BaseException`` (including tuples and ``except*`` via
``TryStar``). Two excerpts are attached: the ``try`` side (justifying
comment above, the ``try`` line, and any comment block immediately after
the ``try`` — but no code from inside the try body) and the ``except``
side (the ``except`` line plus handler body, capped at ``_WINDOW``
lines). If the two excerpts overlap, they are merged into one.

Handlers that re-raise (bare ``raise``) or call ``logger.exception(...)``
are not flagged — re-raising preserves the stack trace, and
``logger.exception`` captures it (though the error is still swallowed).
"""

import ast
from typing import TYPE_CHECKING

from python_surveyor.checks._util import is_pure_comment_line, justifying_comment
from python_surveyor.model import Finding, SourceExcerpt

if TYPE_CHECKING:
    from python_surveyor.scanner import Corpus, SourceFile

_BROAD_NAMES = {"Exception", "BaseException"}
_WINDOW = 5


def _type_contains_broad(node: ast.expr | None) -> bool:
    if node is None:
        return True
    if isinstance(node, ast.Name):
        return node.id in _BROAD_NAMES
    if isinstance(node, ast.Tuple):
        return any(_type_contains_broad(elt) for elt in node.elts)
    return False


def _is_reraise(stmt: ast.stmt) -> bool:
    """True if ``stmt`` is a bare ``raise`` (re-raises the current exception)."""
    return isinstance(stmt, ast.Raise) and stmt.exc is None and stmt.cause is None


def _is_logger_exception(stmt: ast.stmt) -> bool:
    """True if ``stmt`` is ``<something>.exception(...)`` (e.g. ``logger.exception``)."""
    if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
        return False
    func = stmt.value.func
    return isinstance(func, ast.Attribute) and func.attr == "exception"


def _handler_re_raises_or_logs(handler: ast.ExceptHandler) -> bool:
    """True if the handler body re-raises or calls ``logger.exception``."""
    for stmt in handler.body:
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.stmt) and (
                _is_reraise(sub) or _is_logger_exception(sub)
            ):
                return True
    return False


def _body_end(handler: ast.ExceptHandler) -> int:
    """Return the last line of the handler body (or the ``except`` line)."""
    body = handler.body
    if not body:
        return handler.lineno
    last = body[-1]
    end = getattr(last, "end_lineno", None)
    if end is None:
        end = last.lineno
    return max(end, handler.lineno)


def _comment_block_end(source: "SourceFile", start: int) -> int:
    """Return the last line of a contiguous comment block starting at ``start``.

    If ``start`` is not a comment line, returns ``start - 1`` (an empty
    block before ``start``).
    """
    total = len(source.lines)
    end = start
    while end + 1 <= total and is_pure_comment_line(source.line_text(end + 1)):
        end += 1
    return end


def _try_except_excerpts(
    source: "SourceFile",
    jc_start: "int | None",
    try_line: int,
    handler_line: int,
    body_end: int,
) -> tuple[SourceExcerpt, ...]:
    """Build excerpts for the try and except sides of a broad except.

    The try-side excerpt is justifying comment (if any) + ``try`` line +
    any comment block immediately after the ``try`` — never code from
    inside the try body.  If there are no comments before or after the
    ``try``, the try-side excerpt is omitted entirely.  The except-side
    excerpt is the ``except`` line + handler body, capped at ``_WINDOW``
    lines.  If the two overlap, they are merged into one excerpt.
    """
    has_jc = jc_start is not None
    post_end = _comment_block_end(source, try_line)
    has_post = post_end > try_line
    second_start = handler_line
    second_end = min(body_end, handler_line + _WINDOW)
    if not has_jc and not has_post:
        return (
            SourceExcerpt(
                path=source.path,
                start_line=second_start,
                end_line=second_end,
            ),
        )
    first_start = jc_start if jc_start is not None else try_line
    first_end = post_end
    if first_end >= second_start:
        merged_end = min(max(first_end, second_end), body_end)
        return (
            SourceExcerpt(
                path=source.path,
                start_line=first_start,
                end_line=merged_end,
            ),
        )
    return (
        SourceExcerpt(
            path=source.path,
            start_line=first_start,
            end_line=first_end,
        ),
        SourceExcerpt(
            path=source.path,
            start_line=second_start,
            end_line=second_end,
        ),
    )


def run(source: "SourceFile", _corpus: "Corpus") -> list[Finding]:
    """Find broad ``except`` handlers and attach body + justifying-comment context."""
    findings: list[Finding] = []
    for node in ast.walk(source.tree):
        if not isinstance(node, (ast.Try, ast.TryStar)):
            continue
        jc = justifying_comment(source, node.lineno)
        jc_start = jc[0].start_line if jc else None
        for handler in node.handlers:
            if not _type_contains_broad(handler.type):
                continue
            if _handler_re_raises_or_logs(handler):
                continue
            body_end = _body_end(handler)
            excerpts = _try_except_excerpts(
                source, jc_start, node.lineno, handler.lineno, body_end
            )
            findings.append(
                Finding(
                    check_id="broad-except",
                    path=source.path,
                    line=handler.lineno,
                    column=handler.col_offset,
                    excerpts=excerpts,
                )
            )
    return findings
