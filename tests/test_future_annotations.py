"""Tests for the ``future-annotations-import`` check."""

from python_surveyor.checks.future_annotations import run


def test_future_annotations_flagged(make_source_file, empty_corpus):
    source = "from __future__ import annotations\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert findings[0].check_id == "future-annotations-import"


def test_other_future_import_not_flagged(make_source_file, empty_corpus):
    source = "from __future__ import division\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_combined_future_import_flagged(make_source_file, empty_corpus):
    source = "from __future__ import annotations, division\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1


def test_no_future_import(make_source_file, empty_corpus):
    source = "import os\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []
