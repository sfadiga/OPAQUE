# Theming With One Source of Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `QPalette` the only source of truth for colour in OPAQUE, so the token layer is always correct, and turn the three third-party theme packages into optional plug-in providers that the framework does not import.

**Architecture:** The token layer in `src/opaque/view/theme/` already reads `QApplication.palette()`. Two things break it today. First, `ThemeService` applies some themes as a style sheet only, which leaves the palette stale, so `is_dark_theme()` and the status colour tables answer for the previous theme (review 3.10). Second, `theme_service.py` imports `qt_themes`, `qdarkstyle` and `qt_material` at module scope while `pyproject.toml` declares only one of them optional, so a core module fails to import on a clean install (review 2.1). This plan adds built-in `Default`, `Light` and `Dark` palettes, replaces the closed `if/elif` chain in `apply_theme` with a `ThemeProvider` protocol, moves every third-party theme behind a lazily imported provider, and makes every provider set a palette whose polarity matches what it paints.

**Tech Stack:** Python 3.11, PySide6 (`QPalette`, `QColor`), pytest, pytest-qt, `importlib.util.find_spec`, `typing.Protocol`.

**Closes:** review 2.1, review 3.10, decision D4.

**Depends on:** Plan 01. The interpreter is `uv run python` from Plan 01 Task 6 on.

---


## Ordering constraint, found by the final review of Plan 01

`src/opaque/services/theme_service.py:18-21` imports all three theme
packages at module scope:

```python
import qt_themes
from qdarkstyle import load_stylesheet
from qdarkstyle.light.palette import LightPalette
from qt_material import apply_stylesheet, list_themes
```

`qt-themes` is already in the optional `themes` extra, so a plain
`pip install opaque-framework` produces a package that cannot be imported
at all. That was proved by building the wheel and installing it into a bare
environment: `import opaque` raises
`ModuleNotFoundError: No module named 'qt_themes'`. It is review item 2.1.

`qdarkstyle` and `qt_material` are safe today only because they are base
`dependencies`. **This plan moves both of them into the `themes` extra.**
So the order of work inside this plan is binding:

1. Make every theme import lazy first, behind the provider classes.
2. Move `qt-material` and `QDarkStyle` into the `themes` extra second.

Doing it the other way round reintroduces the same crash for two more
packages, and the release blocker gets worse rather than better.

Plan 01 added a `wheel` job to `.github/workflows/ci.yml` that builds the
wheel and imports it with no extras. It carries `continue-on-error: true`
because it fails today. **This plan removes that flag** once the imports are
lazy. That is the check that proves the work is done.

## Rules that apply to every task here

1. Read `docs/superpowers/plans/2026-09-08-techdebt-00-index.md` first. The rules there are binding.
2. Run every command from `C:\Users\sfadiga\sandro\opaque`.
3. The interpreter is `uv run python`.
4. Never write a literal colour in a widget. `src/opaque/view/theme/palettes.py`, created in Task 1, is the **only** new file in the repository that may hold hex colour values, because it builds the palette that every token reads.
5. The seven tests in `tests/theme/test_theme_service.py` must stay green after every task. Do not edit that file except where a task tells you to add to it.

---

## File structure

| File | Responsibility |
|---|---|
| Create: `src/opaque/view/theme/palettes.py` | Builds a complete `QPalette` for the built-in `Light` and `Dark` themes. The one place hex colours live. |
| Create: `tests/theme/test_palettes.py` | Proves both palettes fill every role the token layer reads, and that every text pair passes the WCAG minimum. |
| Create: `src/opaque/services/theme_provider.py` | The `ThemeProvider` protocol. Imported by the service and by the providers, so neither imports the other. |
| Create: `src/opaque/services/theme_providers.py` | The three optional providers plus `discover_providers()`. Every third-party import sits inside a method. |
| Create: `tests/services/__init__.py`, `tests/services/test_theme_providers.py` | Proves a provider with a missing package lists nothing, and that a style sheet provider leaves the palette polarity correct. |
| Modify: `src/opaque/services/theme_service.py` | Built-in themes, a provider registry, no third-party import at module scope. |
| Modify: `tests/theme/test_theme_service.py` | Adds the built-in theme and provider registry tests. Keeps the seven existing tests. |
| Modify: `src/opaque/view/application.py:154-174` | One repaint entry point that reaches every widget after a theme change. |
| Modify: `tests/test_application_shell.py` | Adds the shell repaint test. |
| Modify: `pyproject.toml:31-38` | `qt-material` and `QDarkStyle` move out of `dependencies` into the `themes` extra. |
| Modify: `CLAUDE.md` | The theme rule states the new truth. |

---

## Task 1: Built-in Light and Dark palettes

**Files:**
- Create: `src/opaque/view/theme/palettes.py`
- Modify: `src/opaque/view/theme/__init__.py`
- Test: `tests/theme/test_palettes.py`

The token layer reads exactly seven roles: `Window`, `WindowText`, `Base`, `Text`, `Mid`, `Highlight` and `HighlightedText` (`src/opaque/view/theme/tokens.py`). A palette that leaves any of them at the Qt default gives one token the wrong answer, so both builders fill all seven, plus the roles Qt itself needs to paint a widget.

- [ ] **Step 1: Write the failing test**

