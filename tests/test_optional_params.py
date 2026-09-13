"""Tests for the ``optional-param-default`` check."""

from python_surveyor.checks.optional_params import run
from python_surveyor.scanner import _build_corpus


def test_defaulted_positional_param(make_source_file, empty_corpus):
    source = "def f(a=1):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert findings[0].check_id == "optional-param-default"
    assert "`f`" in findings[0].message


def test_mixed_defaulted_positional(make_source_file, empty_corpus):
    source = "def f(a, b=2):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1


def test_defaulted_kwonly(make_source_file, empty_corpus):
    source = "def f(*, a=1):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1


def test_no_defaults_not_flagged(make_source_file, empty_corpus):
    source = "def f(a, b):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_args_kwargs_not_flagged(make_source_file, empty_corpus):
    source = "def f(*args, **kwargs):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_call_site_note_with_corpus(make_source_file):
    source = "def helper(a=1):\n    pass\n" "def caller():\n" "    helper()\n"
    source_file = make_source_file("a.py", source)
    corpus = _build_corpus([source_file], max_call_sites=5)
    findings = run(source_file, corpus)
    assert findings
    note = findings[0].notes[0]
    assert "called from 1 site" in note


def test_call_site_note_not_called(make_source_file):
    source = "def helper(a=1):\n    pass\n"
    source_file = make_source_file("a.py", source)
    corpus = _build_corpus([source_file], max_call_sites=5)
    findings = run(source_file, corpus)
    assert findings
    assert "not called from anywhere" in findings[0].notes[0]
