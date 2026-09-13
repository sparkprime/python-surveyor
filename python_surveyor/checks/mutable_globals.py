"""``mutable-module-global`` check.

Finds ``Assign``/``AnnAssign``/``AugAssign`` at module scope (the module body
plus nested ``if``/``try``/``with``/``for``/``while`` blocks, but **not**
descending into ``def``/``class``) whose target name is not ``UPPER_CASE`` and
not a dunder. The preceding comment block is attached as an excerpt, and a
note counts + samples ``global <name>`` statements elsewhere in the file so
the agent can tell a real mutation from a naming nit.
"""

import ast
from typing import TYPE_CHECKING

from python_surveyor.checks._util import (
    CONTROL_FLOW_NODES,
    preceding_comment_excerpt,
)
from python_surveyor.model import Finding, Location

if TYPE_CHECKING:
    from python_surveyor.scanner import Corpus, SourceFile


def _is_dunder(name: str) -> bool:
    return len(name) >= 4 and name.startswith("__") and name.endswith("__")


def _is_upper_case(name: str) -> bool:
    return name.isupper() and any(ch.isalpha() for ch in name)


def _target_names(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for elt in target.elts:
            if isinstance(elt, ast.Name):
                names.append(elt.id)
        return names
    return []


def _walk_module_scope(
    body: list[ast.stmt],
) -> "list[tuple[ast.Assign | ast.AnnAssign | ast.AugAssign, int]]":
    """Yield assignment nodes at module-flavored scope with their col offset.

    Recurses into ``if``/``try``/``with``/``for``/``while`` bodies but stops
    at ``def``/``class`` boundaries (those introduce their own scopes).
    """
    results: list[tuple[ast.Assign | ast.AnnAssign | ast.AugAssign, int]] = []
    stack: list[list[ast.stmt]] = [body]
    while stack:
        current = stack.pop()
        for stmt in current:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                results.append((stmt, stmt.col_offset))
            if isinstance(stmt, CONTROL_FLOW_NODES):
                stack.append(_child_bodies(stmt))
    return results


def _child_bodies(stmt: ast.stmt) -> list[ast.stmt]:
    if isinstance(stmt, ast.If):
        return list(stmt.body) + list(stmt.orelse)
    if isinstance(stmt, ast.Try):
        bodies = list(stmt.body) + list(stmt.orelse) + list(stmt.finalbody)
        for handler in stmt.handlers:
            bodies.extend(handler.body)
        return bodies
    if isinstance(stmt, ast.With):
        return list(stmt.body)
    if isinstance(stmt, (ast.For, ast.While)):
        return list(stmt.body) + list(stmt.orelse)
    return []


def _global_uses(source: "SourceFile", name: str) -> list[Location]:
    uses: list[Location] = []
    for node in ast.walk(source.tree):
        if isinstance(node, ast.Global) and name in node.names:
            uses.append(Location(path=source.path, line=node.lineno))
    return uses


def run(source: "SourceFile", _corpus: "Corpus") -> list[Finding]:
    """Find mutable module globals and attach preceding-comment + global-uses context."""
    findings: list[Finding] = []
    for assign, col in _walk_module_scope(source.tree.body):
        targets: list[ast.expr] = []
        if isinstance(assign, ast.Assign):
            targets = list(assign.targets)
        else:
            targets = [assign.target]
        names: list[str] = []
        for target in targets:
            names.extend(_target_names(target))
        if not names:
            continue
        line = assign.lineno
        excerpts = preceding_comment_excerpt(source, line)
        primary = names[0]
        global_uses = _global_uses(source, primary)
        notes: list[str] = []
        if global_uses:
            count = len(global_uses)
            samples = ", ".join(
                f"{loc.path.name}:{loc.line}" for loc in global_uses[:3]
            )
            notes.append(
                f"`global {primary}` declared in {count} " f"function(s): {samples}"
            )
        for name in names:
            if _is_dunder(name) or _is_upper_case(name):
                continue
            findings.append(
                Finding(
                    check_id="mutable-module-global",
                    path=source.path,
                    line=line,
                    column=col,
                    message=f"mutable module global: `{name}` is not UPPER_CASE",
                    excerpts=excerpts,
                    notes=tuple(notes),
                )
            )
    return findings
