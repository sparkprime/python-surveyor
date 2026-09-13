"""Tests for the scanner: discovery, parsing, corpus building, orchestration."""

import ast
import dataclasses

import pytest

from python_surveyor.scanner import (
    Corpus,
    ScanResult,
    SourceFile,
    _build_corpus,
    scan,
)


def test_scan_finds_smelly_file(tmp_path):
    smelly = tmp_path / "smelly.py"
    smelly.write_text(
        "from __future__ import annotations\n" "def f(a=1):\n    pass\n",
        encoding="utf-8",
    )
    result = scan(
        root_paths=(str(tmp_path),),
        check_ids=None,
        excludes=(),
        max_call_sites=5,
    )
    check_ids_found = {f.check_id for f in result.findings}
    assert "future-annotations-import" in check_ids_found
    assert "optional-param-default" in check_ids_found
    assert result.files_scanned == 1


def test_scan_parse_error(tmp_path):
    broken = tmp_path / "broken.py"
    broken.write_text("def f(:\n    pass\n", encoding="utf-8")
    result = scan(
        root_paths=(str(tmp_path),),
        check_ids=None,
        excludes=(),
        max_call_sites=5,
    )
    assert result.parse_errors
    assert result.parse_errors[0].path == broken
    assert result.files_scanned == 0


def test_scan_prunes_venv(tmp_path):
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / "bad.py").write_text(
        "from __future__ import annotations\n", encoding="utf-8"
    )
    (tmp_path / "good.py").write_text("CONST = 1\n", encoding="utf-8")
    result = scan(
        root_paths=(str(tmp_path),),
        check_ids=None,
        excludes=(),
        max_call_sites=5,
    )
    assert result.files_scanned == 1
    assert result.findings == ()
    assert result.parse_errors == ()


def test_scan_exclude_glob(tmp_path):
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "bad.py").write_text(
        "from __future__ import annotations\n", encoding="utf-8"
    )
    (tmp_path / "good.py").write_text("CONST = 1\n", encoding="utf-8")
    result = scan(
        root_paths=(str(tmp_path),),
        check_ids=None,
        excludes=("vendor",),
        max_call_sites=5,
    )
    assert result.files_scanned == 1


def test_scan_check_subset(tmp_path):
    (tmp_path / "a.py").write_text(
        "from __future__ import annotations\n" "def f(a=1):\n    pass\n",
        encoding="utf-8",
    )
    result = scan(
        root_paths=(str(tmp_path),),
        check_ids=("future-annotations-import",),
        excludes=(),
        max_call_sites=5,
    )
    assert all(f.check_id == "future-annotations-import" for f in result.findings)
    assert any(f.check_id == "future-annotations-import" for f in result.findings)


def test_scan_unknown_check_id_raises():
    with pytest.raises(ValueError):
        scan(
            root_paths=(".",),
            check_ids=("nonexistent-check",),
            excludes=(),
            max_call_sites=5,
        )


def test_build_corpus_call_sites(tmp_path):
    source = (
        "def helper():\n"
        "    pass\n"
        "def caller():\n"
        "    helper()\n"
        "    other.method()\n"
    )
    path = tmp_path / "a.py"
    path.write_text(source, encoding="utf-8")
    tree = ast.parse(source)
    source_file = SourceFile(
        path=path,
        source=source,
        lines=tuple(source.splitlines()),
        tree=tree,
        tokens=(),
    )
    corpus = _build_corpus([source_file], max_call_sites=5)
    assert "helper" in corpus.call_sites
    assert "method" in corpus.call_sites


def test_build_corpus_param_locations(tmp_path):
    source = "def f(db):\n" "    pass\n" "def g(db):\n" "    pass\n"
    path = tmp_path / "a.py"
    path.write_text(source, encoding="utf-8")
    tree = ast.parse(source)
    source_file = SourceFile(
        path=path,
        source=source,
        lines=tuple(source.splitlines()),
        tree=tree,
        tokens=(),
    )
    corpus = _build_corpus([source_file], max_call_sites=5)
    assert "db" in corpus.param_locations
    assert len(corpus.param_locations["db"]) == 2


def test_scan_result_is_sorted(tmp_path):
    (tmp_path / "b.py").write_text(
        "from __future__ import annotations\n", encoding="utf-8"
    )
    (tmp_path / "a.py").write_text(
        "from __future__ import annotations\n", encoding="utf-8"
    )
    result = scan(
        root_paths=(str(tmp_path),),
        check_ids=None,
        excludes=(),
        max_call_sites=5,
    )
    paths = [str(f.path) for f in result.findings]
    assert paths == sorted(paths)


def test_corpus_is_immutable():
    corpus = Corpus(call_sites={}, param_locations={}, max_call_sites=5)
    with pytest.raises(dataclasses.FrozenInstanceError):
        corpus.max_call_sites = 10  # type: ignore[misc]


def test_scan_result_fields(tmp_path):
    (tmp_path / "a.py").write_text("CONST = 1\n", encoding="utf-8")
    result = scan(
        root_paths=(str(tmp_path),),
        check_ids=None,
        excludes=(),
        max_call_sites=5,
    )
    assert isinstance(result, ScanResult)
    assert result.files_scanned == 1
