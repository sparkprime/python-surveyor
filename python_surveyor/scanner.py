"""Discovery, parsing, ``Corpus`` building, and check orchestration.

The scanner runs in two passes:

1. **Discover + parse.** Walk the given paths, prune the default
   ignore-directories plus anything matching ``--exclude``, read every
   ``*.py`` file, ``ast.parse`` it. Files that fail to parse become a
   ``ParseError`` and are excluded from further analysis rather than silently
   dropped.
2. **Build a ``Corpus``** over the successfully parsed files, giving every
   check a cheap, already-built answer to "does anything in what we scanned
   call/use this identifier" without re-parsing.
3. **Run checks.** Every check has the same signature so the internal check
   API itself has no optional parameters.
4. **Sort** findings by ``(check_id, path, line)`` and return a
   ``ScanResult``.
"""

import ast
import fnmatch
import os
import tokenize
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from python_surveyor.checks import ALL_CHECKS, COVERED_PYLINT_IDS, CheckSpec
from python_surveyor.model import CallSite, Finding, Location, ParseError

DEFAULT_PRUNED_DIRS: tuple[str, ...] = (
    ".venv",
    ".git",
    "__pycache__",
    "build",
    "dist",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".ruff_cache",
)


def _endswith_egg_info(name: str) -> bool:
    return name.endswith(".egg-info")


@dataclass(frozen=True, eq=False)
class SourceFile:
    """A parsed file plus its source text and tokens."""

    path: Path
    source: str
    lines: tuple[str, ...]
    tree: ast.Module
    tokens: tuple[tokenize.TokenInfo, ...]

    def line_text(self, line_no: int) -> str:
        """Return the (1-indexed) line's text, or ``""`` if out of range."""
        if 1 <= line_no <= len(self.lines):
            return self.lines[line_no - 1]
        return ""


@dataclass(frozen=True)
class Corpus:
    """Cross-file indices built once over every successfully parsed file.

    ``call_sites`` answers "is this name called anywhere we scanned?".
    ``param_locations`` answers "is this name used as a parameter anywhere?"
    and pairs each hit with the enclosing function's name so the
    fixture-naming check can spot redefined-outer-name collisions.
    ``max_call_sites`` is the cap the ``optional-param-default`` check applies
    when sampling call sites into a note (set by the scanner from the CLI
    flag so checks don't need optional parameters of their own).
    """

    call_sites: dict[str, tuple[CallSite, ...]]
    param_locations: dict[str, tuple[tuple[Location, str], ...]]
    max_call_sites: int
    covered_pylint_ids: frozenset[str]


@dataclass(frozen=True)
class ScanResult:
    """The output of a scan: findings plus any parse errors encountered."""

    findings: tuple[Finding, ...]
    parse_errors: tuple[ParseError, ...]
    files_scanned: int
    source_lines: "dict[str, tuple[str, ...]]"


def _discover(root_paths: tuple[str, ...], excludes: tuple[str, ...]) -> Iterator[Path]:
    """Walk ``root_paths`` and yield ``*.py`` file paths, pruning ignored dirs."""
    pruned_dirs = set(DEFAULT_PRUNED_DIRS)
    for root in root_paths:
        root_path = Path(root)
        if root_path.is_file():
            if root_path.suffix == ".py":
                yield root_path
            continue
        for dirpath, dirnames, filenames in os.walk(root_path):
            kept_dirs: list[str] = []
            for dirname in dirnames:
                if dirname in pruned_dirs or _endswith_egg_info(dirname):
                    continue
                if any(
                    fnmatch.fnmatch(dirname, pattern) for pattern in excludes
                ) or any(
                    fnmatch.fnmatch(os.path.join(dirpath, dirname), pattern)
                    for pattern in excludes
                ):
                    continue
                kept_dirs.append(dirname)
            dirnames[:] = kept_dirs
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                if any(fnmatch.fnmatch(filename, pattern) for pattern in excludes):
                    continue
                yield Path(dirpath) / filename


