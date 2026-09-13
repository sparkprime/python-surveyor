"""Tests for the ``suppression-comment`` check."""

from python_surveyor.checks.suppressions import run


def test_pylint_disable_without_preceding_comment(make_source_file, empty_corpus):
    source = "x = 1  # pylint: disable=missing-docstring\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check_id == "suppression-comment"
    assert finding.notes == ()
    assert not any(e.label == "justifying comment" for e in finding.excerpts)


def test_pyright_ignore_without_preceding_comment(make_source_file, empty_corpus):
    source = "x = 1  # pyright: ignore\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert findings[0].notes == ()
    assert not any(e.label == "justifying comment" for e in findings[0].excerpts)


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
    excerpt = findings[0].excerpts[0]
    assert excerpt.label == "source"
    assert excerpt.start_line == 1
    assert excerpt.end_line == 3


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


def test_standalone_disable_extends_downward(make_source_file, empty_corpus):
    source = "# pylint: disable=missing-docstring\n" "def f():\n" "    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    excerpt = findings[0].excerpts[0]
    assert excerpt.start_line == 1
    assert excerpt.end_line == 3


def test_standalone_disable_capped_at_10_lines(make_source_file, empty_corpus):
    source = "# pylint: disable=all\n" + "x = 1\n" * 20
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    excerpt = findings[0].excerpts[0]
    assert excerpt.end_line == 11


def test_standalone_disable_with_enable(make_source_file, empty_corpus):
    source = (
        "# pylint: disable=missing-docstring\n"
        "def f():\n"
        "    pass\n"
        "# pylint: enable=missing-docstring\n"
        "def g():\n"
        "    pass\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    excerpt = findings[0].excerpts[0]
    assert excerpt.start_line == 1
    assert excerpt.end_line == 3


def test_trailing_disable_does_not_extend(make_source_file, empty_corpus):
    source = "x = 1  # pylint: disable=missing-docstring\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    excerpt = findings[0].excerpts[0]
    assert excerpt.end_line == 1


def test_broad_exception_caught_not_flagged(make_source_file, empty_corpus):
    source = "x = 1  # pylint: disable=broad-exception-caught\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_broad_exception_caught_in_list_not_flagged(make_source_file, empty_corpus):
    source = "x = 1  # pylint: disable=broad-exception-caught,missing-docstring\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_redefined_outer_name_not_flagged(make_source_file, empty_corpus):
    source = "x = 1  # pylint: disable=redefined-outer-name\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_redefined_outer_name_in_list_not_flagged(make_source_file, empty_corpus):
    source = "x = 1  # pylint: disable=redefined-outer-name,missing-docstring\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []
