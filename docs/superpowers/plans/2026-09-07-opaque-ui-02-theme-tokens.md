# Plan 02 — Theme Tokens and Type Scale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create one semantic colour token layer and one type scale, so no widget in the framework ever writes a literal colour, font family or font size again.

**Architecture:** Colours come from two sources. Roles that the active theme controls (surface, text, outline, interactive) are read from `QApplication.palette()`, so a `qdarkstyle` or `qt-material` theme change is picked up for free. Status roles (error, warning, info, success, neutral) are not in `QPalette`, so the module holds one fixed table for a light theme and one for a dark theme, and picks the table from the measured lightness of the window colour. Every pair in both tables is at or above the WCAG 4.5:1 text contrast ratio, and a test proves it.

`ThemeService` gains a `theme_changed` signal so widgets can repaint after a theme change.

**Tech Stack:** PySide6 `QPalette`, `QColor`, `QFont`, `QFontDatabase`.

Read **Rules for the executing agent** in `2026-09-07-opaque-ui-00-index.md` before you start.

**Closes:** O1, W22, W23. Provides the foundation for C5 and C6.

---

## File Structure

| Path | Responsibility |
|---|---|
| Create `src/opaque/view/theme/__init__.py` | Public surface. Re-exports every token function and `TypeScale`. This is the only import path a widget may use. |
| Create `src/opaque/view/theme/contrast.py` | Pure WCAG maths. No Qt widgets, no palette access. `relative_luminance`, `contrast_ratio`, `readable_foreground`. |
| Create `src/opaque/view/theme/tokens.py` | Palette-derived roles, the status colour tables, `is_dark_theme`, `muted_on_surface`. |
| Create `src/opaque/view/theme/type_scale.py` | `TypeScale`. Derives every font from `QApplication.font()` so the OS font scale is respected. |
| Modify `src/opaque/services/theme_service.py` | Adds `theme_changed` signal, `DEFAULT_THEME`, `is_valid_theme`. |
| Create `tests/theme/__init__.py` | Test package marker. |
| Create `tests/theme/test_contrast.py` | Proves the WCAG maths and proves every status pair passes 4.5:1. |
| Create `tests/theme/test_tokens.py` | Proves the palette roles and `muted_on_surface`. |
| Create `tests/theme/test_type_scale.py` | Proves the scale respects the application font and never goes below the minimum. |

`contrast.py` is kept separate from `tokens.py` on purpose. It has no Qt dependency beyond `QColor`, so later plans can call it inside an assertion without building a widget.

---

### Task 1: Pure WCAG contrast maths

**Files:**
- Create: `src/opaque/view/theme/__init__.py`
- Create: `src/opaque/view/theme/contrast.py`
- Create: `tests/theme/__init__.py`
- Test: `tests/theme/test_contrast.py`

- [ ] **Step 1: Write the failing test**

Create `tests/theme/__init__.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the theme token layer."""
```

Create `tests/theme/test_contrast.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the pure WCAG contrast maths."""

import pytest

from opaque.view.theme.contrast import (
    contrast_ratio,
    readable_foreground,
    relative_luminance,
)


def test_black_has_zero_luminance():
    assert relative_luminance("#000000") == pytest.approx(0.0)


def test_white_has_full_luminance():
    assert relative_luminance("#ffffff") == pytest.approx(1.0)


def test_black_on_white_is_the_maximum_ratio():
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0, abs=0.01)


def test_the_ratio_does_not_depend_on_argument_order():
    assert contrast_ratio("#000000", "#ffffff") == contrast_ratio("#ffffff", "#000000")


def test_a_colour_against_itself_is_one_to_one():
    assert contrast_ratio("#3c78a0", "#3c78a0") == pytest.approx(1.0)


def test_mid_grey_on_white_fails_the_text_threshold():
    # This is the exact defect the audit found at notification_widget.py:162.
    assert contrast_ratio("#808080", "#ffffff") < 4.5


def test_readable_foreground_picks_black_on_a_light_background():
    assert readable_foreground("#ffd54f") == "#000000"


def test_readable_foreground_picks_white_on_a_dark_background():
    assert readable_foreground("#0b6ba8") == "#ffffff"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/theme/test_contrast.py -q
```

Expected: FAIL, with `ModuleNotFoundError: No module named 'opaque.view.theme'`.

- [ ] **Step 3: Write the implementation**

Create `src/opaque/view/theme/__init__.py` with exactly this content:

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

Theme token layer.

A widget must never write a literal colour, font family or font size. Import
the tokens from this package instead. That keeps every widget correct when the
user changes the theme, and it keeps every colour pair above the WCAG contrast
threshold.
"""

from opaque.view.theme.contrast import (
    contrast_ratio,
    readable_foreground,
    relative_luminance,
)

__all__ = [
    "contrast_ratio",
    "readable_foreground",
    "relative_luminance",
]
```

Create `src/opaque/view/theme/contrast.py` with exactly this content:

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

Pure WCAG 2.2 contrast maths.

This module holds no state and reads no palette. Every function takes a colour
string and gives a number, so a test can call it directly.

Reference: https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio
"""

from PySide6.QtGui import QColor

# WCAG 2.2 minimum contrast for normal body text.
TEXT_CONTRAST_MINIMUM: float = 4.5

# WCAG 2.2 minimum contrast for large text and for user interface components.
LARGE_TEXT_CONTRAST_MINIMUM: float = 3.0

_BLACK = "#000000"
_WHITE = "#ffffff"


def _channel_luminance(value: int) -> float:
    """Convert one 0-255 sRGB channel to its linear luminance part."""
    channel = value / 255.0
    if channel <= 0.03928:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(color: str) -> float:
    """
    Return the WCAG relative luminance of a colour, from 0.0 to 1.0.

    Args:
        color: Any string that QColor accepts, for example "#1a1a1a".
    """
    value = QColor(color)
    return (
        0.2126 * _channel_luminance(value.red())
        + 0.7152 * _channel_luminance(value.green())
        + 0.0722 * _channel_luminance(value.blue())
    )


def contrast_ratio(first: str, second: str) -> float:
    """
    Return the WCAG contrast ratio between two colours.

    The result is from 1.0 (the two colours are equal) to 21.0 (black on
    white). The order of the arguments does not change the result.
    """
    first_luminance = relative_luminance(first)
    second_luminance = relative_luminance(second)
    if first_luminance >= second_luminance:
        lighter, darker = first_luminance, second_luminance
    else:
        lighter, darker = second_luminance, first_luminance
    return (lighter + 0.05) / (darker + 0.05)


