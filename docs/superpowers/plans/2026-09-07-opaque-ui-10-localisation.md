# Plan 10 — Localisation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the framework translatable: every string `lupdate` can read, a translator that actually loads at start up, and a mirrored layout for a right to left language.

**Architecture:** Two source scan tests, both built on `ast`, keep the source honest: one forbids a `tr()` call with anything other than a string literal, the other forbids a user visible string that is not inside `tr()`. A new module, `opaque.localisation`, holds the pure decisions about which translation file to try and which layout direction to use, so both can be tested without a translation file on disk.

**Tech Stack:** PySide6, `QTranslator`, `QLocale`, pytest.

Read **Rules for the executing agent** in `2026-09-07-opaque-ui-00-index.md` before you start.

**Depends on:** Plan 01 to Plan 09. The scan tests in Task 1 and Task 2 check strings that those plans add.

**About the totals:** the `pytest -q` totals assume Plan 01 to Plan 09 are merged.

---

## Findings closed by this plan

| ID | Finding | Task |
|---|---|---|
| C11 | Localisation does not work | 1, 2, 3, 4 |

---

## What is actually wrong

The audit said localisation does not work. Here is the exact state of the source:

1. The whole framework has **24** `tr()` calls. Two of them pass a **variable**, not a literal: `toolbar.py` wraps `feature_name`, and `settings.py` wraps `field.description`. `lupdate` reads source text, so it can extract neither.
2. `src/opaque/view` alone has about **44** user visible strings that are not inside `tr()` at all.
3. There is no `QTranslator`, no `QLocale` handling, no `translations` directory and no `.ts` file anywhere in the repository.
4. Nothing sets the layout direction, so an Arabic or Hebrew user gets a mirrored language inside an unmirrored interface.

Point 3 is the largest of the four. Even a perfectly marked source cannot be translated when nothing loads a translation.

---

## File Structure

| Path | Responsibility |
|---|---|
| Create `src/opaque/localisation.py` | `translation_candidates`, `install_translator`, `apply_layout_direction`. |
| Create `src/opaque/translations/README.md` | How to run `lupdate` and `lrelease`. The directory also ships the `.qm` files. |
| Modify `src/opaque/view/widgets/toolbar.py` | Stop wrapping a runtime feature name. |
| Modify `src/opaque/view/dialogs/settings.py` | Stop wrapping a runtime field description. |
| Modify `src/opaque/view/application.py` | Install the translator and the layout direction at start up. |
| Create `tests/test_localisation.py` | The two source scans and the localisation module tests. |

---

### Task 1: A `tr()` call must hold a literal

`lupdate` is a source scanner. It reads the text of the call, not the value at run time. `self.tr(feature_name)` therefore produces no entry in the `.ts` file, and the string can never be translated. It also gives the reader a false sense that the string is handled.

**Files:**
- Modify: `src/opaque/view/widgets/toolbar.py`
- Modify: `src/opaque/view/dialogs/settings.py`
- Test: `tests/test_localisation.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_localisation.py` with exactly this content:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_localisation.py -q
```

Expected: FAIL. `test_no_source_file_wraps_a_runtime_string` lists two entries, one in `toolbar.py` and one in `settings.py`.

`test_the_scanner_catches_a_variable_argument` must pass. If it does not, the scanner itself is wrong. Stop and report it.

- [ ] **Step 3: Stop the toolbar wrapping a runtime name**

In `src/opaque/view/widgets/toolbar.py`, replace this block:

```python
        button.setText(self.tr(feature_name))
        button.setToolTip(self.tr(presenter.model.feature_description()))
```

with exactly this:

```python
        # These two strings belong to the feature, not to the toolbar. Only
        # the code that writes the literal can call tr() on it, because
        # lupdate reads the source text and not the value at run time.
        button.setText(feature_name)
        button.setToolTip(presenter.model.feature_description())
```

- [ ] **Step 4: Stop the Settings dialog wrapping a runtime description**

In `src/opaque/view/dialogs/settings.py`, replace this line:

```python
            label_text = self.tr(field.description) or name
```

with exactly this:

```python
            # The description comes from a model field at run time. The model
            # that declares the field must call tr() on its own literal.
            label_text = field.description or name
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_localisation.py -q
```

Expected: PASS. `2 passed`.

- [ ] **Step 6: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `223 passed`.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/widgets/toolbar.py src/opaque/view/dialogs/settings.py tests/test_localisation.py
git commit -m "fix(i18n): only ever pass a literal to tr()"
```

---

### Task 2: Every user visible string must be inside `tr()`

About forty four strings in `src/opaque/view` are written straight into a widget. None of them can be translated.

**Files:**
- Modify: every file the scan below reports.
- Test: `tests/test_localisation.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/test_localisation.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_localisation.py::test_no_interface_file_shows_an_untranslated_string -q
```

Expected: FAIL. The assertion message lists every file and line that still holds a bare string.

- [ ] **Step 3: Wrap every reported string**

Work through the list the test printed, one line at a time. For each one:

- If the call is inside a `QWidget` subclass, wrap the literal in `self.tr(...)`.
  `QLabel("Notifications")` becomes `QLabel(self.tr("Notifications"))`.
- If the call is inside a module level function with no `self`, import `QCoreApplication` and use `QCoreApplication.translate("<ClassOrModuleName>", "...")`.
- Never change the words. Never join two literals. Never turn a literal into an f-string.

Run the test again after every file. Stop when it passes.

Do **not** widen `_SCAN_SKIP` and do **not** remove a setter or a constructor from the two sets above. If a string genuinely must not be translated, for example a file extension or an object name, that call is not on the list in the first place.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_localisation.py -q
```

Expected: PASS. `4 passed`.

- [ ] **Step 5: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `225 passed`.

If a test from an earlier plan now fails because it compared against an exact string, keep the string the same and only add `tr()` around it. `tr()` returns the source string when no translation is loaded, so no assertion should need to change. If one does, the words were changed. Put them back.

- [ ] **Step 6: Commit**

```bash
git add src/opaque tests/test_localisation.py
git commit -m "fix(i18n): put every user visible string inside tr()"
```

---

### Task 3: Load a translation at start up

A perfectly marked source still shows English when nothing installs a `QTranslator`.

**Files:**
- Create: `src/opaque/localisation.py`
- Create: `src/opaque/translations/README.md`
- Modify: `src/opaque/view/application.py`
- Test: `tests/test_localisation.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/test_localisation.py`:

```python
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
```

Then add these two imports at the top of `tests/test_localisation.py`, below the `from typing import ...` line:

```python
from PySide6.QtCore import QLocale

from opaque.localisation import install_translator, translation_candidates
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_localisation.py -q
```

Expected: FAIL, with `ModuleNotFoundError: No module named 'opaque.localisation'`.

- [ ] **Step 3: Write the module**

Create `src/opaque/localisation.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

Localisation.

