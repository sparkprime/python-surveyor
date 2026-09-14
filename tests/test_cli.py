"""End-to-end CLI tests using click's ``CliRunner``."""

from click.testing import CliRunner

from python_surveyor.cli import main


def test_list_checks():
    runner = CliRunner()
    result = runner.invoke(main, ["list-checks"])
    assert result.exit_code == 0
    assert "broad-except" in result.output
    assert "fixture-naming" in result.output
    assert "future-annotations-import" in result.output


def test_scan_text(tmp_path):
    (tmp_path / "a.py").write_text(
        "from __future__ import annotations\n", encoding="utf-8"
    )
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "future-annotations-import" in result.output
    assert "file(s) scanned" in result.output


def test_scan_no_findings(tmp_path):
    (tmp_path / "clean.py").write_text("CONST = 1\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "no findings" in result.output


def test_scan_output_to_file(tmp_path):
    (tmp_path / "a.py").write_text(
        "from __future__ import annotations\n", encoding="utf-8"
    )
    out_path = tmp_path / "report.txt"
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path), "--output", str(out_path)])
    assert result.exit_code == 0
    assert "future-annotations-import" in out_path.read_text(encoding="utf-8")


def test_scan_check_filter(tmp_path):
    (tmp_path / "a.py").write_text(
        "from __future__ import annotations\n" "def f(a=1):\n    pass\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["scan", str(tmp_path), "--check", "future-annotations-import"],
    )
    assert result.exit_code == 0
    assert "future-annotations-import" in result.output
    assert "optional-param-default" not in result.output


def test_scan_parse_error_section(tmp_path):
    (tmp_path / "broken.py").write_text("def f(:\n    pass\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "parse errors" in result.output