def readable_foreground(background: str) -> str:
    """
    Return black or white, whichever gives more contrast on the background.

    Use this when a background colour comes from user data or from a theme and
    the foreground must stay readable.
    """
    if contrast_ratio(background, _BLACK) >= contrast_ratio(background, _WHITE):
        return _BLACK
    return _WHITE
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/theme/test_contrast.py -q
```

Expected: PASS. `8 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/opaque/view/theme tests/theme
git commit -m "feat(theme): add pure WCAG contrast maths"
```

---

### Task 2: Palette-derived colour roles

**Files:**
- Create: `src/opaque/view/theme/tokens.py`
- Modify: `src/opaque/view/theme/__init__.py`
- Test: `tests/theme/test_tokens.py`

- [ ] **Step 1: Write the failing test**

Create `tests/theme/test_tokens.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the palette-derived colour tokens."""

from opaque.view.theme.tokens import (
    interactive,
    is_dark_theme,
    on_interactive,
    on_surface,
    outline,
    surface,
)


def test_light_palette_is_not_reported_as_dark(light_palette_app):
    assert is_dark_theme() is False


def test_dark_palette_is_reported_as_dark(dark_palette_app):
    assert is_dark_theme() is True


def test_surface_comes_from_the_palette_base_role(light_palette_app):
    assert surface() == "#ffffff"


def test_on_surface_comes_from_the_palette_text_role(light_palette_app):
    assert on_surface() == "#1a1a1a"


def test_outline_comes_from_the_palette_mid_role(light_palette_app):
    assert outline() == "#b0b0b0"


def test_interactive_pair_comes_from_the_highlight_roles(light_palette_app):
    assert interactive() == "#0b6ba8"
    assert on_interactive() == "#ffffff"


def test_surface_follows_the_dark_palette(dark_palette_app):
    assert surface() == "#1e1e1e"
    assert on_surface() == "#e0e0e0"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/theme/test_tokens.py -q
```

Expected: FAIL, with `ImportError: cannot import name 'interactive'`.

- [ ] **Step 3: Write the implementation**

Create `src/opaque/view/theme/tokens.py` with exactly this content:

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

Semantic colour tokens.

Each function gives a hex string for one role, not for one appearance. Ask for
"the text colour on a surface", never for "dark grey". The role is read from
the active QPalette, so a theme change from qdarkstyle, qt-material or
qt-themes is picked up with no extra work.
"""

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from opaque.view.theme.contrast import relative_luminance

# A window luminance below this value counts as a dark theme.
_DARK_THEME_LUMINANCE_LIMIT: float = 0.18


def _palette() -> QPalette:
    """Return the active application palette, or a default one in a headless test."""
    app = QApplication.instance()
    if app is None:
        return QPalette()
    return app.palette()


def _role(role: QPalette.ColorRole) -> str:
    """Return one palette role as a hex string."""
    return _palette().color(role).name()


def is_dark_theme() -> bool:
    """Return True when the active theme uses a dark window colour."""
    window = _role(QPalette.ColorRole.Window)
    return relative_luminance(window) < _DARK_THEME_LUMINANCE_LIMIT


def surface() -> str:
    """The background of a content area, for example a text view or a list."""
    return _role(QPalette.ColorRole.Base)


def on_surface() -> str:
    """The primary text colour on top of surface()."""
    return _role(QPalette.ColorRole.Text)


def surface_variant() -> str:
    """The background of a window or a panel, one step away from surface()."""
    return _role(QPalette.ColorRole.Window)


def on_surface_variant() -> str:
    """The primary text colour on top of surface_variant()."""
    return _role(QPalette.ColorRole.WindowText)


def outline() -> str:
    """A border or a separator line."""
    return _role(QPalette.ColorRole.Mid)


def interactive() -> str:
    """The background that tells the user an element responds to input."""
    return _role(QPalette.ColorRole.Highlight)


def on_interactive() -> str:
    """The text colour on top of interactive()."""
    return _role(QPalette.ColorRole.HighlightedText)
```

- [ ] **Step 4: Extend the package surface**

In `src/opaque/view/theme/__init__.py`, replace the import block and the `__all__` list with exactly this:

```python
from opaque.view.theme.contrast import (
    contrast_ratio,
    readable_foreground,
    relative_luminance,
)
from opaque.view.theme.tokens import (
    interactive,
    is_dark_theme,
    on_interactive,
    on_surface,
    on_surface_variant,
    outline,
    surface,
    surface_variant,
)

__all__ = [
    "contrast_ratio",
    "readable_foreground",
    "relative_luminance",
    "interactive",
    "is_dark_theme",
    "on_interactive",
    "on_surface",
    "on_surface_variant",
    "outline",
    "surface",
    "surface_variant",
]
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/theme/test_tokens.py -q
```

Expected: PASS. `7 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/theme tests/theme/test_tokens.py
git commit -m "feat(theme): add palette-derived semantic colour roles"
```

---

### Task 3: A muted text colour that still passes contrast

The audit found `color: gray; font-size: 10px` at `notification_widget.py:162`. Grey on white is 3.95:1, which fails. The correct fix is not a different fixed grey, because the surface changes with the theme. Blend the text colour toward the surface, step by step, and stop at the last step that still passes 4.5:1.

**Files:**
- Modify: `src/opaque/view/theme/tokens.py`
- Modify: `src/opaque/view/theme/__init__.py`
- Test: `tests/theme/test_tokens.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/theme/test_tokens.py`:

```python
from opaque.view.theme.contrast import TEXT_CONTRAST_MINIMUM, contrast_ratio
from opaque.view.theme.tokens import muted_on_surface


