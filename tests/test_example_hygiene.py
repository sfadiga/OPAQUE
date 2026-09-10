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


def _dynamic_stylesheets_outside_apply_theme(
        path: Path) -> List[Tuple[int, str]]:
    """
    Find setStyleSheet calls that bake a computed value outside apply_theme.

    A stylesheet built at run time (an f-string, a variable) embeds token
    values that go stale after a theme change. Such a stylesheet must be
    built inside apply_theme(), which the shell calls after every theme
    change. A plain string constant may stay where it is: the literal-style
    guard above screens it, and palette(...) roles inside it stay live
    because the shell repolishes every widget.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: List[Tuple[int, str]] = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name == "apply_theme":
            continue
        for node in ast.walk(func):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "setStyleSheet"
                    and node.args
                    and not isinstance(node.args[0], ast.Constant)):
                offenders.append((node.lineno, func.name))
    return offenders


@pytest.mark.parametrize(
    "path", _example_files(),
    ids=lambda p: str(p.relative_to(EXAMPLES_ROOT)))
def test_a_dynamic_stylesheet_is_built_only_in_apply_theme(path):
    offenders = _dynamic_stylesheets_outside_apply_theme(path)
    assert not offenders, (
        f"{path}: a computed stylesheet outside apply_theme() at "
        f"{offenders}. Token values go stale after a theme change; build "
        f"the stylesheet in apply_theme() and call it from setup_ui()."
    )


@pytest.mark.parametrize(
    "path", _example_files(),
    ids=lambda p: str(p.relative_to(EXAMPLES_ROOT)))
def test_a_class_that_declares_apply_theme_also_calls_it(path):
    """apply_theme() paints nothing until somebody calls it. The shell
    calls it on a theme change; the first paint is the class's own job."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        methods = [item for item in node.body
                   if isinstance(item, ast.FunctionDef)]
        if "apply_theme" not in {method.name for method in methods}:
            continue
        calls_it = any(
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "apply_theme"
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "self"
            for method in methods if method.name != "apply_theme"
            for call in ast.walk(method)
        )
        assert calls_it, (
            f"{path}: {node.name} declares apply_theme() but never calls "
            f"it, so the widget is unstyled until the first theme change."
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
