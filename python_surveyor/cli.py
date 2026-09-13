"""``click`` CLI: ``scan`` and ``list-checks`` commands."""

import sys
from pathlib import Path
from typing import TextIO

import click

from python_surveyor.checks import ALL_CHECKS
from python_surveyor.report import render_json, render_text
from python_surveyor.scanner import scan


@click.group()
def main() -> None:
    """python-surveyor: AST-based scanner for AI-generated-code smells."""


@main.command("scan")
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option(
    "--check",
    "check_ids",
    multiple=True,
    help="Restrict to this check id (repeatable).",
)
@click.option(
    "--exclude",
    "excludes",
    multiple=True,
    help="fnmatch pattern to exclude (repeatable, additive to defaults).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format. Default: text.",
)
@click.option(
    "--output",
    "output",
    type=click.Path(path_type=Path),
    default=None,
    help="Write to PATH instead of stdout.",
)
@click.option(
    "--max-excerpt-lines",
    "max_excerpt_lines",
    type=int,
    default=20,
    help="Cap excerpt line count (default 20).",
)
@click.option(
    "--max-call-sites",
    "max_call_sites",
    type=int,
    default=5,
    help="Cap call-site samples in notes (default 5).",
)
def scan_cmd(
    paths: tuple[str, ...],
    check_ids: tuple[str, ...],
    excludes: tuple[str, ...],
    fmt: str,
    output: "Path | None",
    max_excerpt_lines: int,
    max_call_sites: int,
) -> None:
    """Scan PATHS for AI-generated-code smells."""
    root_paths: tuple[str, ...] = paths if paths else (".",)
    result = scan(
        root_paths=root_paths,
        check_ids=check_ids if check_ids else None,
        excludes=excludes,
        max_call_sites=max_call_sites,
    )
    stream: TextIO
    if output is not None:
        stream = output.open("w", encoding="utf-8")
    else:
        stream = sys.stdout
    try:
        if fmt == "json":
            render_json(result, max_excerpt_lines, stream)
        else:
            render_text(result, max_excerpt_lines, stream)
    finally:
        if output is not None:
            stream.close()


@main.command("list-checks")
def list_checks_cmd() -> None:
    """List available check ids and descriptions."""
    click.echo("id\tdescription")
    for check_spec in ALL_CHECKS:
        click.echo(f"{check_spec.check_id}\t{check_spec.description}")


if __name__ == "__main__":
    main()