def test_muted_text_still_passes_contrast_on_a_light_surface(light_palette_app):
    ratio = contrast_ratio(muted_on_surface(), surface())
    assert ratio >= TEXT_CONTRAST_MINIMUM


def test_muted_text_still_passes_contrast_on_a_dark_surface(dark_palette_app):
    ratio = contrast_ratio(muted_on_surface(), surface())
    assert ratio >= TEXT_CONTRAST_MINIMUM


def test_muted_text_is_dimmer_than_primary_text(light_palette_app):
    primary = contrast_ratio(on_surface(), surface())
    muted = contrast_ratio(muted_on_surface(), surface())
    assert muted < primary


def test_plain_grey_would_have_failed(light_palette_app):
    # Proof that the old hardcoded value was the defect, not the idea.
    assert contrast_ratio("#808080", surface()) < TEXT_CONTRAST_MINIMUM
```

Also add `on_surface` and `surface` to the existing import at the top of the file if they are not already there. They are.

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/theme/test_tokens.py -q
```

Expected: FAIL, with `ImportError: cannot import name 'muted_on_surface'`.

- [ ] **Step 3: Write the implementation**

Append this to the end of `src/opaque/view/theme/tokens.py`:

```python
def muted_on_surface() -> str:
    """
    A dimmer text colour for secondary information, for example a timestamp.

    The colour is the primary text colour blended toward the surface. The blend
    stops at the last step that still meets the WCAG text contrast minimum, so
    the result is always readable, in a light theme and in a dark theme.
    """
    background = surface()
    text = QColor(on_surface())
    back = QColor(background)

    best = text.name()
    for step in range(1, 10):
        factor = step / 10.0
        blended = QColor(
            round(text.red() + (back.red() - text.red()) * factor),
            round(text.green() + (back.green() - text.green()) * factor),
            round(text.blue() + (back.blue() - text.blue()) * factor),
        )
        if contrast_ratio(blended.name(), background) < TEXT_CONTRAST_MINIMUM:
            break
        best = blended.name()
    return best
```

Then change the import block at the top of `src/opaque/view/theme/tokens.py` from:

```python
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from opaque.view.theme.contrast import relative_luminance
```

to:

```python
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from opaque.view.theme.contrast import (
    TEXT_CONTRAST_MINIMUM,
    contrast_ratio,
    relative_luminance,
)
```

- [ ] **Step 4: Extend the package surface**

In `src/opaque/view/theme/__init__.py`, add `muted_on_surface` to the `from opaque.view.theme.tokens import (...)` block and to `__all__`, keeping both lists in alphabetical order.

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/theme/test_tokens.py -q
```

Expected: PASS. `11 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/theme tests/theme/test_tokens.py
git commit -m "feat(theme): add muted_on_surface that keeps 4.5:1 contrast"
```

---

### Task 4: Status colour roles

**Files:**
- Modify: `src/opaque/view/theme/tokens.py`
- Modify: `src/opaque/view/theme/__init__.py`
- Test: `tests/theme/test_contrast.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/theme/test_contrast.py`:

```python
from opaque.view.theme.contrast import TEXT_CONTRAST_MINIMUM
from opaque.view.theme.tokens import StatusRole, status_colors


@pytest.mark.parametrize("role", list(StatusRole))
def test_every_status_pair_passes_contrast_in_a_light_theme(role, light_palette_app):
    colors = status_colors(role)
    ratio = contrast_ratio(colors.foreground, colors.background)
    assert ratio >= TEXT_CONTRAST_MINIMUM, f"{role.value} is only {ratio:.2f}:1"