Create `tests/theme/test_palettes.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the built-in theme palettes."""

import pytest

from PySide6.QtGui import QPalette

from opaque.view.theme.contrast import (
    TEXT_CONTRAST_MINIMUM,
    contrast_ratio,
    relative_luminance,
)
from opaque.view.theme.palettes import build_dark_palette, build_light_palette

# Every role the token layer in tokens.py reads. A role left at the Qt
# default makes one token answer for a theme the user is not looking at.
TOKEN_ROLES = [
    QPalette.ColorRole.Window,
    QPalette.ColorRole.WindowText,
    QPalette.ColorRole.Base,
    QPalette.ColorRole.Text,
    QPalette.ColorRole.Mid,
    QPalette.ColorRole.Highlight,
    QPalette.ColorRole.HighlightedText,
]

# Each pair is a foreground and the background it is painted on. Every pair
# must pass the WCAG text minimum in both palettes.
TEXT_PAIRS = [
    (QPalette.ColorRole.Text, QPalette.ColorRole.Base),
    (QPalette.ColorRole.WindowText, QPalette.ColorRole.Window),
    (QPalette.ColorRole.ButtonText, QPalette.ColorRole.Button),
    (QPalette.ColorRole.HighlightedText, QPalette.ColorRole.Highlight),
    (QPalette.ColorRole.ToolTipText, QPalette.ColorRole.ToolTipBase),
]

BUILDERS = [build_light_palette, build_dark_palette]


@pytest.mark.parametrize("builder", BUILDERS)
@pytest.mark.parametrize("role", TOKEN_ROLES)
def test_the_palette_sets_every_role_the_tokens_read(builder, role):
    palette = builder()
    assert palette.isBrushSet(QPalette.ColorGroup.Active, role)


@pytest.mark.parametrize("builder", BUILDERS)
@pytest.mark.parametrize("foreground,background", TEXT_PAIRS)
def test_every_text_pair_passes_the_contrast_minimum(
        builder, foreground, background):
    palette = builder()
    ratio = contrast_ratio(
        palette.color(foreground).name(), palette.color(background).name())
    assert ratio >= TEXT_CONTRAST_MINIMUM


def test_the_light_palette_reads_as_a_light_theme():
    window = build_light_palette().color(QPalette.ColorRole.Window).name()
    assert relative_luminance(window) >= 0.18


def test_the_dark_palette_reads_as_a_dark_theme():
    window = build_dark_palette().color(QPalette.ColorRole.Window).name()
    assert relative_luminance(window) < 0.18


def test_a_builder_returns_a_new_palette_every_call():
    first = build_light_palette()
    second = build_light_palette()
    first.setColor(
        QPalette.ColorRole.Window, first.color(QPalette.ColorRole.Base))
    assert (first.color(QPalette.ColorRole.Window).name()
            != second.color(QPalette.ColorRole.Window).name())


@pytest.mark.parametrize("builder", BUILDERS)
def test_the_disabled_group_is_not_the_active_group(builder):
    palette = builder()
    active = palette.color(
        QPalette.ColorGroup.Active, QPalette.ColorRole.Text).name()
    disabled = palette.color(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text).name()
    assert active != disabled
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/theme/test_palettes.py -q
```

Expected: a collection error, `ModuleNotFoundError: No module named 'opaque.view.theme.palettes'`.

- [ ] **Step 3: Write the implementation**

Create `src/opaque/view/theme/palettes.py`:

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

The built-in theme palettes.

This module is the only place in the framework that holds a hex colour value.
Every other module asks the token layer, and the token layer reads the palette
that these builders produce. That keeps one source of truth for colour.

