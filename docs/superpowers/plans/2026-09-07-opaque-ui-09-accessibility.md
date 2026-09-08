# Plan 09 — Accessibility Sweep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the framework a keyboard map the user can read, turn the one control that is only clickable into a real button, and add a sweep test that stops any new widget from shipping a target below 24 pixels or a control with no accessible name.

**Architecture:** Plans 03 to 08 fixed the keyboard and the hit targets one widget at a time. This plan adds the two things that keep them fixed: a dialog that lists every shortcut the application actually has, built by reading `QAction.shortcut()` at run time so it can never go stale, and one sweep test that walks every widget the framework ships.

**Tech Stack:** PySide6, pytest, pytest-qt.

Read **Rules for the executing agent** in `2026-09-07-opaque-ui-00-index.md` before you start.

**Depends on:** Plan 01 to Plan 08. Every one of them must be merged first. The sweep test in Task 4 checks the widgets those plans repair, and it will fail if any of them is missing.

**About the totals:** the `pytest -q` totals assume Plan 01 to Plan 08 are merged.

---

## Findings closed by this plan

| ID | Finding | Task |
|---|---|---|
| O4 | Publish a keyboard map | 1, 2 |
| C8 | No keyboard layer (last part) | 2, 3, 4 |
| C9 | Hit targets 16–30 px (sweep) | 3, 4 |

---

## File Structure

| Path | Responsibility |
|---|---|
| Create `src/opaque/view/dialogs/keyboard_map.py` | `collect_shortcuts` and `KeyboardMapDialog`. |
| Modify `src/opaque/view/application.py` | A Help menu, and F1 to open the keyboard map. |
| Modify `src/opaque/view/dialogs/version_info.py` | `VersionStatusWidget` becomes a real button. |
| Create `tests/view/test_keyboard_map.py` | Shortcut collection and the dialog. |
| Create `tests/view/test_accessibility_sweep.py` | The one test that walks every shipped widget. |

---

### Task 1: Collect the shortcuts and show them (O4)

A user has no way to learn what keys the application answers to. A hand written list would be wrong within a week. This task reads the shortcuts off the live `QAction` objects, so the list is always the truth.

**Files:**
- Create: `src/opaque/view/dialogs/keyboard_map.py`
- Test: `tests/view/test_keyboard_map.py`

- [ ] **Step 1: Write the failing test**

Create `tests/view/test_keyboard_map.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the keyboard map dialog."""

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QWidget

from opaque.view.dialogs.keyboard_map import KeyboardMapDialog, collect_shortcuts


def _window_with_actions(qtbot, entries):
    """Build a widget carrying one QAction for each label and key pair."""
    window = QWidget()
    qtbot.addWidget(window)
    for label, key in entries:
        action = QAction(label, window)
        if key:
            action.setShortcut(QKeySequence(key))
        window.addAction(action)
    return window


def test_collect_shortcuts_finds_an_action_with_a_key(qtbot):
    window = _window_with_actions(qtbot, [("Save Workspace", "Ctrl+S")])
    entries = collect_shortcuts(window)
    assert entries == [("Save Workspace", "Ctrl+S")]


def test_collect_shortcuts_skips_an_action_with_no_key(qtbot):
    window = _window_with_actions(
        qtbot, [("Save Workspace", "Ctrl+S"), ("No Key", None)])
    labels = [label for label, _ in collect_shortcuts(window)]
    assert labels == ["Save Workspace"]


def test_collect_shortcuts_is_sorted_by_label(qtbot):
    window = _window_with_actions(qtbot, [
        ("Zoom In", "Ctrl++"),
        ("About", "F2"),
        ("Manual", "F1"),
    ])
    labels = [label for label, _ in collect_shortcuts(window)]
    assert labels == sorted(labels)


def test_collect_shortcuts_drops_the_menu_ampersand(qtbot):
    window = _window_with_actions(qtbot, [("&Save Workspace", "Ctrl+S")])
    assert collect_shortcuts(window)[0][0] == "Save Workspace"


def test_the_dialog_lists_every_shortcut(qtbot, light_palette_app):
    window = _window_with_actions(qtbot, [
        ("Save Workspace", "Ctrl+S"),
        ("Load Workspace", "Ctrl+O"),
    ])
    dialog = KeyboardMapDialog(window)
    qtbot.addWidget(dialog)
    assert dialog.table.rowCount() == 2
    assert dialog.table.item(0, 0).text() == "Load Workspace"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_keyboard_map.py -q
```

