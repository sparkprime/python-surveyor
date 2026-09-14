"""``fixture-naming`` check.

Finds ``@pytest.fixture``/``@fixture``-decorated functions whose registered
fixture name does not match the convention: the function should be prefixed
with ``fixture_`` **and** ``name=`` should register the true fixture name.
The ``def`` line is attached as an excerpt (extended upward to include any
justifying comment block), and a note reports the effective registered name
and the corpus lookup of parameter usages of that name elsewhere (the actual
``redefined-outer-name`` collision sites).
"""

import ast
from typing import TYPE_CHECKING

from python_surveyor.checks._util import justifying_comment
from python_surveyor.model import Finding, SourceExcerpt

if TYPE_CHECKING:
    from python_surveyor.scanner import Corpus, SourceFile


def _decorator_info(
    deco: ast.expr,
) -> "tuple[bool, bool, str | None]":
    """Return ``(is_fixture, has_name_kwarg, name_value)`` for a decorator."""
    call: ast.Call | None = None
    expr = deco
    if isinstance(expr, ast.Call):
        call = expr
        expr = expr.func
    is_fixture = False
    if isinstance(expr, ast.Attribute) and expr.attr == "fixture":
        if isinstance(expr.value, ast.Name) and expr.value.id == "pytest":
            is_fixture = True
    elif isinstance(expr, ast.Name) and expr.id == "fixture":
        is_fixture = True
    if not is_fixture or call is None:
        return is_fixture, False, None
    name_value: str | None = None
    has_name = False
    for kw in call.keywords:
        if kw.arg == "name":
            has_name = True
            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                name_value = kw.value.value
    return True, has_name, name_value


def _collision_note(registered_name: str, corpus: "Corpus") -> str:
    sites = corpus.param_locations.get(registered_name, ())
    count = len(sites)
    if count == 0:
        return f"registered as `{registered_name}`; no parameter usages elsewhere"
    cap = corpus.max_call_sites
    samples = sorted(sites, key=lambda pair: (str(pair[0].path), pair[0].line))[:cap]
    rendered = ", ".join(
        f"{pair[0].path.name}:{pair[0].line} (in `{pair[1]}`)" for pair in samples
    )
    remaining = count - cap
    if remaining > 0:
        rendered += f", and {remaining} other(s)"
    return (
        f"registered as `{registered_name}`; parameter used in "
        f"{count} other function(s): {rendered}"
    )


def _is_autouse(deco: ast.expr) -> bool:
    """True if the decorator call has ``autouse=True``."""
    if not isinstance(deco, ast.Call):
        return False
    for kw in deco.keywords:
        if (
            kw.arg == "autouse"
            and isinstance(kw.value, ast.Constant)
            and kw.value.value is True
        ):
            return True
    return False


def run(source: "SourceFile", corpus: "Corpus") -> list[Finding]:
    """Find fixture-naming issues and attach source + collision-site context."""
    if source.path.name == "conftest.py":
        return []
    findings: list[Finding] = []
    for node in ast.walk(source.tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        fixture_deco: ast.expr | None = None
        has_name_kwarg = False
        name_value: str | None = None
        for deco in node.decorator_list:
            is_fixture, has_name, value = _decorator_info(deco)
            if is_fixture:
                fixture_deco = deco
                has_name_kwarg = has_name
                name_value = value
                break
        if fixture_deco is None:
            continue
        if _is_autouse(fixture_deco):
            continue
        starts_with_fixture_ = node.name.startswith("fixture_")
        if has_name_kwarg and starts_with_fixture_:
            continue
        registered_name = name_value if name_value is not None else node.name
        reasons: list[str] = []
        if not has_name_kwarg:
            reasons.append("no `name=` kwarg")
        if not starts_with_fixture_:
            reasons.append(f"name `{node.name}` lacks `fixture_` prefix")
        jc = justifying_comment(source, node.lineno)
        start = jc[0].start_line if jc else node.lineno
        findings.append(
            Finding(
                check_id="fixture-naming",
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
                notes=(
                    _collision_note(registered_name, corpus),
                    f"reason: {'; '.join(reasons)}",
                ),
            )
        )
    return findings