Both palettes were measured against the WCAG text minimum of 4.5:1. The
measured ratios are checked in tests/theme/test_palettes.py, which fails if a
colour is edited to a value that no longer passes.
"""

from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette


@dataclass(frozen=True)
class _PaletteSpec:
    """One complete colour set. Every field is a hex string."""

    window: str
    window_text: str
    base: str
    alternate_base: str
    text: str
    button: str
    button_text: str
    mid: str
    highlight: str
    highlighted_text: str
    tool_tip_base: str
    tool_tip_text: str
    placeholder_text: str
    bright_text: str
    link: str
    link_visited: str
    disabled_text: str


# Text on base 17.40:1. Window text on window 15.96:1. Highlight 5.70:1.
_LIGHT = _PaletteSpec(
    window="#f5f5f5",
    window_text="#1a1a1a",
    base="#ffffff",
    alternate_base="#ededed",
    text="#1a1a1a",
    button="#e2e2e2",
    button_text="#1a1a1a",
    mid="#b0b0b0",
    highlight="#0b6ba8",
    highlighted_text="#ffffff",
    tool_tip_base="#ffffe1",
    tool_tip_text="#1a1a1a",
    placeholder_text="#6b6b6b",
    bright_text="#b3261e",
    link="#0b57d0",
    link_visited="#7b1fa2",
    disabled_text="#9e9e9e",
)

# Text on base 14.11:1. Window text on window 12.93:1. Highlight 7.54:1.
# The highlight is a pale fill with dark text. A saturated fill on a dark
# surface glares, which is the rule the status tables in tokens.py follow.
_DARK = _PaletteSpec(
    window="#1f2124",
    window_text="#e6e6e6",
    base="#17191c",
    alternate_base="#24272b",
    text="#e6e6e6",
    button="#2b2f33",
    button_text="#e6e6e6",
    mid="#55595e",
    highlight="#a8c7e0",
    highlighted_text="#08324f",
    tool_tip_base="#2b2f33",
    tool_tip_text="#e6e6e6",
    placeholder_text="#9aa0a6",
    bright_text="#f2b8b5",
    link="#a8c7e0",
    link_visited="#d0bcff",
    disabled_text="#6b7075",
)


def _build(spec: _PaletteSpec) -> QPalette:
    """Turn one specification into a complete QPalette."""
    palette = QPalette()
    role = QPalette.ColorRole
    group = QPalette.ColorGroup

    palette.setColor(role.Window, QColor(spec.window))
    palette.setColor(role.WindowText, QColor(spec.window_text))
    palette.setColor(role.Base, QColor(spec.base))
    palette.setColor(role.AlternateBase, QColor(spec.alternate_base))
    palette.setColor(role.Text, QColor(spec.text))
    palette.setColor(role.Button, QColor(spec.button))
    palette.setColor(role.ButtonText, QColor(spec.button_text))
    palette.setColor(role.Mid, QColor(spec.mid))
    palette.setColor(role.Dark, QColor(spec.mid))
    palette.setColor(role.Midlight, QColor(spec.alternate_base))
    palette.setColor(role.Light, QColor(spec.base))
    palette.setColor(role.Shadow, QColor(spec.mid))
    palette.setColor(role.Highlight, QColor(spec.highlight))
    palette.setColor(role.HighlightedText, QColor(spec.highlighted_text))
    palette.setColor(role.ToolTipBase, QColor(spec.tool_tip_base))
    palette.setColor(role.ToolTipText, QColor(spec.tool_tip_text))
    palette.setColor(role.PlaceholderText, QColor(spec.placeholder_text))
    palette.setColor(role.BrightText, QColor(spec.bright_text))
    palette.setColor(role.Link, QColor(spec.link))
    palette.setColor(role.LinkVisited, QColor(spec.link_visited))

    # A disabled widget must stay legible, only clearly inactive.
    disabled = QColor(spec.disabled_text)
    palette.setColor(group.Disabled, role.Text, disabled)
    palette.setColor(group.Disabled, role.WindowText, disabled)
    palette.setColor(group.Disabled, role.ButtonText, disabled)
    palette.setColor(group.Disabled, role.HighlightedText, disabled)

    return palette


def build_light_palette() -> QPalette:
    """Return a new palette for the built-in Light theme."""
    return _build(_LIGHT)


def build_dark_palette() -> QPalette:
    """Return a new palette for the built-in Dark theme."""
    return _build(_DARK)
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/theme/test_palettes.py -q
```

Expected: `29 passed`. If the count differs but there are zero failures, continue.

- [ ] **Step 5: Export the builders from the theme package**

In `src/opaque/view/theme/__init__.py`, add this import directly after the `contrast` import block:

```python
from opaque.view.theme.palettes import build_dark_palette, build_light_palette
```

Then add two entries to `__all__`, directly after `"contrast_ratio",`:

```python
    "build_dark_palette",
    "build_light_palette",
```

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/theme/palettes.py src/opaque/view/theme/__init__.py tests/theme/test_palettes.py
git commit -m "feat(theme): add built-in light and dark palettes"
```

---

## Task 2: A provider protocol and a ThemeService with no third-party import

**Files:**
- Create: `src/opaque/services/theme_provider.py`
- Modify: `src/opaque/services/theme_service.py` (full replacement of lines 13-153)
- Test: `tests/theme/test_theme_service.py` (add to it, keep the seven tests it already has)

Today `apply_theme` is a closed `if/elif` chain that names three packages, and the module imports all three at line 18 to line 21. This task inverts that. The service knows three built-in themes and a list of providers. It knows nothing about any package.

- [ ] **Step 1: Write the failing test**

Replace the `theme_service` fixture at the top of `tests/theme/test_theme_service.py` (lines 1-14) with this block. The imports and the fixture grow; the seven tests below stay exactly as they are.

```python
# This Python file uses the following encoding: utf-8
"""Tests for the theme service signal, validation and provider registry."""

import pytest

from PySide6.QtGui import QColor, QPalette

from opaque.services.theme_provider import ThemeProvider
from opaque.services.theme_service import ThemeService
from opaque.view.theme.tokens import is_dark_theme


class _FakeProvider:
    """A provider that lists two names and records what it was asked to apply."""

    def __init__(self, succeed: bool = True) -> None:
        self.succeed = succeed
        self.applied: list = []

    def names(self):
        return ["Fake One", "Fake Two"]

    def apply(self, name, app):
        self.applied.append(name)
        return self.succeed


@pytest.fixture
def theme_service(qapp):
    # A theme applies to the whole QApplication, and the QApplication lives
    # for the whole test session. Save what was there and put it back, or one
    # test decides the colours another test measures.
    original_palette = qapp.palette()
    original_sheet = qapp.styleSheet()
    service = ThemeService(qapp)
    service.initialize()
    yield service
    service.cleanup()
    qapp.setPalette(original_palette)
    qapp.setStyleSheet(original_sheet)
```

Then add these tests at the end of the same file:

```python
def test_the_three_built_in_themes_are_always_available(theme_service):
    names = theme_service.get_available_themes()
    assert "Default" in names
    assert "Light" in names
    assert "Dark" in names


def test_the_dark_theme_makes_the_token_layer_report_dark(theme_service):
    assert theme_service.apply_theme("Dark") is True
    assert is_dark_theme() is True


def test_the_light_theme_makes_the_token_layer_report_light(theme_service):
    assert theme_service.apply_theme("Light") is True
    assert is_dark_theme() is False


def test_a_built_in_theme_clears_a_style_sheet_left_by_another_theme(
        theme_service, qapp):
    qapp.setStyleSheet("QWidget { color: #ff00ff; }")
    theme_service.apply_theme("Light")
    assert qapp.styleSheet() == ""


def test_the_default_theme_restores_the_palette_from_construction(qapp):
    original_palette = qapp.palette()
    original_sheet = qapp.styleSheet()
    marker = QPalette(original_palette)
    marker.setColor(QPalette.ColorRole.Window, QColor("#123456"))
    qapp.setPalette(marker)

    service = ThemeService(qapp)
    service.initialize()
    try:
        service.apply_theme("Dark")
        assert qapp.palette().color(
            QPalette.ColorRole.Window).name() != "#123456"

        service.apply_theme("Default")
        assert qapp.palette().color(
            QPalette.ColorRole.Window).name() == "#123456"
    finally:
        service.cleanup()
        qapp.setPalette(original_palette)
        qapp.setStyleSheet(original_sheet)


def test_a_registered_provider_adds_its_names(theme_service):
    theme_service.register_provider(_FakeProvider())
    assert theme_service.is_valid_theme("Fake One") is True
    assert "Fake Two" in theme_service.get_available_themes()


def test_a_provider_name_is_applied_by_that_provider(theme_service):
    provider = _FakeProvider()
    theme_service.register_provider(provider)
    assert theme_service.apply_theme("Fake One") is True
    assert provider.applied == ["Fake One"]
    assert theme_service.current_theme() == "Fake One"


def test_a_provider_that_fails_leaves_the_current_theme_alone(theme_service):
    theme_service.apply_theme("Light")
    theme_service.register_provider(_FakeProvider(succeed=False))
    assert theme_service.apply_theme("Fake One") is False
    assert theme_service.current_theme() == "Light"


def test_a_provider_that_fails_does_not_emit_theme_changed(
        theme_service, qtbot):
    theme_service.register_provider(_FakeProvider(succeed=False))
    with qtbot.assertNotEmitted(theme_service.theme_changed):
        theme_service.apply_theme("Fake One")


def test_a_plain_object_with_the_two_methods_is_a_theme_provider():
    assert isinstance(_FakeProvider(), ThemeProvider)


def test_the_service_module_names_no_third_party_theme_package():
    import inspect

    from opaque.services import theme_service as module

    source = inspect.getsource(module)
    for package in ("qt_themes", "qdarkstyle", "qt_material"):
        assert package not in source
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/theme/test_theme_service.py -q
```

Expected: a collection error, `ModuleNotFoundError: No module named 'opaque.services.theme_provider'`.

- [ ] **Step 3: Write the protocol**

Create `src/opaque/services/theme_provider.py`:

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

The contract a theme provider must satisfy.

This module holds only the protocol. ThemeService imports it, and every
provider imports it, so the service never imports a provider and a provider
never imports the service.
"""

from typing import List, Protocol, runtime_checkable

from PySide6.QtWidgets import QApplication


