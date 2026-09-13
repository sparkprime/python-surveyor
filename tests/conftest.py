"""Shared pytest fixtures for python-surveyor tests.

Tests build their source strings inline and write them via ``tmp_path`` so
no intentionally-smelly ``.py`` files sit in the repo where they'd confuse a
reader (or get flagged by this very tool, or by pylint).

Fixtures follow the ``fixture_`` prefix + ``name=`` convention: the function
is prefixed ``fixture_`` and ``name=`` registers the true fixture name that
test functions use as their parameter name.
"""

import ast
import io
import tokenize
from pathlib import Path
from typing import Callable

import pytest

from python_surveyor.scanner import (
    Corpus,
    SourceFile,
    _build_corpus,
)


@pytest.fixture(name="make_source_file")
def fixture_make_source_file(tmp_path: Path) -> Callable[[str, str], SourceFile]:
    """A callable that writes ``source`` to ``tmp_path`` and builds a ``SourceFile``."""

    def make_source_file(name: str, source: str) -> SourceFile:
        path = tmp_path / name
        path.write_text(source, encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        return SourceFile(
            path=path,
            source=source,
            lines=tuple(source.splitlines()),
            tree=tree,
            tokens=tuple(tokens),
        )

    return make_source_file


@pytest.fixture(name="empty_corpus")
def fixture_empty_corpus() -> Corpus:
    """A ``Corpus`` with empty indices and the default call-site cap."""
    return Corpus(call_sites={}, param_locations={}, max_call_sites=5)


@pytest.fixture(name="make_corpus")
def fixture_make_corpus(
    make_source_file: Callable[[str, str], SourceFile],
) -> Callable[[dict[str, str]], Corpus]:
    """A callable that builds a ``Corpus`` over the given named sources."""

    def make_corpus(sources: dict[str, str]) -> Corpus:
        files = [make_source_file(name, src) for name, src in sources.items()]
        return _build_corpus(files, max_call_sites=5)

    return make_corpus
