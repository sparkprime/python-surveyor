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


def test_except_bare(make_source_file, empty_corpus):
    source = "def f():\n" "    try:\n" "        pass\n" "    except:\n" "        pass\n"
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1


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
    assert findings[0].check_id == "broad-except"


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
    assert len(findings) == 1
    excerpts = findings[0].excerpts
    assert len(excerpts) == 1
    assert excerpts[0].start_line == 4
    assert excerpts[0].end_line == 6


def test_except_long_try_body_split_excerpts(make_source_file, empty_corpus):
    source = (
        "def f():\n"
        "    try:\n"
        + "        pass\n" * 20
        + "    except Exception:\n"
        + "        pass\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    excerpts = findings[0].excerpts
    assert len(excerpts) == 1
    handler_line = 2 + 20 + 1
    assert excerpts[0].start_line == handler_line
    assert excerpts[0].end_line == handler_line + 1


def test_except_with_justifying_comment(make_source_file, empty_corpus):
    source = (
        "def f():\n"
        "# We catch Exception here because the subprocess\n"
        "# may already be dead during shutdown.\n"
        "    try:\n"
        "        pass\n"
        "    except Exception:\n"
        "        pass\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    excerpts = findings[0].excerpts
    assert len(excerpts) == 2
    assert excerpts[0].start_line == 2
    assert excerpts[0].end_line == 4
    assert excerpts[1].start_line == 6
    assert excerpts[1].end_line == 7


def test_try_with_comments_after(make_source_file, empty_corpus):
    source = (
        "def f():\n"
        "    try:\n"
        "        # This is a comment about the try\n"
        "        # And another line\n"
        "        actual_code()\n"
        "        more_code()\n"
        "    except Exception:\n"
        "        pass\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    excerpts = findings[0].excerpts
    assert len(excerpts) == 2
    first = excerpts[0]
    second = excerpts[1]
    assert first.start_line == 2
    assert first.end_line == 4
    assert second.start_line == 7
    assert second.end_line == 8


def test_try_with_comments_after_merged(make_source_file, empty_corpus):
    source = (
        "def f():\n"
        "    try:\n"
        "        # comment about try\n"
        "        pass\n"
        "    except Exception:\n"
        "        pass\n"
    )
    source_file = make_source_file("a.py", source)
    findings = run(source_file, empty_corpus)
    assert len(findings) == 1
    excerpts = findings[0].excerpts
    assert len(excerpts) == 2
    assert excerpts[0].start_line == 2
    assert excerpts[0].end_line == 3
    assert excerpts[1].start_line == 5
    assert excerpts[1].end_line == 6