@runtime_checkable
class ThemeProvider(Protocol):
    """
    One source of themes that the application can offer to the user.

    Two rules bind every implementation.

    First, `names()` must be cheap and must never raise. A provider backed by
    a package that is not installed returns an empty list. It does not raise
    ImportError, because the settings dialog calls this to fill a combo box.

    Second, `apply()` must leave the QApplication palette agreeing with what
    it painted. The token layer in opaque.view.theme reads the palette to
    decide whether the theme is dark, and every status colour follows that
    answer. A provider that installs a dark style sheet and leaves a light
    palette gives every token the wrong answer.
    """

    def names(self) -> List[str]:
        """Return the theme names this provider can apply. Empty if absent."""
        ...

    def apply(self, name: str, app: QApplication) -> bool:
        """
        Apply one of this provider's own names.

        Returns:
            True when the theme was applied. False when the name is not one
            this provider offers, or the package refused to apply it. Return
            False instead of raising.
        """
        ...
```

- [ ] **Step 4: Replace the service**

Replace everything in `src/opaque/services/theme_service.py` from line 13 to the end of the file with this. Keep lines 1 to 12, the encoding line and the licence docstring, exactly as they are.

```python
from typing import List, Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from opaque.services.service import BaseService
from opaque.services.theme_provider import ThemeProvider
from opaque.view.theme.palettes import build_dark_palette, build_light_palette


class ThemeService(BaseService):
    """
    Offers the themes the application can apply, and applies one.

    The service owns three built-in themes and nothing else. Every other
    theme arrives through a ThemeProvider, so no third-party theme package is
    imported here and none is a hard dependency of the framework.

    A built-in theme is a QPalette and nothing more. That matters: the token
    layer in opaque.view.theme reads QApplication.palette() for every colour,
    so a theme that changes the palette changes every widget at once.
    """

    # Emitted with the theme name after a theme is applied. A widget that
    # paints its own colours must connect to this and repaint.
    theme_changed = Signal(str)

    # The theme that is always available. Any application default must be a
    # name that get_available_themes() returns.
    DEFAULT_THEME: str = "Default"
    LIGHT_THEME: str = "Light"
    DARK_THEME: str = "Dark"

    # Built in, always offered, needs no package.
    BUILT_IN_THEMES: tuple = (DEFAULT_THEME, LIGHT_THEME, DARK_THEME)

    def __init__(self, app: QApplication) -> None:
        """Initializes the theme manager.

        Args:
            app (QApplication): The main application instance.
        """
        super().__init__("themes")

        self._app: QApplication = app

        # The palette Qt gave us before any theme was applied. "Default"
        # means "what the operating system chose", so it must be captured
        # here, before the first apply_theme call overwrites it.
        self._default_palette: QPalette = QPalette(app.palette())

        self._providers: List[ThemeProvider] = []
        self._available_themes: List[str] = list(self.BUILT_IN_THEMES)

        # The name of the theme applied most recently.
        self._current_theme: str = self.DEFAULT_THEME

    def initialize(self) -> None:
        self._rebuild_available_themes()
        return super().initialize()

    def cleanup(self) -> None:
        self._providers.clear()
        self._available_themes = list(self.BUILT_IN_THEMES)
        return super().cleanup()

    def register_provider(self, provider: ThemeProvider) -> None:
        """
        Add a source of extra themes.

        Call this before the settings dialog is built. The names the provider
        reports join the list immediately.
        """
        self._providers.append(provider)
        self._rebuild_available_themes()

    def _rebuild_available_themes(self) -> None:
        """Recompute the offered names from the built-ins and the providers."""
        names: List[str] = list(self.BUILT_IN_THEMES)
        for provider in self._providers:
            for name in provider.names():
                if name not in names:
                    names.append(name)
        self._available_themes = names

    def get_available_themes(self) -> List[str]:
        """Returns a list of all available theme names."""
        return list(self._available_themes)

    def current_theme(self) -> str:
        """Return the name of the theme applied most recently."""
        return self._current_theme

    def is_valid_theme(self, theme_name: str) -> bool:
        """
        Return True when the name is one this service can apply.

        Call this before you store a theme name in a settings model. A name
        that is not on the list is applied silently as nothing, which leaves
        the settings dialog reporting a theme the user is not looking at.
        """
        return theme_name in self._available_themes

    def apply_theme(self, theme_name: str) -> bool:
        """
        Apply a theme to the application by name.

        Returns:
            True when the theme was applied. False when the name is unknown
            or the provider refused it, in which case the current theme is
            left alone.
        """
        if not self.is_valid_theme(theme_name):
            return False

        if theme_name in self.BUILT_IN_THEMES:
            applied = self._apply_built_in(theme_name)
        else:
            applied = self._apply_from_provider(theme_name)

        if not applied:
            return False

        self._current_theme = theme_name
        self.theme_changed.emit(theme_name)
        return True

    def _apply_built_in(self, theme_name: str) -> bool:
        """Apply one of the three built-in themes."""
        # Clear the style sheet first. A style sheet left by a previous theme
        # paints over the palette, so the palette would stop being the truth.
        self._app.setStyleSheet("")

        if theme_name == self.DEFAULT_THEME:
            self._app.setPalette(QPalette(self._default_palette))
        elif theme_name == self.LIGHT_THEME:
            self._app.setPalette(build_light_palette())
        else:
            self._app.setPalette(build_dark_palette())

        return True

    def _provider_for(self, theme_name: str) -> Optional[ThemeProvider]:
        """Return the first provider that offers this name, or None."""
        for provider in self._providers:
            if theme_name in provider.names():
                return provider
        return None

    def _apply_from_provider(self, theme_name: str) -> bool:
        """Hand the name to the provider that offers it."""
        provider = self._provider_for(theme_name)
        if provider is None:
            return False
        return provider.apply(theme_name, self._app)
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
uv run python -m pytest tests/theme/test_theme_service.py -q
```

Expected: `18 passed`. The seven original tests are among them.

- [ ] **Step 6: Prove no caller used the attribute that is now private**

The old service exposed a public `available_themes` list attribute. It is now `_available_themes`.

```bash
grep -rn "available_themes" --include=*.py src examples tests | grep -v "_available_themes" | grep -v "get_available_themes"
```

Expected: no output. If a line appears, change that line to call `get_available_themes()` and note it in your report.

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. `tests/models/test_app_model.py` and `tests/test_application_shell.py` both touch the theme service; both must still pass.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/services/theme_provider.py src/opaque/services/theme_service.py tests/theme/test_theme_service.py
git commit -m "refactor(theme): apply built-in palettes and take themes from providers"
```

