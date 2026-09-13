"""Check registry used by dispatch and the ``list-checks`` command.

Every check is a ``CheckSpec(check_id, description, run)`` where ``run`` has
the signature ``run(source: SourceFile, corpus: Corpus) -> list[Finding]``.
Checks that ignore ``corpus`` still take it, so the internal check API itself
has no optional parameters.

``SourceFile`` and ``Corpus`` are imported only under ``TYPE_CHECKING`` to
avoid a circular import with :mod:`python_surveyor.scanner` (which imports
this registry at module top-level).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from python_surveyor.checks.broad_except import run as run_broad_except
from python_surveyor.checks.fixture_naming import run as run_fixture_naming
from python_surveyor.checks.future_annotations import run as run_future_annotations
from python_surveyor.checks.mutable_globals import run as run_mutable_globals
from python_surveyor.checks.nontoplevel_imports import run as run_nontoplevel_imports
from python_surveyor.checks.optional_params import run as run_optional_params
from python_surveyor.checks.suppressions import run as run_suppressions
from python_surveyor.model import Finding

if TYPE_CHECKING:
    from python_surveyor.scanner import Corpus, SourceFile


@dataclass(frozen=True)
class CheckSpec:
    """A single check: id, human description, and the runner."""

    check_id: str
    description: str
    run: "Callable[[SourceFile, Corpus], list[Finding]]"


ALL_CHECKS: tuple[CheckSpec, ...] = (
    CheckSpec(
        check_id="broad-except",
        description=(
            "ExceptHandler with no type, or type Exception/BaseException "
            "(including tuples and except*)."
        ),
        run=run_broad_except,
    ),
    CheckSpec(
        check_id="fixture-naming",
        description=(
            "@pytest.fixture function whose registered name does not match "
            "its declared name (the redefined-outer-name collision case)."
        ),
        run=run_fixture_naming,
    ),
    CheckSpec(
        check_id="future-annotations-import",
        description="`from __future__ import annotations` (we never use 3.9).",
        run=run_future_annotations,
    ),
    CheckSpec(
        check_id="mutable-module-global",
        description=(
            "Module-scope assignment whose target name is not UPPER_CASE and "
            "not a dunder."
        ),
        run=run_mutable_globals,
    ),
    CheckSpec(
        check_id="non-toplevel-import",
        description=(
            "Import/ImportFrom not directly in Module.body, at any nesting " "depth."
        ),
        run=run_nontoplevel_imports,
    ),
    CheckSpec(
        check_id="optional-param-default",
        description=(
            "FunctionDef with >=1 defaulted positional or keyword-only " "parameter."
        ),
        run=run_optional_params,
    ),
    CheckSpec(
        check_id="suppression-comment",
        description=(
            "# pylint: disable=... or # pyright: ignore without a "
            "justifying comment block above."
        ),
        run=run_suppressions,
    ),
)

CHECKS_BY_ID: dict[str, CheckSpec] = {
    check_spec.check_id: check_spec for check_spec in ALL_CHECKS
}
