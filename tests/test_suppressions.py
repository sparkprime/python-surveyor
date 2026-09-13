"""Tests for the ``suppression-comment`` check."""

from python_surveyor.checks.suppressions import run


def test_pylint_disable_without_preceding_comment(make_source_file, empty_corpus):
    source = "x = 1  # pylint: disable=missing-docstring\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "suppression-comment"
    assert "no preceding comment found" in finding.notes


def test_pyright_ignore_without_preceding_comment(make_source_file, empty_corpus):
    source = "x = 1  # pyright: ignore\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert "no preceding comment found" in findings[0].notes


def test_pylint_disable_next_line(make_source_file, empty_corpus):
    source = "# pylint: disable-next-line=missing-docstring\nx = 1\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert findings[0].check_id == "suppression-comment"


def test_suppression_with_preceding_comment(make_source_file, empty_corpus):
    source = (
        "# We disable this because the function is a one-liner stub.\n"
        "# pylint: disable=missing-docstring\n"
        "x = 1\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert findings[0].notes == ()
    assert findings[0].excerpts[0].label == "preceding comments"


def test_no_suppression_comment(make_source_file, empty_corpus):
    source = "x = 1  # just a normal comment\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_string_containing_pylint_not_flagged(make_source_file, empty_corpus):
    source = 'msg = "pylint: disable=missing-docstring"\n'
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []
