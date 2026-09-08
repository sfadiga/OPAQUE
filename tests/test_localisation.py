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

from PySide6.QtCore import QLocale

from opaque.localisation import install_translator, translation_candidates

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


# Setters whose first string argument is read by a person.
_TRANSLATED_SETTERS = {
    "setText",
    "setToolTip",
    "setWindowTitle",
    "setPlaceholderText",
    "setAccessibleName",
    "setAccessibleDescription",
    "setStatusTip",
    "setTitle",
    "addMenu",
}

# Widgets whose first argument is a label the user reads.
_TRANSLATED_CONSTRUCTORS = {
    "QLabel",
    "QPushButton",
    "QCheckBox",
    "QRadioButton",
    "QAction",
    "QGroupBox",
}

# Files that are not part of the interface.
_SCAN_SKIP = {"build_tools", "localisation.py"}


def _is_a_readable_string(node: ast.AST) -> bool:
    """True for a string literal that holds at least one letter."""
    if not isinstance(node, ast.Constant):
        return False
    if not isinstance(node.value, str):
        return False
    return any(character.isalpha() for character in node.value)


def _untranslated_strings(path: Path) -> List[int]:
    """Return the line of every user visible literal that is not in tr()."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: List[int] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue

        name = None
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
            if name not in _TRANSLATED_SETTERS:
                continue
        elif isinstance(node.func, ast.Name):
            name = node.func.id
            if name not in _TRANSLATED_CONSTRUCTORS:
                continue
        else:
            continue

        if _is_a_readable_string(node.args[0]):
            offenders.append(node.lineno)

    return offenders


def _interface_files() -> List[Path]:
    """Every source file that builds part of the interface."""
    files = []
    for path in _python_files():
        if any(part in _SCAN_SKIP for part in path.parts):
            continue
        if path.name in _SCAN_SKIP:
            continue
        files.append(path)
    return files


def test_the_scanner_catches_a_bare_label(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def build():\n"
        "    return QLabel(\"Hello\")\n",
        encoding="utf-8",
    )
    assert _untranslated_strings(sample) == [2]


def test_no_interface_file_shows_an_untranslated_string():
    offenders = []
    for path in _interface_files():
        for line in _untranslated_strings(path):
            relative = path.relative_to(SOURCE_ROOT.parents[1])
            offenders.append(f"{relative}:{line}")
    assert offenders == []


def test_the_candidates_start_with_the_most_specific_name():
    names = translation_candidates(QLocale("pt_BR"))
    assert names[0] == "opaque_pt_BR"


def test_the_candidates_end_with_the_language_only_name():
    names = translation_candidates(QLocale("pt_BR"))
    assert names[-1] == "opaque_pt"


def test_the_candidates_have_no_duplicates():
    names = translation_candidates(QLocale("en_US"))
    assert len(names) == len(set(names))


def test_no_translator_is_installed_when_nothing_matches(qapp, tmp_path):
    installed = install_translator(
        qapp, directory=str(tmp_path), locale=QLocale("zz_ZZ"))
    assert installed is None


def test_the_translations_directory_ships_with_the_package():
    assert (SOURCE_ROOT / "translations").is_dir()
