"""Shared helpers for check implementations.

Every finding needs two pieces of context that are shared across all checks:
the source line(s) at the finding location (so the reader can see the actual
code) and any justifying comment block immediately above it (so the reader
can judge whether the smell is intentional). Excerpt-line capping is a
rendering concern and lives in :mod:`python_surveyor.report`.

``SourceFile`` is imported only under ``TYPE_CHECKING`` to avoid a circular
import with :mod:`python_surveyor.scanner`.
"""

import ast
from typing import TYPE_CHECKING

from python_surveyor.model import SourceExcerpt

if TYPE_CHECKING:
    from python_surveyor.scanner import SourceFile

CONTROL_FLOW_NODES: tuple[type[ast.AST], ...] = (
    ast.If,
    ast.Try,
    ast.With,
    ast.For,
    ast.While,
)


def is_pure_comment_line(text: str) -> bool:
    """True if ``text`` is a ``#``-comment line (possibly indented, no code)."""
    return text.strip().startswith("#")


def preceding_comment_block(
    source: "SourceFile", line: int
) -> "tuple[int, int] | None":
    """Return ``(start, end)`` inclusive of the contiguous comment block above
    ``line``, or ``None`` if the line immediately above is not a comment.

    Walks upward while each preceding line is a pure ``#``-comment line; blank
    lines and code lines break the block.
    """
    end = line - 1
    if end < 1:
        return None
    if not is_pure_comment_line(source.line_text(end)):
        return None
    start = end
    while start - 1 >= 1 and is_pure_comment_line(source.line_text(start - 1)):
        start -= 1
    return start, end


def justifying_comment(source: "SourceFile", line: int) -> tuple[SourceExcerpt, ...]:
    """Return a 1-tuple excerpt for the comment block above ``line``, or ``()``.

    If a preceding ``#``-comment block is found, it is attached as an excerpt
    labeled "justifying comment". If no preceding comment block is found,
    returns ``()`` — the absence of the excerpt is the signal that no
    justifying comment exists, so no note is needed.
    """
    block = preceding_comment_block(source, line)
    if block is None:
        return ()
    start, end = block
    return (
        SourceExcerpt(
            path=source.path,
            start_line=start,
            end_line=end,
        ),
    )
