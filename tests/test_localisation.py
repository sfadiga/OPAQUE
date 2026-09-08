# This Python file uses the following encoding: utf-8
"""
Source scans and tests for the localisation layer.

lupdate reads the source text of a tr() call, never the value at run time.
A tr() call whose argument is a variable or an f-string produces no entry in
the .ts file, so the string can never be translated. The scans below make
that a test failure instead of a silent gap.
"""

import ast
from pathlib import Path
from typing import List, Tuple

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "opaque"


def _python_files() -> List[Path]:
    """Every framework source file except the build tools."""
    return sorted(
        path for path in SOURCE_ROOT.rglob("*.py")
        if "build_tools" not in path.parts
    )


def _non_literal_tr_calls(path: Path) -> List[Tuple[int, str]]:
    """Return the line and the dump of every tr() call with no literal."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: List[Tuple[int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "tr":
            continue
        if not node.args:
            continue

        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            continue

        offenders.append((node.lineno, type(first).__name__))

    return offenders


def test_the_scanner_catches_a_variable_argument(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        "class A:\n"
        "    def go(self, name):\n"
        "        return self.tr(name)\n",
        encoding="utf-8",
    )
    assert _non_literal_tr_calls(sample) == [(3, "Name")]


def test_no_source_file_wraps_a_runtime_string():
    offenders = []
    for path in _python_files():
        for line, kind in _non_literal_tr_calls(path):
            relative = path.relative_to(SOURCE_ROOT.parents[1])
            offenders.append(f"{relative}:{line} ({kind})")
    assert offenders == []