The source language of the framework is English. A missing translation file is
normal, not an error, so nothing here raises and nothing here logs an error
when a file is not found.
"""

import logging
import os
from typing import List, Optional

from PySide6.QtCore import QLocale, QTranslator, Qt
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

TRANSLATION_PREFIX = "opaque"


def translations_directory() -> str:
    """Return the directory that ships the compiled .qm files."""
    return os.path.join(os.path.dirname(__file__), "translations")


def translation_candidates(
    locale: QLocale,
    prefix: str = TRANSLATION_PREFIX,
) -> List[str]:
    """
    Return the translation file base names to try, most specific first.

    Args:
        locale: The locale to translate into.
        prefix: The file name prefix, without the language part.

    Returns:
        A list such as ["opaque_pt_BR", "opaque_pt"]. The list holds no
        duplicates and keeps its order.
    """
    names: List[str] = []

    def _add(name: str) -> None:
        candidate = f"{prefix}_{name}"
        if candidate not in names:
            names.append(candidate)

    _add(locale.name())
    for language in locale.uiLanguages():
        _add(language.replace("-", "_"))
    _add(locale.name().split("_")[0])

    return names


def install_translator(
    app: QApplication,
    directory: Optional[str] = None,
    locale: Optional[QLocale] = None,
) -> Optional[QTranslator]:
    """
    Load the best matching translation and install it on the application.

    Args:
        app: The application to install the translator on.
        directory: Where the .qm files live. Defaults to the directory that
            ships with the framework.
        locale: The locale to load. Defaults to the system locale.

    Returns:
        The installed QTranslator, or None when no file matched.
    """
    locale = locale or QLocale.system()
    directory = directory or translations_directory()

    for name in translation_candidates(locale):
        translator = QTranslator(app)
        if translator.load(name, directory):
            app.installTranslator(translator)
            logger.info("Loaded the translation %s", name)
            return translator

    logger.debug("No translation found for %s, showing the source language",
                 locale.name())
    return None


def apply_layout_direction(
    app: QApplication,
    locale: Optional[QLocale] = None,
) -> Qt.LayoutDirection:
    """
    Mirror the whole interface when the language reads right to left.

    Arabic, Hebrew, Farsi and Urdu mirror the layout, so navigation moves from
    right to left and a back arrow points right. Qt mirrors anchors and
    layouts by itself once the direction is set on the application.

    Args:
        app: The application to set the direction on.
        locale: The locale to read the direction from. Defaults to the system
            locale.

    Returns:
        The direction that was applied.
    """
    locale = locale or QLocale.system()
    direction = locale.textDirection()
    app.setLayoutDirection(direction)
    return direction
```

- [ ] **Step 4: Create the translations directory**

Create `src/opaque/translations/README.md` with exactly this content:

```markdown
# Translations

The source language of the OPAQUE framework is English. This directory holds
the compiled `.qm` files that `opaque.localisation.install_translator` loads at
start up. A missing file is normal: the framework then shows English.

## Add a language

Run both commands from the repository root. Replace `pt_BR` with the locale you
want.

1. Collect every string from the source into a `.ts` file:

```
venv\Scripts\pyside6-lupdate.exe src/opaque -ts src/opaque/translations/opaque_pt_BR.ts
```

2. Translate the `.ts` file. `venv\Scripts\pyside6-linguist.exe` opens it.

3. Compile the `.ts` file into the `.qm` file the application loads:

```
venv\Scripts\pyside6-lrelease.exe src/opaque/translations/opaque_pt_BR.ts -qm src/opaque/translations/opaque_pt_BR.qm
```

## Rules

- `lupdate` reads the **source text** of a `tr()` call. `tr(variable)` and
  `tr(f"...")` produce nothing. `tests/test_localisation.py` fails the build
  when either appears.
- Commit the `.ts` file. Commit the `.qm` file too, so a user does not need
  the Qt tools to run the application.
- A translated string is often 30 to 40 per cent longer than the English
  source. Never give a container that holds a translated string a fixed size.
```

- [ ] **Step 5: Install the translator at start up**

In `src/opaque/view/application.py`, replace this block in `__init__`:

```python
        # Make this window accessible to views via QApplication
        app = QApplication.instance()
        if app:
            app.main_window = self  # type: ignore
```

with exactly this:

```python
        # Make this window accessible to views via QApplication
        app = QApplication.instance()
        if app:
            app.main_window = self  # type: ignore
            # The translator must be installed before any widget is built.
            # A widget reads its strings once, when it is created.
            install_translator(app)
            apply_layout_direction(app)
```

Then add this import directly below the `from opaque.services.service import ServiceLocator` line:

```python
from opaque.localisation import apply_layout_direction, install_translator
```

- [ ] **Step 6: Ship the directory in the wheel**

In `pyproject.toml`, find the section that lists the package data. If a `[tool.setuptools.package-data]` section exists, add this line under it:

```toml
opaque = ["translations/*.qm", "translations/*.ts"]
```

If no such section exists, add the whole section at the end of the file:

```toml

[tool.setuptools.package-data]
opaque = ["translations/*.qm", "translations/*.ts"]
```

- [ ] **Step 7: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_localisation.py -q
```

Expected: PASS. `9 passed`.

- [ ] **Step 8: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `230 passed`.

- [ ] **Step 9: Commit**

```bash
git add src/opaque/localisation.py src/opaque/translations src/opaque/view/application.py pyproject.toml tests/test_localisation.py
git commit -m "feat(i18n): load a translation and set the layout direction at start up"
```

---

### Task 4: Prove the mirrored layout

**Files:**
- Test: `tests/test_localisation.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/test_localisation.py`:

```python
@pytest.fixture
def restored_direction(qapp):
    """Put the layout direction back after the test."""
    original = qapp.layoutDirection()
    yield qapp
    qapp.setLayoutDirection(original)


def test_an_arabic_locale_mirrors_the_layout(restored_direction):
    direction = apply_layout_direction(
        restored_direction, QLocale("ar_EG"))
    assert direction == Qt.LayoutDirection.RightToLeft
    assert restored_direction.layoutDirection() == \
        Qt.LayoutDirection.RightToLeft


def test_an_english_locale_does_not_mirror_the_layout(restored_direction):
    direction = apply_layout_direction(
        restored_direction, QLocale("en_GB"))
    assert direction == Qt.LayoutDirection.LeftToRight
    assert restored_direction.layoutDirection() == \
        Qt.LayoutDirection.LeftToRight


def test_a_hebrew_locale_mirrors_the_layout(restored_direction):
    direction = apply_layout_direction(
        restored_direction, QLocale("he_IL"))
    assert direction == Qt.LayoutDirection.RightToLeft
```

Then replace this import block at the top of `tests/test_localisation.py`:

```python
from PySide6.QtCore import QLocale

from opaque.localisation import install_translator, translation_candidates
```

with exactly this:

```python
import pytest
from PySide6.QtCore import QLocale, Qt

from opaque.localisation import (
    apply_layout_direction,
    install_translator,
    translation_candidates,
)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_localisation.py -q
```

Expected: FAIL, with `ImportError: cannot import name 'apply_layout_direction'` if Task 3 was skipped. If Task 3 is done, all three tests pass at once. That is correct: Task 3 wrote the function and this task proves it.

- [ ] **Step 3: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `233 passed`.

- [ ] **Step 4: Check the running application in a mirrored layout**

Run:

```
venv\Scripts\python.exe examples\basic_example\main.py -platform windows:darkmode=0
```

Then, in a second run, force the direction by setting the environment variable first:

```
$env:LANG = "ar_EG"; venv\Scripts\python.exe examples\basic_example\main.py
```

Expected: the toolbar, the menu bar and the dock all move to the right side of the window. Nothing is cut off and no text overlaps.

If the layout does not mirror, the system locale is overriding `LANG`. That is a platform behaviour and not a defect in this code. Note it and continue.

- [ ] **Step 5: Commit**

```bash
git add tests/test_localisation.py
git commit -m "test(i18n): prove the layout mirrors for a right to left locale"
```

---

## Definition of done

- [ ] `venv\Scripts\python.exe -m pytest tests/test_localisation.py -q` prints `12 passed`.
- [ ] `venv\Scripts\python.exe -m pytest -q` reports zero failures.
- [ ] `venv\Scripts\pyside6-lupdate.exe src/opaque -ts src/opaque/translations/opaque_pt_BR.ts` produces a `.ts` file that holds more than 100 messages.
- [ ] `src/opaque/translations/README.md` exists and lists the `lupdate` and `lrelease` commands.

## Left for another plan

- No translation is actually written here. This plan makes translation possible; supplying a language is a separate piece of work for a translator.
- Locale aware date and number formatting is not covered by any finding in the audit. If it becomes a requirement, `QLocale.toString` is the tool, and nothing in this plan blocks it.