Expected: FAIL, with `ModuleNotFoundError: No module named 'opaque.view.dialogs.keyboard_map'`.

- [ ] **Step 3: Write the implementation**

Create `src/opaque/view/dialogs/keyboard_map.py` with exactly this content:

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

The keyboard map.

The list is read off the live QAction objects every time the dialog opens, so
it can never disagree with the application. A hand written list goes stale.
"""

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from opaque.view.theme import TypeScale


def collect_shortcuts(window: QWidget) -> List[Tuple[str, str]]:
    """
    Return every action label and key on a window, sorted by label.

    Args:
        window: The widget whose actions are read. The actions of every child
            widget are read too, so a menu bar action is found as well.

    Returns:
        A list of label and key pairs. An action with no key is left out, and
        the menu ampersand is removed from the label.
    """
    entries: List[Tuple[str, str]] = []
    seen = set()

    for action in window.actions():
        _add_action(action, entries, seen)

    for child in window.findChildren(QWidget):
        for action in child.actions():
            _add_action(action, entries, seen)

    entries.sort(key=lambda pair: pair[0])
    return entries


def _add_action(action, entries: List[Tuple[str, str]], seen: set) -> None:
    """Add one action to the list, if it has a key and is not there already."""
    key = action.shortcut().toString()
    if not key:
        return

    label = action.text().replace("&", "").strip()
    if not label:
        return

    if (label, key) in seen:
        return

    seen.add((label, key))
    entries.append((label, key))
```

Then append this class to the end of the same file:


```python
class KeyboardMapDialog(QDialog):
    """A read only list of every keyboard shortcut the application has."""

    def __init__(self, window: QWidget, parent: Optional[QWidget] = None):
        super().__init__(parent or window)
        self.setWindowTitle(self.tr("Keyboard Shortcuts"))
        self.setMinimumSize(420, 320)

        layout = QVBoxLayout(self)

        entries = collect_shortcuts(window)

        self.table = QTableWidget(len(entries), 2, self)
        self.table.setHorizontalHeaderLabels(
            [self.tr("Action"), self.tr("Key")])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAccessibleName(self.tr("Keyboard shortcuts"))
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)

        for row, (label, key) in enumerate(entries):
            self.table.setItem(row, 0, QTableWidgetItem(label))
            key_item = QTableWidgetItem(key)
            key_item.setFont(TypeScale.mono())
            self.table.setItem(row, 1, key_item)

        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.table.setFocus(Qt.FocusReason.OtherFocusReason)
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_keyboard_map.py -q
```

Expected: PASS. `5 passed`.

- [ ] **Step 5: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `211 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/dialogs/keyboard_map.py tests/view/test_keyboard_map.py
git commit -m "feat(a11y): add a keyboard map read from the live actions"
```

---

### Task 2: Open the keyboard map with F1 (O4, C8)

**Files:**
- Modify: `src/opaque/view/application.py`
- Test: `tests/test_application_shell.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/test_application_shell.py`:

```python
def test_the_help_menu_has_a_keyboard_map_action(app_window):
    labels = [
        action.text().replace("&", "")
        for action in app_window.help_menu.actions()
        if not action.isSeparator()
    ]
    assert "Keyboard Shortcuts" in labels


def test_the_keyboard_map_uses_the_help_key(app_window):
    action = next(
        action for action in app_window.help_menu.actions()
        if action.text().replace("&", "") == "Keyboard Shortcuts"
    )
    assert action.shortcut().toString() == "F1"


def test_the_keyboard_map_lists_the_file_menu_keys(app_window, qtbot):
    dialog = app_window.build_keyboard_map_dialog()
    qtbot.addWidget(dialog)
    labels = [
        dialog.table.item(row, 0).text()
        for row in range(dialog.table.rowCount())
    ]
    assert "Save Workspace" in labels
    assert "Keyboard Shortcuts" in labels
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: FAIL. The output contains `AttributeError: 'BaseApplication' object has no attribute 'help_menu'`.

- [ ] **Step 3: Add the Help menu**

In `src/opaque/view/application.py`, add this method directly below `_setup_file_menu`:

```python
    def _setup_help_menu(self) -> None:
        """Build the Help menu. F1 opens the keyboard map."""
        self.help_menu = self.menuBar().addMenu(self.tr("&Help"))

        keyboard_map_action = QAction(self.tr("Keyboard Shortcuts"), self)
        keyboard_map_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        keyboard_map_action.triggered.connect(self.show_keyboard_map)
        self.help_menu.addAction(keyboard_map_action)

    def build_keyboard_map_dialog(self) -> KeyboardMapDialog:
        """Build the keyboard map dialog for this window."""
        return KeyboardMapDialog(self, parent=self)

    def show_keyboard_map(self) -> None:
        """Show every keyboard shortcut this application answers to."""
        self.build_keyboard_map_dialog().exec()
```

`QKeySequence.StandardKey.HelpContents` is F1 on Windows and on Linux.

- [ ] **Step 4: Call it and import the dialog**

In the same file, replace this line:

```python
        self._setup_file_menu()
```

with exactly these two lines:

```python
        self._setup_file_menu()
        self._setup_help_menu()
```

Then add this import directly below the `from opaque.view.dialogs.settings import SettingsDialog` line:

```python
from opaque.view.dialogs.keyboard_map import KeyboardMapDialog
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: PASS. `24 passed`.

If `test_the_keyboard_map_uses_the_help_key` fails because `HelpContents` gives something other than `F1`, change the assertion to `!= ""` and note it in the commit message. Do not hardcode `F1` in the source file.

- [ ] **Step 6: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `214 passed`.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/application.py tests/test_application_shell.py
git commit -m "feat(a11y): add a Help menu and open the keyboard map with F1"
```

---

### Task 3: The version status control must be a real button (C8, C9)

`VersionStatusWidget` is a `QLabel` with a `mousePressEvent` handler. A label cannot take the keyboard focus, it shows no focus ring, and a screen reader reports it as static text. The only way to reach it is a mouse.

**Files:**
- Modify: `src/opaque/view/dialogs/version_info.py`
- Test: `tests/view/test_version_dialogs.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_version_dialogs.py`:

```python
def test_the_version_status_widget_is_a_button(qtbot, light_palette_app):
    widget = VersionStatusWidget({"version": "1.0"})
    qtbot.addWidget(widget)
    assert isinstance(widget, QAbstractButton)


def test_the_version_status_widget_can_take_the_keyboard_focus(
        qtbot, light_palette_app):
    widget = VersionStatusWidget({"version": "1.0"})
    qtbot.addWidget(widget)
    assert widget.focusPolicy() != Qt.FocusPolicy.NoFocus


def test_the_version_status_widget_is_tall_enough(qtbot, light_palette_app):
    widget = VersionStatusWidget({"version": "1.0"})
    qtbot.addWidget(widget)
    assert widget.minimumHeight() >= 24


def test_the_version_status_widget_has_an_accessible_name(
        qtbot, light_palette_app):
    widget = VersionStatusWidget({"version": "1.0"})
    qtbot.addWidget(widget)
    assert widget.accessibleName() != ""
    assert "1.0" in widget.text()
```

Then add these imports at the top of `tests/view/test_version_dialogs.py`, above the `from opaque...` lines:

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractButton
```

And replace this import line in the same file:

```python
from opaque.view.dialogs.version_info import AboutDialog, VersionInfoDialog
```

with exactly this:

```python
from opaque.view.dialogs.version_info import (
    AboutDialog,
    VersionInfoDialog,
    VersionStatusWidget,
)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_version_dialogs.py -q
```

Expected: FAIL. `test_the_version_status_widget_is_a_button` fails with `assert False`, because the widget is still a `QLabel`.

- [ ] **Step 3: Turn the label into a button**

In `src/opaque/view/dialogs/version_info.py`, replace this block:

```python
class VersionStatusWidget(QLabel):
    """Status bar widget for displaying version information."""

    def __init__(self, version_info: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.version_info = version_info or {}
        self._update_display()
```

with exactly this:

```python
class VersionStatusWidget(QPushButton):
    """
    A status bar control that opens the version information dialog.

    This was a QLabel with a mousePressEvent handler. A label cannot take the
    keyboard focus, shows no focus ring, and a screen reader reports it as
    static text. Anything the user can act on must be a real control.
    """

    # 24 pixels is the smallest target a pointer can hit reliably.
    MINIMUM_HEIGHT = 24

    def __init__(self, version_info: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.version_info = version_info or {}
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(self.MINIMUM_HEIGHT)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(self.tr("Version information"))
        self.clicked.connect(self._show_version_info)
        self._update_display()
```

- [ ] **Step 4: Replace the style and the click handler**

In the same file, replace this block:

```python
        # The hover colours come from the palette. A black overlay is
        # invisible on a dark theme.
        self.setStyleSheet(f"""
            QLabel {{
                padding: 2px 8px;
                border: 1px solid transparent;
                border-radius: 3px;
            }}
            QLabel:hover {{
                background-color: {surface_variant()};
                border-color: {outline()};
            }}
        """)
```

with exactly this:

```python
        # The hover colours come from the palette. A black overlay is
        # invisible on a dark theme. The focus rule is the visible focus
        # indicator a keyboard user needs.
        self.setStyleSheet(f"""
            QPushButton {{
                padding: 2px 8px;
                border: 1px solid transparent;
                border-radius: 3px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {surface_variant()};
                border-color: {outline()};
            }}
            QPushButton:focus {{
                border: 2px solid {interactive()};
            }}
        """)
```

Then replace this block:

```python
    def mousePressEvent(self, event) -> None:
        """Handle mouse click to show detailed version info."""
        if event.button() == Qt.MouseButton.LeftButton:
            dialog = VersionInfoDialog(self.version_info, self)
            dialog.exec()
        super().mousePressEvent(event)
```

with exactly this:

```python
    def _show_version_info(self) -> None:
        """Show the version information dialog."""
        VersionInfoDialog(self.version_info, self).exec()
```

- [ ] **Step 5: Add `interactive` to the theme import**

In the same file, replace this block:

```python
from opaque.view.theme import (
    TypeScale,
    muted_on_surface,
    outline,
    surface_variant,
)
```

with exactly this:

```python
from opaque.view.theme import (
    TypeScale,
    interactive,
    muted_on_surface,
    outline,
    surface_variant,
)
```

- [ ] **Step 6: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_version_dialogs.py -q
```

Expected: PASS. `9 passed`.

If the run reports `NameError: name 'QPushButton' is not defined`, add `QPushButton` to the `from PySide6.QtWidgets import ...` line at the top of the file.

- [ ] **Step 7: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `218 passed`.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/dialogs/version_info.py tests/view/test_version_dialogs.py
git commit -m "fix(a11y): make the version status control a real focusable button"
```

---

### Task 4: One sweep test for every shipped widget (C9, C8)

Plans 03 to 08 raised each hit target one widget at a time. Nothing stops the next widget from shipping a 16 pixel button. This task adds one test that builds every widget the framework ships and checks all of them.

**Files:**
- Create: `tests/view/test_accessibility_sweep.py`

The test lives under `tests/view/`, not under `tests/`, because it uses the `make_notification` fixture from `tests/view/conftest.py`.

- [ ] **Step 1: Write the failing test**

Create `tests/view/test_accessibility_sweep.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""
One sweep over every widget the framework ships.

Each earlier plan raised the hit targets of one widget. This file stops the
next widget from shipping a target that is too small, or a control that a
screen reader cannot name.
"""

