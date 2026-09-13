"""Tests for the ``broad-except`` check."""

from python_surveyor.checks.broad_except import run


def test_except_exception(make_source_file, empty_corpus):
    source = (
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except Exception:\n"
        "        pass\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert findings[0].check_id == "broad-except"
    assert "Exception" in findings[0].message


def test_except_bare(make_source_file, empty_corpus):
    source = "def f():\n" "    try:\n" "        pass\n" "    except:\n" "        pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert "bare" in findings[0].message


def test_except_baseexception(make_source_file, empty_corpus):
    source = (
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except BaseException:\n"
        "        pass\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1


def test_except_tuple_with_exception(make_source_file, empty_corpus):
    source = (
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except (Exception, ValueError):\n"
        "        pass\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1


def test_except_specific_not_flagged(make_source_file, empty_corpus):
    source = (
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except ValueError:\n"
        "        pass\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings == []


def test_except_star_exception(make_source_file, empty_corpus):
    source = (
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except* Exception:\n"
        "        pass\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    assert "except*" in findings[0].message


def test_except_body_excerpt(make_source_file, empty_corpus):
    source = (
        "def f():\n"
        "    try:\n"
        "        pass\n"
        "    except Exception:\n"
        "        log_error()\n"
        "        cleanup()\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert findings[0].excerpts[0].label == "source"
