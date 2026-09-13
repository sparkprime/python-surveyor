"""``optional-param-default`` check.

Finds any ``FunctionDef``/``AsyncFunctionDef`` with at least one defaulted
positional or keyword-only parameter (``*args``/``**kwargs`` names are not
"parameters" for this purpose). A note reports the corpus call-site count and
samples for the function's name so the agent can judge whether the optional
param is actually exercised across the scanned tree.
"""

import ast
from typing import TYPE_CHECKING

from python_surveyor.model import Finding

if TYPE_CHECKING:
    from python_surveyor.scanner import Corpus, SourceFile


def _has_defaulted_param(
    func: "ast.FunctionDef | ast.AsyncFunctionDef",
) -> bool:
    args = func.args
    if args.defaults:
        return True
    for default in args.kw_defaults:
        if default is not None:
            return True
    return False


def _call_site_note(name: str, corpus: "Corpus") -> str:
    sites = corpus.call_sites.get(name, ())
    count = len(sites)
    if count == 0:
        return f"`{name}` not called from anywhere scanned"
    sample = sorted(sites, key=lambda loc: (str(loc.path), loc.line))[
        : corpus.max_call_sites
    ]
    rendered = ", ".join(f"{loc.path.name}:{loc.line}" for loc in sample)
    suffix = "" if count <= corpus.max_call_sites else ", ..."
    return f"`{name}` called from {count} site(s): {rendered}{suffix}"


def run(source: "SourceFile", corpus: "Corpus") -> list[Finding]:
    """Find functions with defaulted params and attach call-site context."""
    findings: list[Finding] = []
    for node in ast.walk(source.tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _has_defaulted_param(node):
            continue
        findings.append(
            Finding(
                check_id="optional-param-default",
                path=source.path,
                line=node.lineno,
                column=node.col_offset,
                message=(f"function `{node.name}` has defaulted parameter(s)"),
                excerpts=(),
                notes=(_call_site_note(node.name, corpus),),
            )
        )
    return findings