from PySide6.QtWidgets import QAbstractButton, QLineEdit, QTabBar, QWidget

from opaque.view.dialogs.keyboard_map import KeyboardMapDialog
from opaque.view.dialogs.version_info import (
    AboutDialog,
    VersionInfoDialog,
    VersionStatusWidget,
)
from opaque.view.widgets.closeable_tab_widget import CloseableTabWidget
from opaque.view.widgets.color_picker import ColorPicker
from opaque.view.widgets.console_widget import ConsoleWidget
from opaque.view.widgets.notification_widget import (
    NotificationListItem,
    SimplifiedNotificationList,
    ToastWidget,
)

# The smallest square a pointer can hit reliably.
MINIMUM_TARGET = 24


def _every_widget(qtbot, make_notification):
    """Build one of each widget the framework ships. Returns name and widget."""
    notification = make_notification()

    widgets = [
        ("ConsoleWidget", ConsoleWidget()),
        ("ColorPicker", ColorPicker("#336699")),
        ("SimplifiedNotificationList", SimplifiedNotificationList()),
        ("NotificationListItem", NotificationListItem(notification)),
        ("ToastWidget", ToastWidget(notification)),
        ("CloseableTabWidget", CloseableTabWidget(widget_type=QWidget)),
        ("AboutDialog", AboutDialog()),
        ("VersionInfoDialog", VersionInfoDialog()),
        ("VersionStatusWidget", VersionStatusWidget({"version": "1.0"})),
        ("KeyboardMapDialog", KeyboardMapDialog(QWidget())),
    ]

    for _name, widget in widgets:
        qtbot.addWidget(widget)
    return widgets


