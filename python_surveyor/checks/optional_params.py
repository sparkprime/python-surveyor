"""``optional-param-default`` check.

Finds any ``FunctionDef``/``AsyncFunctionDef`` with at least one defaulted
positional or keyword-only parameter (``*args``/``**kwargs`` names are not
"parameters" for this purpose). The signature (justifying comment + ``def``
line, with non-defaulted leading params elided) is attached as an excerpt,
and notes report the defaulted parameter names plus call sites that rely on
at least one default value (capped at ``corpus.max_call_sites``, with
"and N other(s)" when truncated) — call sites that override every default
are not listed, since they don't exercise the default path.

**Framework route handlers are excluded.** FastAPI/Flask route handlers use
defaulted params as a user interface (query parameters, headers, etc.) and
are invoked by the framework rather than by application code, so the
"missing call sites" signal this check looks for doesn't apply. A handler is
recognised only when its decorator (e.g. ``@app.get(...)``, ``@router.post(
...)``, ``@app.route(...)``) is a call on a name that is statically traced,
via imports in the same file, to an actual ``fastapi.FastAPI`` /
``fastapi.APIRouter`` / ``flask.Flask`` / ``flask.Blueprint`` instance. Only
direct ``name = Ctor()`` assignments are tracked — factory functions that
build and return an app/router are not (this matches the heuristic, not
exhaustive, philosophy of the other checks).
"""

import ast
from typing import TYPE_CHECKING

from python_surveyor.checks._util import justifying_comment
from python_surveyor.model import CallSite, Finding, SourceExcerpt

if TYPE_CHECKING:
    from python_surveyor.scanner import Corpus, SourceFile


# Framework classes whose instances expose route-decorator methods. Mapped
# from fully-qualified ``module.ClassName`` to the set of attribute names
# that route handlers are registered with.
_FRAMEWORK_CLASSES: dict[str, frozenset[str]] = {
    "fastapi.FastAPI": frozenset(
        {
            "get",
            "post",
            "put",
            "delete",
            "patch",
            "options",
            "head",
            "trace",
            "websocket",
            "api_route",
            "route",
        }
    ),
    "fastapi.APIRouter": frozenset(
        {
            "get",
            "post",
            "put",
            "delete",
            "patch",
            "options",
            "head",
            "trace",
            "websocket",
            "api_route",
        }
    ),
    "flask.Flask": frozenset(
        {"get", "post", "put", "delete", "patch", "options", "head", "route"}
    ),
    "flask.Blueprint": frozenset(
        {"get", "post", "put", "delete", "patch", "options", "head", "route"}
    ),
}


def _framework_import_bindings(
    tree: ast.Module,
) -> dict[str, str]:
    """Map locally-bound names to fully-qualified ``module.Name`` for framework imports.

    Handles ``from fastapi import FastAPI``, ``from fastapi import APIRouter as
    AR``, and ``import fastapi`` / ``import fastapi as fa``. Only names that
    resolve to a known framework class (``fastapi.FastAPI`` etc.) are kept.
    """
    bindings: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module not in ("fastapi", "flask"):
                continue
            for alias in node.names:
                fq = f"{node.module}.{alias.name}"
                if fq in _FRAMEWORK_CLASSES:
                    local = alias.asname if alias.asname else alias.name
                    bindings[local] = fq
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in ("fastapi", "flask"):
                    local = alias.asname if alias.asname else alias.name
                    bindings[local] = alias.name
    return bindings


def _resolve_call_qualname(func: ast.expr, bindings: dict[str, str]) -> str | None:
    """Resolve the called function to a fully-qualified name, or ``None``.

    Handles bare ``FastAPI()`` (``Name`` resolved via bindings) and dotted
    ``fastapi.FastAPI()`` / ``fa.FastAPI()`` (``Attribute`` whose value is a
    module-alias name in bindings).
    """
    if isinstance(func, ast.Name):
        return bindings.get(func.id)
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        module_alias = bindings.get(func.value.id)
        if module_alias is not None:
            return f"{module_alias}.{func.attr}"
    return None


def _framework_object_names(tree: ast.Module) -> set[str]:
    """Return names of variables bound to real FastAPI/Flask app/router instances.

    Only direct ``name = Ctor(...)`` assignments at any depth are tracked.
    Factory functions that build and return an app/router are not recognised
    — see the module docstring for the rationale.
    """
    bindings = _framework_import_bindings(tree)
    if not bindings:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1:
                continue
            target = node.targets[0]
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target = node.target
            value = node.value
        if not isinstance(target, ast.Name) or value is None:
            continue
        if not isinstance(value, ast.Call):
            continue
        fq = _resolve_call_qualname(value.func, bindings)
        if fq is not None and fq in _FRAMEWORK_CLASSES:
            names.add(target.id)
    return names