---

## Task 3: The three optional providers

**Files:**
- Create: `src/opaque/services/theme_providers.py`
- Create: `tests/services/__init__.py`
- Test: `tests/services/test_theme_providers.py`

Each provider wraps one package. The package is imported inside a method, never at module scope, so `import opaque` works on a machine that has none of them. Each provider also sets a palette whose polarity matches the style sheet it installs. That is the fix for review 3.10: a dark style sheet with a light palette made `is_dark_theme()` and every status colour answer for the wrong theme.

- [ ] **Step 1: Write the failing test**

Create `tests/services/__init__.py` as an empty file:

```bash
uv run python -c "open('tests/services/__init__.py', 'w').close()"
```

Create `tests/services/test_theme_providers.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the optional theme providers."""

import pytest

from opaque.services.theme_provider import ThemeProvider
from opaque.services.theme_providers import (
    QDarkStyleProvider,
    QtMaterialProvider,
    QtThemesProvider,
    discover_providers,
)
from opaque.view.theme.tokens import is_dark_theme

PROVIDER_CLASSES = [QtThemesProvider, QtMaterialProvider, QDarkStyleProvider]


@pytest.fixture
def clean_app(qapp):
    """Give the test the application, and undo whatever it applied."""
    original_palette = qapp.palette()
    original_sheet = qapp.styleSheet()
    yield qapp
    qapp.setStyleSheet(original_sheet)
    qapp.setPalette(original_palette)


@pytest.mark.parametrize("provider_class", PROVIDER_CLASSES)
def test_every_provider_satisfies_the_protocol(provider_class):
    assert isinstance(provider_class(), ThemeProvider)


@pytest.mark.parametrize("provider_class", PROVIDER_CLASSES)
def test_a_provider_with_a_missing_package_lists_nothing(
        provider_class, monkeypatch):
    monkeypatch.setattr(
        "opaque.services.theme_providers._package_present", lambda name: False)
    assert provider_class().names() == []


@pytest.mark.parametrize("provider_class", PROVIDER_CLASSES)
def test_a_provider_with_a_missing_package_applies_nothing(
        provider_class, monkeypatch, clean_app):
    monkeypatch.setattr(
        "opaque.services.theme_providers._package_present", lambda name: False)
    assert provider_class().apply("anything", clean_app) is False


@pytest.mark.parametrize("provider_class", PROVIDER_CLASSES)
def test_a_provider_refuses_a_name_it_does_not_offer(
        provider_class, clean_app):
    assert provider_class().apply("No Such Theme", clean_app) is False


@pytest.mark.parametrize("provider_class", PROVIDER_CLASSES)
def test_every_name_a_provider_offers_can_be_applied(
        provider_class, clean_app):
    provider = provider_class()
    names = provider.names()
    if not names:
        pytest.skip("the package behind this provider is not installed")
    for name in names:
        assert provider.apply(name, clean_app) is True


def test_discover_providers_returns_only_providers_that_offer_names():
    for provider in discover_providers():
        assert provider.names() != []


def test_a_dark_style_sheet_leaves_the_token_layer_reporting_dark(clean_app):
    provider = QDarkStyleProvider()
    if "QDarkStyle" not in provider.names():
        pytest.skip("QDarkStyle is not installed")
    assert provider.apply("QDarkStyle", clean_app) is True
    assert is_dark_theme() is True


def test_a_light_style_sheet_leaves_the_token_layer_reporting_light(clean_app):
    provider = QDarkStyleProvider()
    if "QLightStyle" not in provider.names():
        pytest.skip("QDarkStyle is not installed")
    assert provider.apply("QLightStyle", clean_app) is True
    assert is_dark_theme() is False


def test_a_dark_material_theme_leaves_the_token_layer_reporting_dark(
        clean_app):
    provider = QtMaterialProvider()
    dark_names = [name for name in provider.names() if name.startswith("dark")]
    if not dark_names:
        pytest.skip("qt-material is not installed")
    assert provider.apply(dark_names[0], clean_app) is True
    assert is_dark_theme() is True


def test_a_light_material_theme_leaves_the_token_layer_reporting_light(
        clean_app):
    provider = QtMaterialProvider()
    light_names = [
        name for name in provider.names() if name.startswith("light")]
    if not light_names:
        pytest.skip("qt-material is not installed")
    assert provider.apply(light_names[0], clean_app) is True
    assert is_dark_theme() is False


def test_the_qt_themes_names_keep_the_historic_prefix(clean_app):
    names = QtThemesProvider().names()
    if not names:
        pytest.skip("qt-themes is not installed")
    for name in names:
        assert name.startswith("qt-themes: ")
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/services/test_theme_providers.py -q
```

Expected: a collection error, `ModuleNotFoundError: No module named 'opaque.services.theme_providers'`.

- [ ] **Step 3: Write the implementation**

Create `src/opaque/services/theme_providers.py`:

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

Theme providers for the optional third-party packages.

Every import of a theme package happens inside a method. The framework must
import on a machine that has none of them installed, so nothing here is
imported at module scope and no name below is a hard dependency.

Every provider sets a palette that matches the polarity of what it painted.
A style sheet changes what the user sees but not what QApplication.palette()
reports, and the token layer in opaque.view.theme reads only the palette. A
dark style sheet with a light palette makes every status colour wrong.
"""

import importlib.util
import logging
from typing import List

from PySide6.QtWidgets import QApplication

from opaque.services.theme_provider import ThemeProvider
from opaque.view.theme.palettes import build_dark_palette, build_light_palette

logger = logging.getLogger(__name__)


def _package_present(name: str) -> bool:
    """Return True when a package can be imported, without importing it."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _set_polarity(app: QApplication, dark: bool) -> None:
    """Give the token layer a palette that agrees with the style sheet."""
    app.setPalette(build_dark_palette() if dark else build_light_palette())


