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
    source = "def helper(a=1):\n" "    pass\n" "def caller():\n" "    helper()\n"
    source_file = make_source_file("a.py", source)
    corpus = _build_corpus([source_file], max_call_sites=5)
    findings = run(source_file, corpus)
    assert findings
    notes = "\n".join(findings[0].notes)
    assert "using default" in notes
    assert "explicit value" in notes


def test_call_site_note_not_called(make_source_file):
    source = "def helper(a=1):\n    pass\n"
    source_file = make_source_file("a.py", source)
    corpus = _build_corpus([source_file], max_call_sites=5)
    findings = run(source_file, corpus)
    assert findings
    assert "not called from anywhere" in findings[0].notes[0]


def test_call_site_note_override(make_source_file):
    source = "def helper(a=1):\n" "    pass\n" "def caller():\n" "    helper(2)\n"
    source_file = make_source_file("a.py", source)
    corpus = _build_corpus([source_file], max_call_sites=5)
    findings = run(source_file, corpus)
    notes = "\n".join(findings[0].notes)
    assert "explicit value" in notes
    assert "using default" in notes


def test_call_site_note_mixed(make_source_file):
    source = (
        "def helper(a=1):\n"
        "    pass\n"
        "def c1():\n"
        "    helper()\n"
        "def c2():\n"
        "    helper(2)\n"
    )
    source_file = make_source_file("a.py", source)
    corpus = _build_corpus([source_file], max_call_sites=5)
    findings = run(source_file, corpus)
    notes = "\n".join(findings[0].notes)
    assert "explicit value" in notes
    assert "using default" in notes


def test_message_names_defaulted_params(make_source_file, empty_corpus):
    source = "def f(a, b=2, *, c=3):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert "b" in findings[0].message
    assert "c" in findings[0].message
    assert "a" not in findings[0].message.split(":")[-1]
