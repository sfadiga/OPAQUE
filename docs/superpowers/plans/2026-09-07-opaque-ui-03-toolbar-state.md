# Plan 03 — Toolbar State and Theme Propagation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the feature toolbar report the true open state of every feature window, using the Qt checked state instead of an injected style sheet.

**Architecture:** The current code fakes a toggle state by writing a background colour into each button's style sheet. That approach caused three defects at once: the state never clears, the colour is the only cue, and the colour goes stale after a theme change. `QToolButton` already has a checked state. The platform style and every third-party theme already draw it, with a frame change as well as a colour change, and Qt reports it to a screen reader. Delete the style sheet machinery and use the built-in state.

**Tech Stack:** PySide6 `QToolBar`, `QToolButton`.

Read **Rules for the executing agent** in `2026-09-07-opaque-ui-00-index.md` before you start.

**Closes:** C1, C2, O2, W6. Half of C3 — this plan makes `update_theme` correct, and Plan 08 Task 7 connects it to `ThemeService.theme_changed`.

**Depends on:** Plan 02.

**File ownership:** This plan modifies `src/opaque/view/widgets/toolbar.py` and nothing else in `src/`. It is safe to run at the same time as Plans 04 to 08.

---

## Background: what is wrong today

Read these four lines before you change anything. They are the whole defect.

```python
# toolbar.py:85-86 — the name says inactive, the body says active.
def connect_signal_to_set_inactive(self, deactivate_signal: Callable, button: QToolButton):
    deactivate_signal(lambda: self._set_active(button))
```

```python
# toolbar.py:212 — Qt Style Sheets have no opacity property. This line does nothing.
opacity: 0.8;
```

`_set_inactive` at `toolbar.py:235` is never called from anywhere. It is dead code.

---

## File Structure

| Path | Responsibility |
|---|---|
| Modify `src/opaque/view/widgets/toolbar.py` | Holds the feature buttons and their checked state. Loses all colour and style sheet logic. |
| Create `tests/view/__init__.py` | Test package marker. |
| Create `tests/view/test_toolbar.py` | Proves the checked state follows the window signals, and proves no style sheet is written. |

---

### Task 1: A test double for a feature presenter

`OpaqueMainToolbar.add_feature` reads only five things from a presenter. Building a real `BasePresenter` needs a model, a view, an application window and a service locator, which is far more than the toolbar needs. Write a small duck-typed double instead.

**Files:**
- Create: `tests/view/__init__.py`
- Test: `tests/view/test_toolbar.py`

- [ ] **Step 1: Create the test package marker**

Create `tests/view/__init__.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the OPAQUE view layer."""
```

- [ ] **Step 2: Write the test double and one passing sanity test**

Create `tests/view/test_toolbar.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""
Tests for OpaqueMainToolbar.

The toolbar reads only five members from a presenter, so these tests use a
duck-typed double instead of a real BasePresenter. A real presenter needs a
model, a view, a main window and a populated ServiceLocator, none of which the
toolbar touches.
"""

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QToolButton

from opaque.view.widgets.toolbar import OpaqueMainToolbar


class FakeView(QObject):
    """Emits the same four signals as OpaqueMdiSubWindow."""

    window_opened = Signal()
    window_closed = Signal()
    window_focused = Signal()
    window_unfocused = Signal()

    def __init__(self):
        super().__init__()
        self.open_close_calls = 0

    def open_close(self) -> None:
        self.open_close_calls += 1


class FakeModel:
    def __init__(self, name: str):
        self._name = name

    def feature_name(self) -> str:
        return self._name

    def feature_description(self) -> str:
        return f"{self._name} description"

    def feature_icon(self) -> QIcon:
        return QIcon()


class FakePresenter:
    def __init__(self, name: str):
        self.model = FakeModel(name)
        self.view = FakeView()


def test_the_double_satisfies_add_feature(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    button = toolbar.add_feature(FakePresenter("Alpha"))
    assert isinstance(button, QToolButton)
    assert button.text() == "Alpha"
```