@pytest.mark.parametrize("role", list(StatusRole))
def test_every_status_pair_passes_contrast_in_a_dark_theme(role, dark_palette_app):
    colors = status_colors(role)
    ratio = contrast_ratio(colors.foreground, colors.background)
    assert ratio >= TEXT_CONTRAST_MINIMUM, f"{role.value} is only {ratio:.2f}:1"


def test_light_and_dark_tables_are_different(light_palette_app):
    light_error = status_colors(StatusRole.ERROR).background
    assert light_error == "#b3261e"


def test_dark_theme_uses_the_dark_table(dark_palette_app):
    dark_error = status_colors(StatusRole.ERROR).background
    assert dark_error == "#f2b8b5"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/theme/test_contrast.py -q
```

Expected: FAIL, with `ImportError: cannot import name 'StatusRole'`.

- [ ] **Step 3: Write the implementation**

Append this to the end of `src/opaque/view/theme/tokens.py`:

```python
class StatusRole(Enum):
    """
    A semantic status, not an appearance.

    Ask for ERROR, never for red. The table below gives a different colour for
    a light theme and for a dark theme, and both pass the WCAG text contrast
    minimum.
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class StatusColors:
    """A background, a foreground and a border for one status role."""

    background: str
    foreground: str
    border: str


# Saturated fills with light text. Verified at or above 4.5:1.
_STATUS_LIGHT = {
    StatusRole.ERROR: StatusColors("#b3261e", "#ffffff", "#8c1d18"),
    StatusRole.WARNING: StatusColors("#ffd54f", "#000000", "#c8a415"),
    StatusRole.INFO: StatusColors("#0b6ba8", "#ffffff", "#084f7d"),
    StatusRole.SUCCESS: StatusColors("#1b5e20", "#ffffff", "#124016"),
    StatusRole.NEUTRAL: StatusColors("#5f6368", "#ffffff", "#45484b"),
}

# Pale fills with dark text. A saturated fill on a dark surface glares.
_STATUS_DARK = {
    StatusRole.ERROR: StatusColors("#f2b8b5", "#601410", "#8c1d18"),
    StatusRole.WARNING: StatusColors("#ffd54f", "#000000", "#c8a415"),
    StatusRole.INFO: StatusColors("#a8c7e0", "#08324f", "#084f7d"),
    StatusRole.SUCCESS: StatusColors("#a5d6a7", "#0b2e0d", "#124016"),
    StatusRole.NEUTRAL: StatusColors("#c4c7c5", "#2b2f31", "#45484b"),
}


def status_colors(role: StatusRole) -> StatusColors:
    """Return the colour triple for one status role, correct for the active theme."""
    table = _STATUS_DARK if is_dark_theme() else _STATUS_LIGHT
    return table[role]
```

Then add these two lines to the top of the import block in `src/opaque/view/theme/tokens.py`, above the PySide6 imports:

```python
from dataclasses import dataclass
from enum import Enum
```

- [ ] **Step 4: Extend the package surface**

In `src/opaque/view/theme/__init__.py`, add `StatusColors`, `StatusRole` and `status_colors` to the tokens import block and to `__all__`.

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/theme/test_contrast.py -q
```

Expected: PASS. `22 passed`. Ten of those are the two parametrised contrast checks, five roles each.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/theme tests/theme/test_contrast.py
git commit -m "feat(theme): add status colour roles with proven 4.5:1 contrast"
```

---

### Task 5: The type scale

The audit found `QFont("Arial", 8)`, `QFont("Consolas", 9)` and `QFont("Courier", 9)`, plus sizes picked per call site as `pointSize() + 4`, `+ 2`, `+ 1` and `- 1`. All of them ignore the OS font scale. `TypeScale` derives every size from `QApplication.font()` using a minor third ratio of 1.2, and clamps every result so nothing drops below a readable size.

**Files:**
- Create: `src/opaque/view/theme/type_scale.py`
- Modify: `src/opaque/view/theme/__init__.py`
- Test: `tests/theme/test_type_scale.py`

- [ ] **Step 1: Write the failing test**

Create `tests/theme/test_type_scale.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the type scale."""