def _parse_file(path: Path) -> "tuple[SourceFile | None, ParseError | None]":
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as err:
        return None, ParseError(path=path, line=0, message=str(err))
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as err:
        line = err.lineno if err.lineno is not None else 0
        return None, ParseError(path=path, line=line, message=err.msg)
    token_list: list[tokenize.TokenInfo] = []
    try:
        with tokenize.open(str(path)) as readline:
            token_list = list(tokenize.generate_tokens(readline.readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        token_list = []
    lines = tuple(source.splitlines())
    return (
        SourceFile(
            path=path,
            source=source,
            lines=lines,
            tree=tree,
            tokens=tuple(token_list),
        ),
        None,
    )


def _resolve_call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _call_positional_count(node: ast.Call) -> int:
    """Count positional args (excluding ``*args`` spreads)."""
    return sum(1 for arg in node.args if not isinstance(arg, ast.Starred))


def _call_keywords(node: ast.Call) -> frozenset[str]:
    """Return the set of keyword arg names (excluding ``**kwargs`` spreads)."""
    return frozenset(kw.arg for kw in node.keywords if kw.arg is not None)


def _collect_params(
    func_node: "ast.FunctionDef | ast.AsyncFunctionDef",
    path: Path,
    param_locations: dict[str, list[tuple[Location, str]]],
) -> None:
    args = func_node.args
    skip_names = {"self", "cls"}
    names: list[str] = []
    for arg in args.posonlyargs:
        if arg.arg not in skip_names:
            names.append(arg.arg)
    for arg in args.args:
        if arg.arg not in skip_names:
            names.append(arg.arg)
    for arg in args.kwonlyargs:
        names.append(arg.arg)
    for name in names:
        param_locations.setdefault(name, []).append(
            (Location(path=path, line=func_node.lineno), func_node.name)
        )


def _build_corpus(
    source_files: list[SourceFile],
    max_call_sites: int,
    covered_pylint_ids: frozenset[str],
) -> Corpus:
    call_sites: dict[str, list[CallSite]] = {}
    param_locations: dict[str, list[tuple[Location, str]]] = {}
    for source_file in source_files:
        for node in ast.walk(source_file.tree):
            if isinstance(node, ast.Call):
                resolved = _resolve_call_name(node)
                if resolved is None:
                    continue
                call_sites.setdefault(resolved, []).append(
                    CallSite(
                        location=Location(path=source_file.path, line=node.lineno),
                        positional_count=_call_positional_count(node),
                        keywords=_call_keywords(node),
                    )
                )
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _collect_params(node, source_file.path, param_locations)
    return Corpus(
        call_sites={k: tuple(v) for k, v in call_sites.items()},
        param_locations={k: tuple(v) for k, v in param_locations.items()},
        max_call_sites=max_call_sites,
        covered_pylint_ids=covered_pylint_ids,
    )


def scan(
    root_paths: tuple[str, ...],
    check_ids: "tuple[str, ...] | None",
    excludes: tuple[str, ...],
    max_call_sites: int,
) -> ScanResult:
    """Run the full discover -> parse -> corpus -> checks pipeline."""
    if check_ids is None:
        enabled_checks: tuple[CheckSpec, ...] = tuple(ALL_CHECKS)
    else:
        wanted = set(check_ids)
        enabled_checks = tuple(
            check_spec for check_spec in ALL_CHECKS if check_spec.check_id in wanted
        )
        missing = wanted - {check_spec.check_id for check_spec in enabled_checks}
        if missing:
            raise ValueError(f"unknown check ids: {sorted(missing)}")
    source_files: list[SourceFile] = []
    parse_errors: list[ParseError] = []
    for path in _discover(root_paths, excludes):
        parsed, parse_err = _parse_file(path)
        if parse_err is not None:
            parse_errors.append(parse_err)
            continue
        assert parsed is not None
        source_files.append(parsed)
    corpus = _build_corpus(source_files, max_call_sites, COVERED_PYLINT_IDS)
    findings: list[Finding] = []
    for source_file in source_files:
        for check_spec in enabled_checks:
            findings.extend(check_spec.run(source_file, corpus))
    findings.sort(key=lambda f: (f.check_id, str(f.path), f.line))
    return ScanResult(
        findings=tuple(findings),
        parse_errors=tuple(parse_errors),
        files_scanned=len(source_files),
        source_lines={str(f.path): f.lines for f in source_files},
    )
