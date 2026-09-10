# This Python file uses the following encoding: utf-8
"""
The examples must obey the framework's own stated rules.

An example is what a user or an AI agent copies. An example that breaks a
rule teaches the violation, so the rules that can be checked mechanically
are checked here: no literal colour or font size inside setStyleSheet, no
cleanup() call inside on_view_close, no BaseView subclass that overrides
__init__ instead of setup_ui, and no tr() call without a literal argument.
"""

import ast
import re
from pathlib import Path
from typing import List, Tuple

import pytest

from tests.test_localisation import _non_literal_tr_calls

EXAMPLES_ROOT = Path(__file__).resolve().parents[1] / "examples"

# Hex colours, font sizes, and the named CSS colours the examples used.
_LITERAL_STYLE = re.compile(
    r"#[0-9a-fA-F]{3,8}\b"
    r"|font-size\s*:"
    r"|\bcolor\s*:\s*(gray|grey|white|black|red|green|blue)\b"
)


def _example_files() -> List[Path]:
    return sorted(EXAMPLES_ROOT.rglob("*.py"))


def _stylesheet_offenders(path: Path) -> List[Tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: List[Tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "setStyleSheet":
            continue
        for part in ast.walk(node):
            if (isinstance(part, ast.Constant)
                    and isinstance(part.value, str)
                    and _LITERAL_STYLE.search(part.value)):
                offenders.append((node.lineno, part.value.strip()))
    return offenders


@pytest.mark.parametrize(
    "path", _example_files(),
    ids=lambda p: str(p.relative_to(EXAMPLES_ROOT)))
def test_no_literal_colour_or_font_size_in_a_stylesheet(path):
    offenders = _stylesheet_offenders(path)
    assert not offenders, (
        f"{path}: literal colour or font size in setStyleSheet at "
        f"{offenders}. Use the tokens in opaque.view.theme instead."
    )


@pytest.mark.parametrize(
    "path", _example_files(),
    ids=lambda p: str(p.relative_to(EXAMPLES_ROOT)))
def test_on_view_close_never_calls_cleanup(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "on_view_close":
            continue
        for call in ast.walk(node):
            if (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "cleanup"):
                pytest.fail(
                    f"{path}:{call.lineno}: on_view_close() calls cleanup(). "
                    f"The framework calls cleanup() itself after the hook."
                )


@pytest.mark.parametrize(
    "path", _example_files(),
    ids=lambda p: str(p.relative_to(EXAMPLES_ROOT)))
def test_a_view_subclass_overrides_setup_ui_and_not_init(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        base_names = {
            base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
            for base in node.bases
        }
        if "BaseView" not in base_names:
            continue
        methods = {
            item.name for item in node.body
            if isinstance(item, ast.FunctionDef)
        }
        assert "__init__" not in methods, (
            f"{path}: view {node.name} overrides __init__. Build the "
            f"widgets in setup_ui(); the framework calls it."
        )
        assert "setup_ui" in methods, (
            f"{path}: view {node.name} does not override setup_ui()."
        )


@pytest.mark.parametrize(
    "path", _example_files(),
    ids=lambda p: str(p.relative_to(EXAMPLES_ROOT)))
def test_every_tr_call_carries_a_literal(path):
    offenders = _non_literal_tr_calls(path)
    assert not offenders, (
        f"{path}: tr() without a string literal at {offenders}. "
        f"lupdate cannot extract a variable."
    )
