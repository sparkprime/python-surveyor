"""Tests for the ``mutable-module-global`` check."""

from python_surveyor.checks.mutable_globals import run


def test_lowercase_global_flagged(make_source_file, empty_corpus):
    source = "foo = 1\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert findings[0].check_id == "mutable-module-global"
    assert "`foo`" in findings[0].message


def test_upper_case_global_not_flagged(make_source_file, empty_corpus):
    source = "FOO = 1\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_dunder_not_flagged(make_source_file, empty_corpus):
    source = "__all__ = ['a']\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_local_assignment_not_flagged(make_source_file, empty_corpus):
    source = "def f():\n    foo = 1\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_global_inside_if_flagged(make_source_file, empty_corpus):
    source = "import os\nif os.name == 'nt':\n    config = 1\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert "`config`" in findings[0].message


def test_aug_assign_flagged(make_source_file, empty_corpus):
    source = "count = 0\ncount += 1\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert any("`count`" in f.message for f in findings)


def test_global_statement_note(make_source_file, empty_corpus):
    source = "state = 0\n" "def mutate():\n" "    global state\n" "    state = 1\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    mutable_findings = [f for f in findings if f.check_id == "mutable-module-global"]
    assert mutable_findings
    notes = "\n".join(mutable_findings[0].notes)
    assert "global state" in notes
    assert "1 function" in notes
