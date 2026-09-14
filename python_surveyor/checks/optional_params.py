"""``optional-param-default`` check.

Finds any ``FunctionDef``/``AsyncFunctionDef`` with at least one defaulted
positional or keyword-only parameter (``*args``/``**kwargs`` names are not
"parameters" for this purpose). The signature (justifying comment + ``def``
line, with non-defaulted leading params elided) is attached as an excerpt,
and notes report the defaulted parameter names plus call sites that rely on
at least one default value (capped at ``corpus.max_call_sites``, with
"and N other(s)" when truncated) — call sites that override every default
are not listed, since they don't exercise the default path.
"""

import ast
from typing import TYPE_CHECKING

from python_surveyor.checks._util import justifying_comment
from python_surveyor.model import CallSite, Finding, SourceExcerpt

if TYPE_CHECKING:
    from python_surveyor.scanner import Corpus, SourceFile


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
    findings: list[Finding] = []
    for node in ast.walk(source.tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
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
