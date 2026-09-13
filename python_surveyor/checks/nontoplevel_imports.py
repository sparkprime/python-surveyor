"""``non-toplevel-import`` check.

Finds ``Import``/``ImportFrom`` nodes that are not direct children of
``Module.body`` (i.e. nested inside a function, class, or control-flow block
at any depth). The import line is attached as an excerpt (extended upward to
include any justifying comment block), and a note names the nearest
enclosing scope so the agent can judge whether the late import is justified
(e.g. test-harness monkeypatching) or just laziness.
"""

import ast
from typing import TYPE_CHECKING

from python_surveyor.checks._util import (
    CONTROL_FLOW_NODES,
    justifying_comment,
)
from python_surveyor.model import Finding, SourceExcerpt

if TYPE_CHECKING:
    from python_surveyor.scanner import Corpus, SourceFile

_SCOPE_LABELS = {
    ast.FunctionDef: "function",
    ast.AsyncFunctionDef: "function",
    ast.ClassDef: "class",
    ast.If: "if block",
    ast.Try: "try block",
    ast.With: "with block",
    ast.For: "for block",
    ast.While: "while block",
    ast.ExceptHandler: "except block",
    ast.TryStar: "try* block",
}


def _is_type_checking_test(test: ast.expr) -> bool:
    """True for ``if TYPE_CHECKING:`` / ``if typing.TYPE_CHECKING:`` guards."""
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    return (
        isinstance(test, ast.Attribute)
        and test.attr == "TYPE_CHECKING"
        and isinstance(test.value, ast.Name)
        and test.value.id == "typing"
    )


def _scope_label(node: ast.AST) -> str:
    kind = _SCOPE_LABELS.get(type(node))
    if kind is None:
        return "nested block"
    name = getattr(node, "name", None)
    if name:
        return f"{kind} `{name}`"
    return kind


def _walk(
    body: list[ast.stmt],
    scope_stack: list[ast.AST],
    source: "SourceFile",
    findings: list[Finding],
) -> None:
    for stmt in body:
        new_stack = scope_stack
        if isinstance(
            stmt,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            new_stack = scope_stack + [stmt]
        elif isinstance(stmt, CONTROL_FLOW_NODES):
            if isinstance(stmt, ast.If) and _is_type_checking_test(stmt.test):
                new_stack = scope_stack
            else:
                new_stack = scope_stack + [stmt]
        if isinstance(stmt, (ast.Import, ast.ImportFrom)) and scope_stack:
            _record(stmt, source, scope_stack, findings)
        for child_field in ("body", "orelse", "finalbody"):
            child_body = getattr(stmt, child_field, None)
            if isinstance(child_body, list):
                _walk(child_body, new_stack, source, findings)
        if isinstance(stmt, ast.Try):
            for handler in stmt.handlers:
                _walk(handler.body, new_stack + [handler], source, findings)


def _record(
    stmt: "ast.Import | ast.ImportFrom",
    source: "SourceFile",
    scope_stack: list[ast.AST],
    findings: list[Finding],
) -> None:
    line = stmt.lineno
    jc = justifying_comment(source, line)
    start = jc[0].start_line if jc else line
    nearest = scope_stack[-1] if scope_stack else None
    note = (
        f"inside {_scope_label(nearest)}"
        if nearest is not None
        else "at module top-level"
    )
    findings.append(
        Finding(
            check_id="non-toplevel-import",
            path=source.path,
            line=line,
            column=stmt.col_offset,
            message="import below module top-level",
            excerpts=(
                SourceExcerpt(
                    label="source",
                    path=source.path,
                    start_line=start,
                    end_line=line,
                ),
            ),
            notes=(note,),
        )
    )


def run(source: "SourceFile", _corpus: "Corpus") -> list[Finding]:
    """Find non-top-level imports and attach source + enclosing-scope context."""
    findings: list[Finding] = []
    _walk(source.tree.body, [], source, findings)
    return findings
