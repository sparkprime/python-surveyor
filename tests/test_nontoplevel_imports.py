"""Tests for the ``non-toplevel-import`` check."""

from python_surveyor.checks.nontoplevel_imports import run


def test_toplevel_import_not_flagged(make_source_file, empty_corpus):
    source = "import os\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_import_inside_function_flagged(make_source_file, empty_corpus):
    source = "def f():\n    import os\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert findings[0].check_id == "non-toplevel-import"
    assert "function `f`" in findings[0].notes[0]


def test_import_inside_if_flagged(make_source_file, empty_corpus):
    source = "if True:\n    import os\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert "if block" in findings[0].notes[0]


def test_type_checking_import_not_flagged(make_source_file, empty_corpus):
    source = (
        "from typing import TYPE_CHECKING\n" "if TYPE_CHECKING:\n" "    import os\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_from_import_inside_function_flagged(make_source_file, empty_corpus):
    source = "def f():\n    from os import path\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1


def test_import_inside_try_flagged(make_source_file, empty_corpus):
    source = (
        "try:\n"
        "    import optional_dep\n"
        "except ImportError:\n"
        "    optional_dep = None\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert "try block" in findings[0].notes[0]


def test_import_inside_class_flagged(make_source_file, empty_corpus):
    source = "class C:\n    import os\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert "class `C`" in findings[0].notes[0]
