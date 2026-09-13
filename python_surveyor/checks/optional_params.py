"""``optional-param-default`` check.

Finds any ``FunctionDef``/``AsyncFunctionDef`` with at least one defaulted
positional or keyword-only parameter (``*args``/``**kwargs`` names are not
"parameters" for this purpose). The ``def`` line is attached as an excerpt
(extended upward to include any justifying comment block), and a note
reports the corpus call-site count, how many call sites use the default vs
override it, and samples — so the agent can judge whether the optional
param is actually exercised across the scanned tree.
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


def _has_defaulted_param(
    func: "ast.FunctionDef | ast.AsyncFunctionDef",
) -> bool:
    return bool(_defaulted_param_names(func))


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
    """Return notes describing call-site usage of defaulted params.

    Splits call sites into "explicit value" and "using default" groups so
    the agent can see whether the defaults are actually relied upon.
    """
    sites = corpus.call_sites.get(name, ())
    count = len(sites)
    if count == 0:
        return (f"`{name}` not called from anywhere scanned",)
    explicit: list[CallSite] = []
    using_default: list[CallSite] = []
    for site in sites:
        any_default = False
        any_override = False
        for idx, param_name in enumerate(defaulted_params):
            if _param_uses_default(param_name, idx, site):
                any_default = True
            else:
                any_override = True
        if any_override:
            explicit.append(site)
        elif any_default:
            using_default.append(site)
    explicit_sorted = sorted(
        explicit, key=lambda s: (str(s.location.path), s.location.line)
    )
    default_sorted = sorted(
        using_default, key=lambda s: (str(s.location.path), s.location.line)
    )
    cap = corpus.max_call_sites
    explicit_sample = explicit_sorted[:cap]
    default_sample = default_sorted[:cap]
    explicit_str = ", ".join(
        f"{s.location.path.name}:{s.location.line}" for s in explicit_sample
    )
    if len(explicit) > cap:
        explicit_str += ", ..."
    default_str = ", ".join(
        f"{s.location.path.name}:{s.location.line}" for s in default_sample
    )
    if len(using_default) > cap:
        default_str += ", ..."
    if not explicit:
        explicit_str = "None"
    if not using_default:
        default_str = "None"
    return (
        f"Call sites with explicit value: {explicit_str}",
        f"Call sites using default: {default_str}",
    )


def _def_end_line(node: "ast.FunctionDef | ast.AsyncFunctionDef") -> int:
    """Return the last line of the ``def`` signature (may span multiple lines)."""
    end = getattr(node, "end_lineno", None)
    if end is not None:
        return end
    return node.lineno


def run(source: "SourceFile", corpus: "Corpus") -> list[Finding]:
    """Find functions with defaulted params and attach source + call-site context."""
    findings: list[Finding] = []
    for node in ast.walk(source.tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        defaulted = _defaulted_param_names(node)
        if not defaulted:
            continue
        jc = justifying_comment(source, node.lineno)
        start = jc[0].start_line if jc else node.lineno
        end = _def_end_line(node)
        findings.append(
            Finding(
                check_id="optional-param-default",
                path=source.path,
                line=node.lineno,
                column=node.col_offset,
                message=(
                    f"function `{node.name}` has defaulted parameter(s): "
                    f"{', '.join(defaulted)}"
                ),
                excerpts=(
                    SourceExcerpt(
                        label="source",
                        path=source.path,
                        start_line=start,
                        end_line=end,
                    ),
                ),
                notes=_call_site_notes(node.name, defaulted, corpus),
            )
        )
    return findings
