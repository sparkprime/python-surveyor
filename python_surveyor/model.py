"""Frozen dataclasses shared by scanner, checks, and report renderers.

All construction uses required positional fields; there are no
default-valued fields on ``Finding``/``SourceExcerpt``, consistent with the
"no optional params on internal APIs" rule this tool itself checks for.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Location:
    """A single source position."""

    path: Path
    line: int


@dataclass(frozen=True)
class SourceExcerpt:
    """A literal slice of source worth showing verbatim."""

    label: str
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
    message: str
    excerpts: tuple[SourceExcerpt, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class ParseError:
    """A file that could not be ``ast.parse``-d."""

    path: Path
    line: int
    message: str
