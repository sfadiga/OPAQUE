# Plan 01 — Test Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pytest and pytest-qt harness that `pyproject.toml` already declares but that the repository never created, so every later plan can prove its fix with a test.

**Architecture:** One `tests/` package with a `conftest.py` that forces the offscreen Qt platform and supplies two fixed palettes, one light and one dark. Widget code must never be tested against the developer's own desktop theme, because the result would then change from machine to machine.

**Tech Stack:** pytest 7+, pytest-qt 4+, PySide6.

Read **Rules for the executing agent** in `2026-09-07-opaque-ui-00-index.md` before you start.

---

## File Structure

| Path | Responsibility |
|---|---|
| Create `tests/__init__.py` | Marks the test package. Almost empty. |
| Create `tests/conftest.py` | Forces `QT_QPA_PLATFORM=offscreen`. Supplies the `light_palette_app` and `dark_palette_app` fixtures. |
| Create `tests/test_harness.py` | Smoke tests that prove the harness runs and the fixtures work. |
| Modify `pyproject.toml` | Adds the `[tool.pytest.ini_options]` section at the end of the file. |
| Modify `.gitignore` | Ignores `.pytest_cache/`. |

---

### Task 1: Install the declared dev dependencies

**Files:**
- None. This task only installs packages.

- [ ] **Step 1: Install the dev extra into the existing virtual environment**

Run:

```
venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Expected: the output ends with `Successfully installed ...` or `Requirement already satisfied` for both `pytest` and `pytest-qt`. There must be no line that starts with `ERROR:`.

- [ ] **Step 2: Confirm both packages import**

Run:

```
venv\Scripts\python.exe -c "import pytest, pytestqt; print(pytest.__version__, pytestqt.__file__)"
```

Expected: a version number of 7.0 or higher, then a path that ends in `pytestqt\__init__.py`.

If this fails with `ModuleNotFoundError`, stop and report it. Do not try a different install command.

---

### Task 2: Create the test package and the palette fixtures

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Test: `tests/test_harness.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_harness.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Smoke tests that prove the pytest-qt harness and the palette fixtures work."""

from PySide6.QtGui import QPalette


def test_light_fixture_gives_a_light_window_colour(light_palette_app):
    window = light_palette_app.palette().color(QPalette.ColorRole.Window)
    assert window.name() == "#f5f5f5"


def test_dark_fixture_gives_a_dark_window_colour(dark_palette_app):
    window = dark_palette_app.palette().color(QPalette.ColorRole.Window)
    assert window.name() == "#2b2b2b"


def test_fixture_restores_the_original_palette(qapp):
    original = qapp.palette().color(QPalette.ColorRole.Window).name()
    assert original not in ("#f5f5f5", "#2b2b2b")
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_harness.py -v
```

Expected: FAIL. The output contains `fixture 'light_palette_app' not found`.

- [ ] **Step 3: Create the package marker**

Create `tests/__init__.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Test package for the OPAQUE framework."""
```

- [ ] **Step 4: Write the conftest**

Create `tests/conftest.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""
Shared pytest fixtures for the OPAQUE framework tests.

The Qt platform is forced to "offscreen" so the suite runs the same way on a
developer machine and on a build agent with no display.

Widget tests must never read the developer's own desktop palette. The two
palette fixtures below give a fixed light palette and a fixed dark palette, so
a contrast assertion gives the same answer on every machine.
"""

import os

# This must run before any PySide6 module creates a QGuiApplication.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QColor, QPalette


def _build_palette(values: dict) -> QPalette:
    """Build a QPalette from a mapping of colour role to hex string."""
    palette = QPalette()
    for role, hex_value in values.items():
        palette.setColor(role, QColor(hex_value))
    return palette


_LIGHT_ROLES = {
    QPalette.ColorRole.Window: "#f5f5f5",
    QPalette.ColorRole.WindowText: "#1a1a1a",
    QPalette.ColorRole.Base: "#ffffff",
    QPalette.ColorRole.Text: "#1a1a1a",
    QPalette.ColorRole.Mid: "#b0b0b0",
    QPalette.ColorRole.Button: "#efefef",
    QPalette.ColorRole.ButtonText: "#1a1a1a",
    QPalette.ColorRole.Highlight: "#0b6ba8",
    QPalette.ColorRole.HighlightedText: "#ffffff",
}

_DARK_ROLES = {
    QPalette.ColorRole.Window: "#2b2b2b",
    QPalette.ColorRole.WindowText: "#e0e0e0",
    QPalette.ColorRole.Base: "#1e1e1e",
    QPalette.ColorRole.Text: "#e0e0e0",
    QPalette.ColorRole.Mid: "#5a5a5a",
    QPalette.ColorRole.Button: "#3a3a3a",
    QPalette.ColorRole.ButtonText: "#e0e0e0",
    QPalette.ColorRole.Highlight: "#a8c7e0",
    QPalette.ColorRole.HighlightedText: "#08324f",
}


@pytest.fixture
def light_palette_app(qapp):
    """Apply a fixed light palette for the duration of one test."""
    original = qapp.palette()
    qapp.setPalette(_build_palette(_LIGHT_ROLES))
    yield qapp
    qapp.setPalette(original)


@pytest.fixture
def dark_palette_app(qapp):
    """Apply a fixed dark palette for the duration of one test."""
    original = qapp.palette()
    qapp.setPalette(_build_palette(_DARK_ROLES))
    yield qapp
    qapp.setPalette(original)
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_harness.py -v
```

Expected: PASS. The summary line reads `3 passed`.

- [ ] **Step 6: Commit**

```bash
git add tests/__init__.py tests/conftest.py tests/test_harness.py
git commit -m "test: add pytest-qt harness with fixed light and dark palette fixtures"
```

---

### Task 3: Register the pytest configuration

**Files:**
- Modify: `pyproject.toml` (append one new section at the end of the file)
- Modify: `.gitignore` (append one line)

- [ ] **Step 1: Append the pytest section to `pyproject.toml`**

Add these lines at the very end of `pyproject.toml`. Do not change any existing line.

```toml

[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
addopts = "-ra --strict-markers"
```

`--strict-markers` turns a typo in a marker name into an error instead of a silent skip.

- [ ] **Step 2: Add the cache directory to `.gitignore`**

Append this single line to `.gitignore`:

```
.pytest_cache/
```

- [ ] **Step 3: Run the whole suite through the new configuration**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `3 passed`. The header block contains `configfile: pyproject.toml` and `testpaths: tests`.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .gitignore
git commit -m "test: register pytest configuration in pyproject.toml"
```

---

## Definition of done

- [ ] `venv\Scripts\python.exe -m pytest -q` prints `3 passed`.
- [ ] The pytest header names `pyproject.toml` as the config file.
- [ ] `tests/conftest.py` sets `QT_QPA_PLATFORM` before it imports any PySide6 module.