class QtThemesProvider:
    """The themes from the qt-themes package. It sets a real palette itself."""

    PACKAGE = "qt_themes"
    PREFIX = "qt-themes: "

    def names(self) -> List[str]:
        if not _package_present(self.PACKAGE):
            return []
        try:
            import qt_themes  # pylint: disable=import-outside-toplevel

            # The historic display format is kept, because a settings file
            # written by an earlier version holds these exact strings.
            return [
                self.PREFIX + key.replace("_", " ").title()
                for key in qt_themes.get_themes()
            ]
        except (ImportError, AttributeError):
            return []

    def apply(self, name: str, app: QApplication) -> bool:
        if name not in self.names():
            return False
        key = name[len(self.PREFIX):].replace(" ", "_").lower()
        try:
            import qt_themes  # pylint: disable=import-outside-toplevel

            # qt-themes installs a full palette, so clear any style sheet a
            # previous theme left behind and let the palette be the truth.
            app.setStyleSheet("")
            qt_themes.set_theme(key)
            return True
        except Exception:  # pylint: disable=broad-except
            logger.warning("qt-themes refused the theme %s", name)
            return False


class QtMaterialProvider:
    """The themes from the qt-material package. It installs a style sheet."""

    PACKAGE = "qt_material"

    def names(self) -> List[str]:
        if not _package_present(self.PACKAGE):
            return []
        try:
            from qt_material import (  # pylint: disable=import-outside-toplevel
                list_themes,
            )

            return [name.replace(".xml", "") for name in list_themes()]
        except (ImportError, AttributeError):
            return []

    def apply(self, name: str, app: QApplication) -> bool:
        if name not in self.names():
            return False
        try:
            from qt_material import (  # pylint: disable=import-outside-toplevel
                apply_stylesheet,
            )

            # A qt-material name starts with dark_ or light_, which is the
            # only statement of polarity the package makes.
            light = name.startswith("light")
            apply_stylesheet(
                app, theme=f"{name}.xml", invert_secondary=light)
            _set_polarity(app, dark=not light)
            return True
        except Exception:  # pylint: disable=broad-except
            logger.warning("qt-material refused the theme %s", name)
            return False


class QDarkStyleProvider:
    """The two QDarkStyleSheet themes. Both install a style sheet."""

    PACKAGE = "qdarkstyle"
    DARK_NAME = "QDarkStyle"
    LIGHT_NAME = "QLightStyle"

    def names(self) -> List[str]:
        if not _package_present(self.PACKAGE):
            return []
        return [self.DARK_NAME, self.LIGHT_NAME]

    def apply(self, name: str, app: QApplication) -> bool:
        if name not in self.names():
            return False
        try:
            # pylint: disable=import-outside-toplevel
            from qdarkstyle import load_stylesheet
            from qdarkstyle.light.palette import LightPalette

            if name == self.DARK_NAME:
                app.setStyleSheet(load_stylesheet())
                _set_polarity(app, dark=True)
            else:
                app.setStyleSheet(load_stylesheet(palette=LightPalette))
                _set_polarity(app, dark=False)
            return True
        except Exception:  # pylint: disable=broad-except
            logger.warning("QDarkStyle refused the theme %s", name)
            return False


def discover_providers() -> List[ThemeProvider]:
    """
    Return one instance of every provider whose package is installed.

    A provider whose package is absent reports no names, so it is dropped
    here instead of showing an empty group in the settings dialog.
    """
    candidates: List[ThemeProvider] = [
        QtThemesProvider(),
        QtMaterialProvider(),
        QDarkStyleProvider(),
    ]
    return [provider for provider in candidates if provider.names()]
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/services/test_theme_providers.py -q
```

Expected: every test passes or skips. Zero failures. On this machine `qt-material` and `QDarkStyle` are installed, so the polarity tests run and pass. `qt-themes` may be absent, in which case two tests skip.

- [ ] **Step 5: Prove the framework imports with no theme package**

This is the check that review 2.1 asked for. It runs the import with the three packages hidden from the import system.

```bash
uv run python -c "
import sys
for name in ('qt_themes', 'qdarkstyle', 'qt_material'):
    sys.modules[name] = None
import importlib.util
real = importlib.util.find_spec
importlib.util.find_spec = lambda n, *a, **k: None if n in ('qt_themes', 'qdarkstyle', 'qt_material') else real(n, *a, **k)
from opaque.services.theme_service import ThemeService
from opaque.services.theme_providers import discover_providers
print('providers:', discover_providers())
print('import ok')
"
```

Expected output:

```
providers: []
import ok
```

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/services/theme_providers.py tests/services/__init__.py tests/services/test_theme_providers.py
git commit -m "feat(theme): wrap the optional theme packages in lazy providers"
```

---

## Task 4: The service discovers the installed providers

**Files:**
- Modify: `src/opaque/services/theme_service.py` (the import block and `initialize`)
- Test: `tests/theme/test_theme_service.py` (add to it)

Task 3 built the providers. Nothing calls them yet, so the application still offers only the three built-in themes. This task connects them, and proves the whole seam: a dark theme from a provider must make the status colour tables in `tokens.py` return the dark table. That is the end of review 3.10.

- [ ] **Step 1: Write the failing test**

Extend the import block at the top of `tests/theme/test_theme_service.py`. After the `from opaque.services.theme_service import ThemeService` line, add:

```python
from opaque.services.theme_providers import discover_providers
from opaque.view.theme.tokens import StatusRole, status_colors
```

Then add these tests at the end of the file:

```python
def test_initialize_offers_every_installed_provider_theme(theme_service):
    expected = []
    for provider in discover_providers():
        expected.extend(provider.names())
    if not expected:
        pytest.skip("no optional theme package is installed")

    offered = theme_service.get_available_themes()
    for name in expected:
        assert name in offered


def test_the_built_in_themes_come_first_in_the_list(theme_service):
    offered = theme_service.get_available_themes()
    assert offered[:3] == ["Default", "Light", "Dark"]


def test_a_dark_provider_theme_gives_the_dark_status_colours(theme_service):
    dark_names = [
        name for name in theme_service.get_available_themes()
        if name.startswith("dark")
    ]
    if not dark_names:
        pytest.skip("qt-material is not installed")

    assert theme_service.apply_theme(dark_names[0]) is True
    assert is_dark_theme() is True
    # The dark table uses a pale error fill, the light table a saturated one.
    # Before this plan the service installed a dark style sheet and left the
    # light palette, so the light table was used on a dark window.
    assert status_colors(StatusRole.ERROR).background == "#f2b8b5"


def test_the_built_in_dark_theme_gives_the_dark_status_colours(theme_service):
    assert theme_service.apply_theme("Dark") is True
    assert status_colors(StatusRole.ERROR).background == "#f2b8b5"


def test_the_built_in_light_theme_gives_the_light_status_colours(
        theme_service):
    assert theme_service.apply_theme("Light") is True
    assert status_colors(StatusRole.ERROR).background == "#b3261e"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/theme/test_theme_service.py -q -k "offers_every_installed_provider or dark_provider_theme"
```