def _is_route_decorator(deco: ast.expr, router_names: set[str]) -> bool:
    """True if ``deco`` is a ``@<router>.<verb>(...)`` call on a known router.

    ``<router>`` must be a name in ``router_names`` (a verified framework
    app/router instance) and ``<verb>`` must be a route-registration method
    for that object's class (e.g. ``get``, ``post``, ``route``).
    """
    if not isinstance(deco, ast.Call):
        return False
    func = deco.func
    if not isinstance(func, ast.Attribute):
        return False
    if not isinstance(func.value, ast.Name):
        return False
    if func.value.id not in router_names:
        return False
    # ``router_names`` only contains verified framework instances, so any
    # attribute on them that matches a known route verb is a route decorator.
    for verbs in _FRAMEWORK_CLASSES.values():
        if func.attr in verbs:
            return True
    return False


def _defaulted_param_names(
    func: "ast.FunctionDef | ast.AsyncFunctionDef",
) -> list[str]:
    """Return the names of positional and keyword-only params that have defaults."""
    args = func.args
    names: list[str] = []
    positional_defaults = len(args.defaults)
    for i, arg in enumerate(args.args):
        if i >= len(args.args) - positional_defaults:
            names.append(arg.arg)
    for idx, default in enumerate(args.kw_defaults):
        if default is not None:
            names.append(args.kwonlyargs[idx].arg)
    return names


def _first_defaulted_line(
    func: "ast.FunctionDef | ast.AsyncFunctionDef",
) -> int:
    """Return the source line of the first defaulted parameter.

    Non-defaulted positional params before the first default are elided
    from the excerpt, so the reader sees only the params that matter.
    """
    args = func.args
    positional_defaults = len(args.defaults)
    first_defaulted_idx = len(args.args) - positional_defaults
    if positional_defaults > 0:
        return args.args[first_defaulted_idx].lineno
    for idx, default in enumerate(args.kw_defaults):
        if default is not None:
            return args.kwonlyargs[idx].lineno
    return func.lineno


def _param_uses_default(
    param_name: str,
    param_index: int,
    call: CallSite,
) -> bool:
    """True if the call site does not pass this param (uses the default)."""
    if param_name in call.keywords:
        return False
    if param_index < call.positional_count:
        return False
    return True


def _call_site_notes(
    name: str,
    defaulted_params: list[str],
    corpus: "Corpus",
) -> tuple[str, ...]:
    """Return notes describing call sites that use at least one default value.

    Call sites that override every defaulted param are not listed — they
    don't exercise the default path and only add noise.  Call sites that
    use at least one default are listed (capped at ``corpus.max_call_sites``)
    with "and N other(s)" when truncated.
    """
    sites = corpus.call_sites.get(name, ())
    total = len(sites)
    if total == 0:
        return (f"`{name}` not called from anywhere scanned",)
    using_default: list[CallSite] = []
    for site in sites:
        for idx, param_name in enumerate(defaulted_params):
            if _param_uses_default(param_name, idx, site):
                using_default.append(site)
                break
    using_default_sorted = sorted(
        using_default, key=lambda s: (str(s.location.path), s.location.line)
    )
    cap = corpus.max_call_sites
    shown = using_default_sorted[:cap]
    if not shown:
        return (f"All {total} call site(s) override every defaulted parameter",)
    parts = [f"{s.location.path.name}:{s.location.line}" for s in shown]
    remaining = len(using_default) - len(shown)
    if remaining > 0:
        parts.append(f"and {remaining} other(s)")
    sites_str = ", ".join(parts)
    return (
        f"Call sites using defaults ({len(using_default)} of {total}): {sites_str}",
    )


def _signature_end_line(
    node: "ast.FunctionDef | ast.AsyncFunctionDef",
) -> int:
    """Return the last line of the ``def`` signature (the ``:`` line)."""
    if not node.body:
        return node.lineno
    first_body = node.body[0]
    return max(node.lineno, first_body.lineno - 1)


def run(source: "SourceFile", corpus: "Corpus") -> list[Finding]:
    """Find functions with defaulted params and attach signature + call-site context."""
    router_names = _framework_object_names(source.tree)
    findings: list[Finding] = []
    for node in ast.walk(source.tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if router_names and any(
            _is_route_decorator(deco, router_names) for deco in node.decorator_list
        ):
            continue
        defaulted = _defaulted_param_names(node)
        if not defaulted:
            continue
        jc = justifying_comment(source, node.lineno)
        jc_start = jc[0].start_line if jc else None
        sig_start = _first_defaulted_line(node)
        start = jc_start if jc_start is not None else sig_start
        end = _signature_end_line(node)
        findings.append(
            Finding(
                check_id="optional-param-default",
                path=source.path,
                line=node.lineno,
                column=node.col_offset,
                excerpts=(
                    SourceExcerpt(
                        path=source.path,
                        start_line=start,
                        end_line=end,
                    ),
                ),
                notes=(
                    f"Defaulted params: {', '.join(defaulted)}",
                    *_call_site_notes(node.name, defaulted, corpus),
                ),
            )
        )
    return findings