import pytest
from PySide6.QtGui import QFont

from opaque.view.theme.type_scale import TypeScale


@pytest.fixture
def scaled_app(qapp):
    """Give the application a known 10 point base font, then restore it."""
    original = qapp.font()
    base = QFont(original)
    base.setPointSizeF(10.0)
    qapp.setFont(base)
    yield qapp
    qapp.setFont(original)


def test_body_matches_the_application_font_size(scaled_app):
    assert TypeScale.body().pointSizeF() == pytest.approx(10.0)


def test_the_scale_grows_by_the_ratio(scaled_app):
    assert TypeScale.h2().pointSizeF() == pytest.approx(10.0 * 1.2)
    assert TypeScale.h1().pointSizeF() == pytest.approx(10.0 * 1.2 * 1.2)


def test_the_scale_is_ordered(scaled_app):
    sizes = [
        TypeScale.caption().pointSizeF(),
        TypeScale.body().pointSizeF(),
        TypeScale.h2().pointSizeF(),
        TypeScale.h1().pointSizeF(),
        TypeScale.display().pointSizeF(),
    ]
    assert sizes == sorted(sizes)


def test_nothing_drops_below_the_minimum(qapp):
    original = qapp.font()
    tiny = QFont(original)
    tiny.setPointSizeF(6.0)
    qapp.setFont(tiny)
    try:
        assert TypeScale.caption().pointSizeF() >= TypeScale.MINIMUM_POINT_SIZE
    finally:
        qapp.setFont(original)


def test_the_scale_follows_the_operating_system_font_scale(qapp):
    original = qapp.font()
    try:
        large = QFont(original)
        large.setPointSizeF(20.0)
        qapp.setFont(large)
        assert TypeScale.body().pointSizeF() == pytest.approx(20.0)
    finally:
        qapp.setFont(original)


def test_monospace_does_not_hardcode_a_family(scaled_app):
    mono = TypeScale.mono()
    assert mono.family() not in ("Consolas", "Courier")
    assert mono.pointSizeF() == pytest.approx(10.0)


def test_emphasis_raises_the_weight_without_changing_the_size(scaled_app):
    plain = TypeScale.body()
    strong = TypeScale.emphasis(plain)
    assert strong.pointSizeF() == pytest.approx(plain.pointSizeF())
    assert strong.weight() > plain.weight()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/theme/test_type_scale.py -q