Expected: `test_initialize_offers_every_installed_provider_theme` FAILS with an `AssertionError`, because `initialize()` registers no provider. `test_a_dark_provider_theme_gives_the_dark_status_colours` SKIPS, because the material names are not offered yet.

- [ ] **Step 3: Write the implementation**

In `src/opaque/services/theme_service.py`, add this import directly after the `from opaque.services.theme_provider import ThemeProvider` line:

```python
from opaque.services.theme_providers import discover_providers
```

Then replace the `initialize` method:

```python
    def initialize(self) -> None:
        # Ask once, at start. A package cannot appear while the process runs,
        # and the settings dialog needs a stable list.
        for provider in discover_providers():
            self._providers.append(provider)
        self._rebuild_available_themes()
        return super().initialize()
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/theme/test_theme_service.py -q
```

Expected: every test passes or skips. Zero failures.

- [ ] **Step 5: Confirm the module still names no package**

```bash
uv run python -m pytest tests/theme/test_theme_service.py -q -k "names_no_third_party"
```

Expected: `1 passed`. `theme_providers` is named, but no theme package is.

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/services/theme_service.py tests/theme/test_theme_service.py
git commit -m "feat(theme): discover the installed theme providers at start"
```

---

## Task 5: The theme packages become optional

**Files:**
- Modify: `pyproject.toml:31-38`
- Modify: `CLAUDE.md` (the **Theme rule** bullet in `## Architecture`)
- Test: `tests/test_packaging.py` (add to the file Plan 01 Task 1 created)

The review found `qt-material` and `QDarkStyle` in `dependencies` while `qt-themes` sat in an extra named `themes`, and all three imported at module scope. Task 2 and Task 3 removed the imports. This task makes the declaration match: none of the three is required.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_packaging.py`:

```python
def test_no_theme_package_is_a_hard_dependency(project_metadata):
    required = " ".join(project_metadata["project"]["dependencies"]).lower()
    for package in ("qt-material", "qdarkstyle", "qt-themes"):
        assert package not in required


def test_every_theme_package_is_in_the_themes_extra(project_metadata):
    extras = project_metadata["project"]["optional-dependencies"]
    themes = " ".join(extras["themes"]).lower()
    for package in ("qt-material", "qdarkstyle", "qt-themes"):
        assert package in themes


def test_pyside6_is_still_a_hard_dependency(project_metadata):
    required = " ".join(project_metadata["project"]["dependencies"]).lower()
    assert "pyside6" in required
```

`project_metadata` is the fixture Plan 01 Task 1 added to that file. It parses `pyproject.toml` with `tomllib`.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_packaging.py -q -k "theme"
```

Expected: `test_no_theme_package_is_a_hard_dependency` FAILS. `test_every_theme_package_is_in_the_themes_extra` FAILS.

- [ ] **Step 3: Write the implementation**

In `pyproject.toml`, replace the `dependencies` list and the `themes` extra. Before:

```toml
dependencies = [
    "PySide6>=6.0.0",
    "qt-material>=2.14",
    "QDarkStyle>=3.2.0",
]

[project.optional-dependencies]
themes = [
    "qt-themes>=1.0.0",
]
```

After:

```toml
dependencies = [
    "PySide6>=6.0.0",
]

[project.optional-dependencies]
# Extra theme sources. The framework offers Default, Light and Dark with no
# extra package. Install this extra to add the qt-themes, qt-material and
# QDarkStyleSheet themes. See src/opaque/services/theme_providers.py.
themes = [
    "qt-themes>=1.0.0",
    "qt-material>=2.14",
    "QDarkStyle>=3.2.0",
]
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_packaging.py -q
```

Expected: every test passes.

- [ ] **Step 5: Refresh the lock file and the environment**

```bash
uv lock
uv sync --all-extras
```

Expected: `uv lock` reports the resolution. `uv sync --all-extras` keeps the three theme packages installed, because `--all-extras` includes `themes`. The suite therefore still exercises the provider paths.

- [ ] **Step 6: Prove a build without the extra has no theme package**

```bash
uv run --no-project --with . python -c "
import importlib.util
for name in ('qt_themes', 'qdarkstyle', 'qt_material'):
    print(name, importlib.util.find_spec(name) is not None)
import opaque
print('opaque', opaque.__version__)
"
```

Expected: three lines reading `False`, then the version line. This is the clean install that used to raise `ModuleNotFoundError`.

If `uv run --no-project --with .` fails on this machine for a reason unrelated to themes, record the exact error in your report and continue. The check in Task 3 Step 5 already covers the same ground from inside the project environment.

- [ ] **Step 7: Update CLAUDE.md**

In `## Architecture`, replace the whole **Theme rule** bullet with:

```markdown
- **Theme rule**: a widget must never write a literal colour or point size. Ask `view/theme/tokens.py` for colours and `type_scale.py` for fonts. Tokens read `QApplication.palette()`, and `QPalette` is the single source of truth. `ThemeService` offers three built-in themes (`Default`, `Light`, `Dark`) that are palettes and nothing else; `view/theme/palettes.py` is the only module in the framework that holds a hex colour. Every other theme arrives through a `ThemeProvider` (`services/theme_provider.py`, implementations in `services/theme_providers.py`), which imports its package lazily and must set a palette that matches the polarity of the style sheet it installs. No theme package is a hard dependency; install the `themes` extra to get them.
```

- [ ] **Step 8: Run the whole suite and the checks**

```bash
uv run python -m pytest tests -q
uv run python -m pylint src/opaque/services/theme_service.py src/opaque/services/theme_provider.py src/opaque/services/theme_providers.py src/opaque/view/theme/palettes.py
```

Expected: the suite reports zero failures. pylint reports no error and no warning for the four files. If pylint reports `too-few-public-methods` on `_PaletteSpec`, add `# pylint: disable=too-few-public-methods` on the class line and run it again.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock CLAUDE.md tests/test_packaging.py
git commit -m "fix(packaging): make every theme package optional"
```

---

## Task 6: One repaint entry point for the whole shell

**Files:**
- Modify: `src/opaque/view/application.py:154-174` (`_wire_shell_signals`, and one new method after it)
- Modify: `CLAUDE.md` (one new bullet in `## Architecture`)
- Test: `tests/test_application_shell.py` (add to it)

