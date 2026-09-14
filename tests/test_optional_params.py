"""Tests for the ``optional-param-default`` check."""

from python_surveyor.checks import COVERED_PYLINT_IDS
from python_surveyor.checks.optional_params import run
from python_surveyor.scanner import _build_corpus


def test_defaulted_positional_param(make_source_file, empty_corpus):
    source = "def f(a=1):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert findings[0].check_id == "optional-param-default"
    notes = "\n".join(findings[0].notes)
    assert "`f`" in notes


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
    corpus = _build_corpus([source_file], 10, COVERED_PYLINT_IDS)
    findings = run(source_file, corpus)
    assert findings
    notes = "\n".join(findings[0].notes)
    assert "using defaults" in notes


def test_call_site_note_not_called(make_source_file):
    source = "def helper(a=1):\n" "    pass\n"
    source_file = make_source_file("a.py", source)
    corpus = _build_corpus([source_file], 10, COVERED_PYLINT_IDS)
    findings = run(source_file, corpus)
    assert findings
    assert "not called from anywhere" in findings[0].notes[1]


def test_call_site_note_override(make_source_file):
    source = "def helper(a=1):\n" "    pass\n" "def caller():\n" "    helper(2)\n"
    source_file = make_source_file("a.py", source)
    corpus = _build_corpus([source_file], 10, COVERED_PYLINT_IDS)
    findings = run(source_file, corpus)
    notes = "\n".join(findings[0].notes)
    assert "override every defaulted parameter" in notes


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
    corpus = _build_corpus([source_file], 10, COVERED_PYLINT_IDS)
    findings = run(source_file, corpus)
    notes = "\n".join(findings[0].notes)
    assert "using defaults" in notes
    assert "1 of 2" in notes


def test_call_site_note_truncation(make_source_file):
    source = "def helper(a=1):\n    pass\n"
    for i in range(15):
        source += f"def c{i}():\n    helper()\n"
    source_file = make_source_file("a.py", source)
    corpus = _build_corpus([source_file], 10, COVERED_PYLINT_IDS)
    findings = run(source_file, corpus)
    notes = "\n".join(findings[0].notes)
    assert "and 5 other(s)" in notes


def test_defaulted_param_names_in_notes(make_source_file, empty_corpus):
    source = "def f(a, b=2, *, c=3):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    notes = "\n".join(findings[0].notes)
    assert "b" in notes
    assert "c" in notes
    # "a" should not appear in the defaulted-params note (it has no default)
    defaulted_note = [n for n in findings[0].notes if "Defaulted params" in n][0]
    assert "a" not in defaulted_note.split(":")[-1]


def test_signature_excerpt_not_full_body(make_source_file, empty_corpus):
    source = "def f(a=1):\n" + "    x = 1\n" * 30 + "    return x\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    excerpt = findings[0].excerpts[0]
    assert excerpt.start_line == 1
    assert excerpt.end_line == 1


def test_no_api_note(make_source_file, empty_corpus):
    source = "def _helper(a=1):\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    notes = "\n".join(findings[0].notes)
    assert "API" not in notes