```

Expected: FAIL, with `ModuleNotFoundError: No module named 'opaque.view.theme.type_scale'`.

- [ ] **Step 3: Write the implementation**

Create `src/opaque/view/theme/type_scale.py` with exactly this content:

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

The framework type scale.

Every size comes from the application font multiplied by a fixed ratio. That
keeps the sizes in proportion to each other, and it keeps them correct when the
user raises the operating system font size.

Never write a font family or a point size in a widget. Ask for a role.

Use no more than three roles on one screen. More than three sizes makes a
screen look noisy.
"""

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


class TypeScale:
    """A modular type scale built on a minor third ratio."""

    # A minor third. Moderate contrast between steps, which suits a dense
    # engineering interface.
    RATIO: float = 1.2

    # No role may produce a font smaller than this, whatever the base is.
    MINIMUM_POINT_SIZE: float = 9.0

    # Used only when there is no QApplication, which happens in a unit test
    # that does not need a widget.
    FALLBACK_POINT_SIZE: float = 9.0

    @classmethod
    def base_point_size(cls) -> float:
        """Return the application font size, which follows the OS font scale."""
        app = QApplication.instance()
        if app is None:
            return cls.FALLBACK_POINT_SIZE
        size = app.font().pointSizeF()
        if size <= 0:
            return cls.FALLBACK_POINT_SIZE
        return size

    @classmethod
    def _size_for_step(cls, step: int) -> float:
        """Return the point size for one step of the scale."""
        size = cls.base_point_size() * (cls.RATIO ** step)
        return max(size, cls.MINIMUM_POINT_SIZE)

    @classmethod
    def _font_for_step(cls, step: int) -> QFont:
        """Return a copy of the application font resized to one step."""
        app = QApplication.instance()
        font = QFont(app.font()) if app is not None else QFont()
        font.setPointSizeF(cls._size_for_step(step))
        return font

    @classmethod
    def caption(cls) -> QFont:
        """Secondary information, for example a timestamp or a unit label."""
        return cls._font_for_step(-1)

    @classmethod
    def body(cls) -> QFont:
        """Primary reading text. This is the base of the scale."""
        return cls._font_for_step(0)

    @classmethod
    def h2(cls) -> QFont:
        """A section heading inside a panel."""
        return cls._font_for_step(1)

    @classmethod
    def h1(cls) -> QFont:
        """A dialog title or a page title."""
        return cls._font_for_step(2)

    @classmethod
    def display(cls) -> QFont:
        """A single large value, for example a version number on an About page."""
        return cls._font_for_step(3)

    @classmethod
    def mono(cls, step: int = 0) -> QFont:
        """
        A fixed-width font for console output and for hexadecimal values.

        The family comes from the platform, not from a literal name, so it is
        correct on Windows, on macOS and on Linux.
        """
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSizeF(cls._size_for_step(step))
        return font

    @staticmethod
    def emphasis(font: QFont) -> QFont:
        """
        Return a copy of a font at medium weight.

        Use this for a heading or for a list item title. Never use bold inside
        body text.
        """
        emphasised = QFont(font)
        emphasised.setWeight(QFont.Weight.Medium)
        return emphasised
```

- [ ] **Step 4: Extend the package surface**

In `src/opaque/view/theme/__init__.py`, add this import line below the tokens import block:

```python
from opaque.view.theme.type_scale import TypeScale
```