- [ ] **Step 3: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_toolbar.py -q
```

Expected: PASS. `1 passed`.

This step passes against the unchanged code on purpose. It proves the double is valid before you rely on it.

- [ ] **Step 4: Commit**

```bash
git add tests/view/__init__.py tests/view/test_toolbar.py
git commit -m "test(toolbar): add a duck-typed presenter double"
```

---

### Task 2: The checked state must follow the window signals

**Files:**
- Modify: `src/opaque/view/widgets/toolbar.py`
- Test: `tests/view/test_toolbar.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_toolbar.py`:

```python
def test_a_new_feature_button_is_checkable_and_starts_unchecked(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    button = toolbar.add_feature(FakePresenter("Alpha"))
    assert button.isCheckable() is True
    assert button.isChecked() is False


def test_opening_a_window_checks_its_button(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    presenter = FakePresenter("Alpha")
    button = toolbar.add_feature(presenter)

    presenter.view.window_opened.emit()

    assert button.isChecked() is True


def test_closing_a_window_unchecks_its_button(qtbot):
    """This is defect C1. The old code called _set_active on the close signal."""
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    presenter = FakePresenter("Alpha")
    button = toolbar.add_feature(presenter)

    presenter.view.window_opened.emit()
    presenter.view.window_closed.emit()

    assert button.isChecked() is False


def test_focusing_a_second_window_unchecks_the_first(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    first = FakePresenter("Alpha")
    second = FakePresenter("Beta")
    first_button = toolbar.add_feature(first)
    second_button = toolbar.add_feature(second)

    first.view.window_opened.emit()
    second.view.window_focused.emit()

    assert second_button.isChecked() is True
    assert first_button.isChecked() is False


def test_closing_one_window_leaves_another_checked(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    first = FakePresenter("Alpha")
    second = FakePresenter("Beta")
    first_button = toolbar.add_feature(first)
    second_button = toolbar.add_feature(second)

    second.view.window_opened.emit()
    first.view.window_closed.emit()

    assert second_button.isChecked() is True
    assert first_button.isChecked() is False


def test_clicking_the_button_calls_open_close(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    presenter = FakePresenter("Alpha")
    button = toolbar.add_feature(presenter)

    button.click()

    assert presenter.view.open_close_calls == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_toolbar.py -q
```

Expected: FAIL. At least `test_a_new_feature_button_is_checkable_and_starts_unchecked` and `test_closing_a_window_unchecks_its_button` fail. The second one is defect C1.

- [ ] **Step 3: Track the feature buttons**

In `src/opaque/view/widgets/toolbar.py`, inside `__init__`, replace these two lines:

```python
        self._active_button: Optional[QToolButton] = None
        self._current_highlight_style: str = ""
```

with these two lines:

```python
        # Every feature button, in the order it was added. The checked state is
        # exclusive across this list.
        self._feature_buttons: List[QToolButton] = []
```

Then change the typing import at the top of the file from:

```python
from typing import Optional, Callable
```

to:

```python
from typing import Callable, List, Optional
```

- [ ] **Step 4: Make the button checkable and register it**

In `add_feature`, after the line `button.setMinimumSize(70, 0)`, add these three lines:

```python
        # Qt draws the checked state itself, in every platform style and in
        # every third-party theme. The visual includes a frame change as well
        # as a colour change, so the state is not carried by colour alone.
        button.setCheckable(True)
        self._feature_buttons.append(button)
```

- [ ] **Step 5: Fix the inactive connection**

In `connect_signal_to_set_inactive`, replace the body. Replace this:

```python
    def connect_signal_to_set_inactive(self, deactivate_signal: Callable, button: QToolButton):
        deactivate_signal(lambda: self._set_active(button))
```

with this:

```python
    def connect_signal_to_set_inactive(self, deactivate_signal: Callable, button: QToolButton):
        deactivate_signal(lambda: self._set_inactive(button))
```

- [ ] **Step 6: Rewrite the two state methods**

Replace both `_set_active` and `_set_inactive` with exactly this:

```python
    def _set_active(self, button_to_activate: QToolButton) -> None:
        """
        Check one feature button and clear every other one.

        The checked state is exclusive because only one MDI sub window can hold
        the focus at a time.
        """
        for button in self._feature_buttons:
            button.setChecked(button is button_to_activate)

    def _set_inactive(self, button_to_deactivate: QToolButton) -> None:
        """Clear the checked state of one feature button."""
        button_to_deactivate.setChecked(False)
```

- [ ] **Step 7: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_toolbar.py -q
```

Expected: PASS. `7 passed`.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/widgets/toolbar.py tests/view/test_toolbar.py
git commit -m "fix(toolbar): use the Qt checked state so the active feature clears on close"
```

---

### Task 3: Delete the style sheet colour machinery

**Files:**
- Modify: `src/opaque/view/widgets/toolbar.py`
- Test: `tests/view/test_toolbar.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_toolbar.py`:

```python
def test_no_style_sheet_is_written_on_any_button(qtbot):
    """
    Defect C2. The old code injected a background colour with no text colour,
    which fell below 4.5:1 against light text in a dark theme.
    """
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    presenter = FakePresenter("Alpha")
    button = toolbar.add_feature(presenter)

    presenter.view.window_opened.emit()

    assert button.styleSheet() == ""


def test_the_toolbar_no_longer_exposes_a_hardcoded_colour():
    assert not hasattr(OpaqueMainToolbar, "DEFAULT_HIGHLIGHT_COLOR")


def test_update_theme_is_safe_to_call_with_no_features(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    toolbar.update_theme()


def test_update_theme_keeps_the_checked_state(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    presenter = FakePresenter("Alpha")
    button = toolbar.add_feature(presenter)
    presenter.view.window_opened.emit()

    toolbar.update_theme()

    assert button.isChecked() is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_toolbar.py -q
```

Expected: FAIL, on `test_the_toolbar_no_longer_exposes_a_hardcoded_colour`.

- [ ] **Step 3: Delete the colour code**

In `src/opaque/view/widgets/toolbar.py`, delete all of the following:

1. The class attribute and its comment:

```python
    # Default fallback color if theme doesn't provide one
    DEFAULT_HIGHLIGHT_COLOR = "rgb(85, 170, 0)"
```

2. The whole `_get_theme_highlight_color` method.

3. The whole `_update_highlight_style` method.

4. The call `self._update_highlight_style()` at the end of `__init__`.

- [ ] **Step 4: Replace `update_theme`**

Replace the whole `update_theme` method with exactly this:

```python
    def update_theme(self) -> None:
        """
        Repaint the toolbar after the application theme changed.

        The toolbar writes no colours of its own. A style sheet theme changes
        the button appearance, but Qt does not always repolish a widget that
        was created before the style sheet was installed, so ask for it here.

        Connect this to ThemeService.theme_changed.
        """
        style = self.style()
        for button in self._feature_buttons:
            style.unpolish(button)
            style.polish(button)
        style.unpolish(self)
        style.polish(self)
        self.update()
```

- [ ] **Step 5: Remove the now-unused imports**

At the top of `src/opaque/view/widgets/toolbar.py`, change:

```python
from PySide6.QtWidgets import QToolBar, QToolButton, QWidget, QApplication
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPalette
```

to:

```python
from PySide6.QtWidgets import QToolBar, QToolButton, QWidget
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
```

- [ ] **Step 6: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_toolbar.py -q
```

Expected: PASS. `11 passed`.

- [ ] **Step 7: Confirm no colour literal is left in the file**

Run:

```
venv\Scripts\python.exe -c "import pathlib,re; text=pathlib.Path('src/opaque/view/widgets/toolbar.py').read_text(encoding='utf-8'); hits=re.findall(r'#[0-9a-fA-F]{6}|rgb\(|background-color|opacity', text); print(hits or 'CLEAN')"
```

Expected: `CLEAN`.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/widgets/toolbar.py tests/view/test_toolbar.py
git commit -m "fix(toolbar): delete the hand-rolled highlight style sheet"
```

---

### Task 4: The notification button carries its own state and an unread count

`NotificationPresenter._on_notification_count_changed` is an empty `pass`, so the count is calculated and thrown away. When the dock is hidden, an unread notification is invisible. The count goes in the button text, not in a coloured dot, so it is readable without colour and it is readable by a screen reader.

**Files:**
- Modify: `src/opaque/view/widgets/toolbar.py`
- Test: `tests/view/test_toolbar.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_toolbar.py`:

```python
def test_the_notification_button_is_checkable(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    button = toolbar.add_notification_button(lambda: None)
    assert button.isCheckable() is True
    assert button.isChecked() is False


def test_set_notifications_visible_updates_the_checked_state(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    button = toolbar.add_notification_button(lambda: None)

    toolbar.set_notifications_visible(True)
    assert button.isChecked() is True

    toolbar.set_notifications_visible(False)
    assert button.isChecked() is False


def test_a_zero_count_shows_the_plain_label(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    button = toolbar.add_notification_button(lambda: None)

    toolbar.set_notification_count(0)

    assert button.text() == "Notifications"


def test_a_positive_count_appears_in_the_button_text(qtbot):
    """
    Defect W6. The count must be readable as text, not as a coloured dot,
    so it survives a colour-blindness simulation and a screen reader.
    """
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    button = toolbar.add_notification_button(lambda: None)

    toolbar.set_notification_count(3)

    assert "3" in button.text()


def test_a_positive_count_appears_in_the_accessible_name(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    button = toolbar.add_notification_button(lambda: None)

    toolbar.set_notification_count(3)

    assert "3" in button.accessibleName()


def test_a_large_count_is_capped(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    button = toolbar.add_notification_button(lambda: None)

    toolbar.set_notification_count(250)

    assert "99+" in button.text()


def test_the_count_api_is_safe_before_the_button_exists(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    toolbar.set_notification_count(5)
    toolbar.set_notifications_visible(True)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_toolbar.py -q
```

Expected: FAIL, with `AttributeError: 'OpaqueMainToolbar' object has no attribute 'set_notifications_visible'`.

- [ ] **Step 3: Store the notification button**

In `__init__`, directly after the `self._feature_buttons: List[QToolButton] = []` line you added in Task 2, add:

```python
        # The notification toggle. None until add_notification_button runs.
        self._notification_button: Optional[QToolButton] = None
        self._notification_count: int = 0
```

- [ ] **Step 4: Replace `add_notification_button`**

Replace the whole `add_notification_button` method, including its long comment block, with exactly this:

```python
    def add_notification_button(self, callback: Callable) -> QToolButton:
        """
        Add the notification panel toggle.

        The button is checkable so it reports whether the panel is open. Call
        set_notifications_visible to keep it in step with the dock, and
        set_notification_count to show the unread count.
        """
        notif_button = QToolButton()
        notif_button.setText(self.tr("Notifications"))
        notif_button.setToolTip(self.tr("Toggle Notifications Panel"))
        notif_button.setIcon(QIcon.fromTheme("dialog-information"))
        notif_button.setIconSize(QSize(24, 24))
        notif_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        notif_button.setMinimumSize(70, 0)
        notif_button.setCheckable(True)
        notif_button.setAccessibleName(self.tr("Notifications"))
        notif_button.clicked.connect(callback)

        self._notification_button = notif_button

        # Group the toggle with Cascade and Tiled, which sit before the
        # separator that _setup_default_buttons adds.
        actions = self.actions()
        if actions and actions[-1].isSeparator():
            self.insertWidget(actions[-1], notif_button)
        else:
            self.addWidget(notif_button)

        return notif_button
```

- [ ] **Step 5: Add the two new state methods**

Add these methods directly after `add_notification_button`:

```python
    # The highest count shown as a number. Above this the label reads "99+",
    # because an exact count stops being useful and starts widening the button.
    NOTIFICATION_COUNT_LIMIT: int = 99

    def set_notifications_visible(self, visible: bool) -> None:
        """Keep the notification toggle in step with the panel."""
        if self._notification_button is None:
            return
        self._notification_button.setChecked(visible)

    def set_notification_count(self, count: int) -> None:
        """
        Show the unread notification count on the toggle.

        The count is text, not a coloured dot, so it stays readable for a user
        with a colour vision deficiency and it reaches a screen reader.
        """
        self._notification_count = max(0, count)
        if self._notification_button is None:
            return

        label = self.tr("Notifications")
        if self._notification_count == 0:
            self._notification_button.setText(label)
            self._notification_button.setAccessibleName(label)
            self._notification_button.setToolTip(
                self.tr("Toggle Notifications Panel"))
            return

        if self._notification_count > self.NOTIFICATION_COUNT_LIMIT:
            shown = f"{self.NOTIFICATION_COUNT_LIMIT}+"
        else:
            shown = str(self._notification_count)

        self._notification_button.setText(f"{label} ({shown})")
        self._notification_button.setAccessibleName(f"{label} ({shown})")
        self._notification_button.setToolTip(
            self.tr("Toggle Notifications Panel. Unread: ") + shown)
```

Note the tooltip is built by joining a translated literal and a number. Never place the number inside the `tr()` argument.

- [ ] **Step 6: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_toolbar.py -q
```

Expected: PASS. `18 passed`.

- [ ] **Step 7: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `65 passed`.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/widgets/toolbar.py tests/view/test_toolbar.py
git commit -m "feat(toolbar): checkable notification toggle with a readable unread count"
```

---

## Definition of done

- [ ] `venv\Scripts\python.exe -m pytest tests/view/test_toolbar.py -q` prints `18 passed`.
- [ ] The regex check in Task 3 Step 7 prints `CLEAN`.
- [ ] `grep -n "_update_highlight_style\|DEFAULT_HIGHLIGHT_COLOR\|_get_theme_highlight_color" src/opaque/view/widgets/toolbar.py` returns nothing.
- [ ] `update_theme` exists and repolishes the buttons. Plan 08 Task 7 connects it.