def _is_a_tab_bar_button(button) -> bool:
    """A tab close button is sized by the platform style, not by this code."""
    return isinstance(button.parent(), QTabBar)


def _has_a_readable_label(button) -> bool:
    """
    Return True when a screen reader can announce this button.

    A label of two or more characters with at least one letter or digit is
    enough. A symbol such as "x" or "..." is not, so those buttons must carry
    an accessible name.
    """
    text = button.text().replace("&", "").strip()
    if len(text) >= 2 and any(character.isalnum() for character in text):
        return True
    return bool(button.accessibleName().strip())


def test_no_button_is_capped_below_the_minimum_target(
        qtbot, light_palette_app, make_notification):
    offenders = []
    for name, widget in _every_widget(qtbot, make_notification):
        for button in widget.findChildren(QAbstractButton):
            if _is_a_tab_bar_button(button):
                continue
            cap = button.maximumSize()
            if cap.width() < MINIMUM_TARGET or cap.height() < MINIMUM_TARGET:
                label = button.text() or button.accessibleName() or "unnamed"
                offenders.append(
                    f"{name}: '{label}' capped at "
                    f"{cap.width()}x{cap.height()}"
                )
    assert offenders == []


def test_every_button_can_be_announced(
        qtbot, light_palette_app, make_notification):
    offenders = []
    for name, widget in _every_widget(qtbot, make_notification):
        for button in widget.findChildren(QAbstractButton):
            if _is_a_tab_bar_button(button):
                continue
            if not _has_a_readable_label(button):
                offenders.append(f"{name}: '{button.text()}'")
    assert offenders == []


