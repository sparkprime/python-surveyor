"""Tests for the ``fixture-naming`` check."""

from python_surveyor.checks.fixture_naming import run
from python_surveyor.scanner import _build_corpus


def test_plain_fixture_flagged(make_source_file, empty_corpus):
    source = "import pytest\n" "@pytest.fixture\n" "def db():\n" "    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert findings[0].check_id == "fixture-naming"
    assert "no `name=` kwarg" in findings[0].message
    assert "lacks `fixture_` prefix" in findings[0].message


def test_fixture_with_name_and_prefix_not_flagged(make_source_file, empty_corpus):
    source = (
        "import pytest\n"
        '@pytest.fixture(name="db")\n'
        "def fixture_db():\n"
        "    pass\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_fixture_prefix_without_name_flagged(make_source_file, empty_corpus):
    source = "import pytest\n" "@pytest.fixture\n" "def fixture_db():\n" "    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert "no `name=` kwarg" in findings[0].message


def test_name_without_prefix_flagged(make_source_file, empty_corpus):
    source = "import pytest\n" '@pytest.fixture(name="db")\n' "def db():\n" "    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert "lacks `fixture_` prefix" in findings[0].message


def test_bare_fixture_decorator(make_source_file, empty_corpus):
    source = "from pytest import fixture\n" "@fixture\n" "def db():\n" "    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1


def test_non_fixture_function_not_flagged(make_source_file, empty_corpus):
    source = "def db():\n    pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_collision_note(make_source_file):
    source = (
        "import pytest\n"
        "@pytest.fixture\n"
        "def db():\n"
        "    pass\n"
        "def test_thing(db):\n"
        "    pass\n"
    )
    source_file = make_source_file("a.py", source)
    corpus = _build_corpus([source_file], max_call_sites=5)
    findings = run(source_file, corpus)
    assert findings
    note = findings[0].notes[0]
    assert "registered as `db`" in note
    assert "1 other function" in note