and add `"TypeScale"` to `__all__`.

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/theme/test_type_scale.py -q
```

Expected: PASS. `7 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/theme tests/theme/test_type_scale.py
git commit -m "feat(theme): add TypeScale derived from the application font"
```

---

### Task 6: A theme change signal on ThemeService

Nothing in the framework can react to a theme change today, because `ThemeService.apply_theme` tells nobody. Plan 03 needs this signal.

**Files:**
- Modify: `src/opaque/services/theme_service.py`
- Test: `tests/theme/test_theme_service.py`

- [ ] **Step 1: Write the failing test**

Create `tests/theme/test_theme_service.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the theme service signal and validation."""

import pytest

from opaque.services.theme_service import ThemeService


@pytest.fixture
def theme_service(qapp):
    service = ThemeService(qapp)
    service.initialize()
    yield service
    service.cleanup()


def test_default_theme_is_a_valid_theme_name(theme_service):
    assert theme_service.is_valid_theme(ThemeService.DEFAULT_THEME)


def test_an_unknown_theme_name_is_rejected(theme_service):
    assert theme_service.is_valid_theme("light") is False


def test_apply_theme_reports_success_for_a_known_theme(theme_service):
    assert theme_service.apply_theme("Default") is True


def test_apply_theme_reports_failure_for_an_unknown_theme(theme_service):
    assert theme_service.apply_theme("light") is False


def test_apply_theme_emits_theme_changed_on_success(theme_service, qtbot):
    with qtbot.waitSignal(theme_service.theme_changed, timeout=1000) as blocker:
        theme_service.apply_theme("Default")
    assert blocker.args == ["Default"]


def test_apply_theme_does_not_emit_for_an_unknown_theme(theme_service, qtbot):
    with qtbot.assertNotEmitted(theme_service.theme_changed):
        theme_service.apply_theme("light")


def test_current_theme_tracks_the_last_applied_theme(theme_service):
    theme_service.apply_theme("Default")
    assert theme_service.current_theme() == "Default"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/theme/test_theme_service.py -q
```

Expected: FAIL, with `AttributeError: type object 'ThemeService' has no attribute 'DEFAULT_THEME'`.

- [ ] **Step 3: Write the implementation**

In `src/opaque/services/theme_service.py`, change the import line:

```python
from PySide6.QtWidgets import QApplication
```

to:

```python
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QApplication
```

Then replace the class header and `__init__` block. Replace this:

```python
class ThemeService(BaseService):
    """Discovers and applies themes from qt-material and QDarkStyleSheet."""

    def __init__(self, app: QApplication) -> None:
```

with this:

```python
class ThemeService(BaseService):
    """Discovers and applies themes from qt-material and QDarkStyleSheet."""

    # Emitted with the theme name after a theme is applied. A widget that
    # paints its own colours must connect to this and repaint.
    theme_changed = Signal(str)

    # The one theme name that is always available. Any application default must
    # be a name that get_available_themes() returns.
    DEFAULT_THEME: str = "Default"

    def __init__(self, app: QApplication) -> None:
```

Then, at the end of the existing `__init__` body, after the line `self.available_themes: List[str] = []`, add:

```python
        # The name of the theme applied most recently.
        self._current_theme: str = self.DEFAULT_THEME
```

Then add these two methods directly after `get_available_themes`:

```python
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
        return theme_name in self.available_themes
```

Now replace the whole `apply_theme` method with this:

```python
    def apply_theme(self, theme_name: str) -> bool:
        """
        Apply a theme to the application by name.

        Returns:
            True when the theme was applied. False when the name is unknown,
            in which case the current theme is left alone.
        """
        if not self.is_valid_theme(theme_name):
            return False

        if theme_name == self.DEFAULT_THEME:
            self._app.setStyleSheet("")

        elif theme_name.startswith('qt-themes: '):
            actual_theme_name = theme_name.replace('qt-themes: ', '')
            theme_key = actual_theme_name.replace(' ', '_').lower()
            try:
                qt_themes.set_theme(theme_key)
            except Exception:
                return False

        elif theme_name in self._qt_material_themes:
            # Invert secondary colors for light themes from qt-material
            invert: bool = 'light_' in theme_name
            apply_stylesheet(
                self._app, theme=f"{theme_name}.xml", invert_secondary=invert)

        elif theme_name == 'QDarkStyle':
            self._app.setStyleSheet(load_stylesheet())

        elif theme_name == 'QLightStyle':
            self._app.setStyleSheet(load_stylesheet(palette=LightPalette))

        else:
            return False

        self._current_theme = theme_name
        self.theme_changed.emit(theme_name)
        return True
```

Note three deliberate changes. The empty-name branch is gone, because an empty name is now simply invalid. The `print` calls are gone, because a failure is now reported through the return value. `QLightStyle` no longer catches `ImportError`, because `LightPalette` is imported at module level, so an import failure would already have stopped the module from loading.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/theme/test_theme_service.py -q
```

Expected: PASS. `7 passed`.

- [ ] **Step 5: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `47 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/services/theme_service.py tests/theme/test_theme_service.py
git commit -m "feat(theme): add theme_changed signal and theme name validation"
```

---

## Definition of done

- [ ] `venv\Scripts\python.exe -m pytest tests/theme -q` passes.
- [ ] `status_colors` is proven at or above 4.5:1 for all five roles, in both palettes.
- [ ] `TypeScale.body()` follows the application font size.
- [ ] `ThemeService.apply_theme` returns a bool and emits `theme_changed`.
- [ ] No widget file was modified by this plan. The consumers come in Plans 03 to 08.