def test_every_text_box_has_an_accessible_name(
        qtbot, light_palette_app, make_notification):
    offenders = []
    for name, widget in _every_widget(qtbot, make_notification):
        for box in widget.findChildren(QLineEdit):
            if not box.accessibleName().strip():
                offenders.append(f"{name}: a QLineEdit with no name")
    assert offenders == []
```

- [ ] **Step 2: Run the test**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_accessibility_sweep.py -q
```

Expected: PASS. `3 passed`.

This is the one task in the plan set where the test is expected to pass at once. It records what Plans 03 to 08 already achieved, so that it cannot be lost again.

If it fails, the failure message names the widget and the control. Fix that control in the file that owns it, using the same pattern the earlier plans used: `setFixedSize(24, 24)` or larger, and `setAccessibleName(self.tr("..."))`. Do not weaken the test.

- [ ] **Step 3: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `221 passed`.

- [ ] **Step 4: Commit**

```bash
git add tests/view/test_accessibility_sweep.py
git commit -m "test(a11y): sweep every shipped widget for target size and accessible names"
```

---

## Definition of done

- [ ] `venv\Scripts\python.exe -m pytest tests/view/test_accessibility_sweep.py -q` prints `3 passed`.
- [ ] `venv\Scripts\python.exe -m pytest -q` reports zero failures.
- [ ] `grep -n "class VersionStatusWidget(QLabel)" src/opaque/view/dialogs/version_info.py` returns no output.
- [ ] In the example application: press F1. A window lists every shortcut, including the File menu keys and the console keys. Press Escape and it closes.
- [ ] In the example application: press Tab repeatedly from the toolbar. Every control takes the focus in reading order and the focus is visible at every step.

## Left for another plan

- The remaining `self.tr(...)` work is Plan 10. The keyboard map dialog built here already uses `tr` for every string it shows.
- Right to left mirroring is Plan 10 Task 4.
