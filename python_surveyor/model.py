"""Frozen dataclasses shared by scanner, checks, and report renderers."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Location:
    """A single source position."""

    path: Path
    line: int


@dataclass(frozen=True)
class CallSite:
    """A call to a name, with enough info to tell if defaulted params are used.

    ``positional_count`` is the number of positional args (not counting
    ``*args`` spreads). ``keywords`` is the set of keyword arg names (not
    counting ``**kwargs`` spreads). Together these let the
    ``optional-param-default`` check determine whether a call site uses the
    default value or passes an explicit one.
    """

    location: Location
    positional_count: int
    keywords: frozenset[str]


@dataclass(frozen=True)
class SourceExcerpt:
    """A literal slice of source worth showing verbatim."""

    path: Path
    start_line: int
    end_line: int


@dataclass(frozen=True)
class Finding:
    """A candidate smell detected by a check."""

    check_id: str
    path: Path
    line: int
    column: int
    excerpts: tuple[SourceExcerpt, ...]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParseError:
    """A file that could not be ``ast.parse``-d."""

    path: Path
    line: int
    message: str