A token is a string, not a live binding. A widget that asks for `surface()` in its constructor keeps that colour for ever. Today only the toolbar and the console are told about a theme change, and the console is told by its own presenter. This task gives the shell one walk that reaches every widget, so a new widget needs no wiring of its own.

- [ ] **Step 1: Write the failing test**

Check the `PySide6.QtWidgets` import line of `tests/test_application_shell.py`. If `QWidget` is not on it, add it.

Add these tests at the end of `tests/test_application_shell.py`:

```python
def test_a_theme_change_reaches_a_widget_that_paints_its_own_colours(
        app_window):
    calls = []

    class _PaintingWidget(QWidget):
        def apply_theme(self):
            calls.append(True)

    _PaintingWidget(app_window)

    app_window.theme_service.theme_changed.emit("Default")

    assert calls == [True]


def test_a_widget_without_apply_theme_does_not_break_the_walk(app_window):
    plain = QWidget(app_window)

    app_window.theme_service.theme_changed.emit("Default")

    # Nothing to assert on the widget itself. The test passes when the walk
    # completes, which proves the walk does not require the method.
    assert plain.parent() is app_window
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_application_shell.py -q -k "paints_its_own_colours"
```

Expected: FAIL with `assert [] == [True]`.

- [ ] **Step 3: Write the implementation**

In `src/opaque/view/application.py`, replace the first connection inside `_wire_shell_signals`. Before:

```python
        self.theme_service.theme_changed.connect(
            lambda _name: self.toolbar.update_theme())
```

After:

```python
        self.theme_service.theme_changed.connect(
            lambda _name: self._repaint_after_theme_change())
```

Then add this method directly after `_wire_shell_signals`:

```python
    def _repaint_after_theme_change(self) -> None:
        """
        Give every widget in the shell a chance to repaint after a theme change.

        A token is a string, not a live binding, so a widget that reads
        surface() in its constructor keeps that colour for ever. Such a widget
        declares apply_theme() with no arguments, and this walk calls it. The
        walk also repolishes the tree, because Qt does not always repolish a
        widget that was created before a style sheet was installed.

        One walk in the shell means a new widget needs no signal wiring of its
        own, which is what stops the next widget from being left behind.
        """
        self.toolbar.update_theme()

        style = self.style()
        for widget in self.findChildren(QWidget):
            repaint = getattr(widget, "apply_theme", None)
            if callable(repaint):
                repaint()
            style.unpolish(widget)
            style.polish(widget)

        style.unpolish(self)
        style.polish(self)
        self.update()
```

`QWidget` is already on the `PySide6.QtWidgets` import line at `src/opaque/view/application.py:16`. Do not add it again.

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_application_shell.py -q
```

Expected: every test passes, including the older `test_a_theme_change_reaches_the_toolbar`, which monkeypatches `toolbar.update_theme` and still sees exactly one call.

- [ ] **Step 5: Update CLAUDE.md**

In `## Architecture`, add this bullet directly after the **Theme rule** bullet:

```markdown
- **Theme repaint**: a widget that caches a token value must declare `apply_theme()` with no arguments. `BaseApplication._repaint_after_theme_change()` walks the widget tree after every theme change and calls it. Do not connect `theme_changed` in a presenter; the shell already does the walk.
```

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 7: Look at the running application**

```bash
uv run python examples/basic_example/main.py
```

In the application, open Settings, change the theme to `Dark`, and accept. Expected: the whole window changes, including the console panel if the example opens one. Change it to `Light`. Expected: the window changes back, and no panel keeps dark colours. Close the application.

Record what you saw in your report. If a widget keeps the old colours, name that widget; it needs an `apply_theme()` method, and adding it is in scope for this step.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/application.py tests/test_application_shell.py CLAUDE.md
git commit -m "fix(theme): repaint the whole shell after a theme change"
```

---

## Verification of the whole plan

Run this after Task 6. It is the evidence that review 2.1 and review 3.10 are closed.

- [ ] **Check 1: the framework imports with no theme package**

```bash
uv run python -c "
import sys, importlib.util
real = importlib.util.find_spec
importlib.util.find_spec = lambda n, *a, **k: None if n in ('qt_themes', 'qdarkstyle', 'qt_material') else real(n, *a, **k)
from opaque.services.theme_providers import discover_providers
print('providers with no package:', discover_providers())
"
```

Expected: `providers with no package: []`.

- [ ] **Check 2: no theme package is required**

```bash
uv run python -c "
import tomllib
data = tomllib.load(open('pyproject.toml', 'rb'))
print('required:', data['project']['dependencies'])
print('themes extra:', data['project']['optional-dependencies']['themes'])
"
```

Expected: `required: ['PySide6>=6.0.0']`, and the three theme packages in the extra.

- [ ] **Check 3: the palette is the only source of truth**

```bash
grep -rn "#[0-9a-fA-F]\{6\}" --include=*.py src/opaque | grep -v "src/opaque/view/theme/palettes.py" | grep -v "src/opaque/view/theme/tokens.py"
```

Expected: no output. `palettes.py` holds the built-in palettes and `tokens.py` holds the two status tables; both are documented exceptions. Any other file printing here is a widget writing a literal colour, which breaks the theme rule.

- [ ] **Check 4: the whole suite and the type check**

```bash
uv run python -m pytest tests -q
uv run python -m mypy src/opaque
```

Expected: the suite reports zero failures. mypy reports no error in `theme_service.py`, `theme_provider.py`, `theme_providers.py` or `palettes.py`. mypy may still report errors elsewhere; those belong to Plan 10 Task 8. Report exactly which files any remaining error is in.

---

## What this plan does not do

These are known, and each has an owner. Do not fix them here.

| Left open | Owner |
|---|---|
| `console_presenter.py:101` asks the locator for `"theme"`, which is not a registered name, so the console never gets its own theme signal. The walk added in Task 6 now repaints the console anyway, so the duplicate connection in the presenter can be deleted. | Plan 06 Task 1 |
| `ApplicationPresenter` fills `theme_field.choices` from `get_available_themes()` by writing to a class-level `Field` object, which every instance of the model shares. | Plan 04 Task 1 |
| The settings dialog draws a `ChoiceField` and writes the chosen theme back. Its typed round trip is broken for other field kinds. | Plan 05 Task 1 to Task 3 |
| `ThemeService` is still reached with `ServiceLocator.get_service("themes")`, a string. | Plan 07 |
