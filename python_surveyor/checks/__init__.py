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
from python_surveyor.checks.nontoplevel_imports import run as run_nontoplevel_imports
from python_surveyor.checks.optional_params import run as run_optional_params
from python_surveyor.checks.suppressions import run as run_suppressions
from python_surveyor.model import Finding

if TYPE_CHECKING:
    from python_surveyor.scanner import Corpus, SourceFile


@dataclass(frozen=True)
class CheckSpec:
    """A single check: id, short description, longer explanation, and runner.

    ``description`` is the one-liner shown by ``list-checks``.
    ``explanation`` is shown as a header note when the text report has
    findings for this check, so the reader understands *why* the smell
    matters before judging each hit.
    ``pylint_equivalents`` lists pylint check IDs that this check already
    covers, so the ``suppression-comment`` check can skip ``# pylint:
    disable=`` directives that are fully redundant with another check (the
    list is parsed and checked against this set — no regex to maintain).
    """

    check_id: str
    description: str
    explanation: str
    pylint_equivalents: tuple[str, ...]
    run: "Callable[[SourceFile, Corpus], list[Finding]]"


_ALL_CHECKS_DATA: tuple[
    tuple[
        str, str, str, tuple[str, ...], "Callable[[SourceFile, Corpus], list[Finding]]"
    ],
    ...,
] = (
    (
        "broad-except",
        "ExceptHandler with no type, or type Exception/BaseException "
        "(including tuples and except*).",
        "Catching a narrower exception type is usually better — it makes "
        "the intent explicit and avoids swallowing unexpected bugs. When a "
        "broad except is necessary, it should typically re-raise to "
        "preserve the stack trace for actual bugs rather than silently "
        "discarding them.",
        ("broad-exception-caught",),
        run_broad_except,
    ),
    (
        "fixture-naming",
        "@pytest.fixture function whose registered name does not match "
        "its declared name (the redefined-outer-name collision case).",
        "A pytest fixture function should be prefixed with `fixture_` and "
        "register its real name via `name=` so the function parameter in "
        "test functions doesn't shadow the fixture function name — the "
        "`redefined-outer-name` pylint disable that AI code often adds to "
        "silence this is a symptom, not a fix.",
        ("redefined-outer-name",),
        run_fixture_naming,
    ),
    (
        "future-annotations-import",
        "`from __future__ import annotations` (we never use 3.9).",
        "`from __future__ import annotations` makes all type annotations "
        "strings at runtime, which breaks any code that relies on "
        "resolving types at runtime (e.g. `typing.get_type_hints`, "
        "Pydantic models, FastAPI dependency injection). Since the "
        "target is always Python 3.12+, it's unnecessary and should be "
        "removed.",
        (),
        run_future_annotations,
    ),
    (
        "non-toplevel-import",
        "Import/ImportFrom not directly in Module.body, at any nesting depth.",
        "Imports inside functions or blocks are usually a sign of lazy "
        "import resolution — often masking circular dependencies that "
        "should be fixed with proper architecture. There may be a good "
        "reason (e.g. performance, test-harness monkeypatching), but "
        "absent one, imports should be at module top level.",
        ("import-outside-toplevel",),
        run_nontoplevel_imports,
    ),
    (
        "optional-param-default",
        "FunctionDef with >=1 defaulted positional or keyword-only parameter, "
        "excluding FastAPI/Flask route handlers (verified via real imports).",
        "Defaulted parameters are often added to avoid updating existing "
        "call sites, but they make it impossible for pyright to flag "
        "callers that should be passing an explicit value — the type "
        "checker sees the default and moves on. On internal APIs, every "
        "caller should pass an explicit value so pyright can catch "
        "missing or wrong arguments. FastAPI/Flask route handlers are "
        "excluded because their defaults are a framework user interface "
        "(query parameters, headers) and the handler is invoked by the "
        "framework, not by application code.",
        (),
        run_optional_params,
    ),
    (
        "suppression-comment",
        "# pylint: disable=... or # pyright: ignore without a "
        "justifying comment block above.",
        "Suppression comments disable a linter's check for a line or "
        "region. They're sometimes necessary, but each one should have a "
        "comment explaining *why* the suppression is warranted — without "
        "that, the suppression is indistinguishable from silencing a real "
        "problem.",
        (),
        run_suppressions,
    ),
)


ALL_CHECKS: tuple[CheckSpec, ...] = tuple(
    CheckSpec(
        check_id=cid,
        description=desc,
        explanation=expl,
        pylint_equivalents=equiv,
        run=run,
    )
    for cid, desc, expl, equiv, run in _ALL_CHECKS_DATA
)

CHECKS_BY_ID: dict[str, CheckSpec] = {
    check_spec.check_id: check_spec for check_spec in ALL_CHECKS
}

COVERED_PYLINT_IDS: frozenset[str] = frozenset(
    eq for check in ALL_CHECKS for eq in check.pylint_equivalents
)
