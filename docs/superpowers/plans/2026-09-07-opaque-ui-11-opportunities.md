# Plan 11 — Opportunities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the five improvement findings from the audit, and finish the `print()` sweep that Plan 08 left for the service layer.

**Architecture:** Every task here is small and stands on its own. None of them repairs a defect; each adds something the framework is missing. Run them in any order.

**Tech Stack:** PySide6, pytest, pytest-qt.

Read **Rules for the executing agent** in `2026-09-07-opaque-ui-00-index.md` before you start.

**Depends on:** Plan 01 to Plan 10.

**About the totals:** the `pytest -q` totals assume Plan 01 to Plan 10 are merged.

---

## Findings closed by this plan

| ID | Finding | Task |
|---|---|---|
| O8 | `FlowLayout.minimumSize` uses the top margin for both axes | 1 |
| O3 | Expose the `QMdiArea` tabbed view mode | 2 |
| O6 | Group and filter the notification centre | 3 |
| O7 | Shared busy state primitive | 4 |
| O5 | Debug build interface self check | 5 |
| W17 | `print()` in the service layer (the part Plan 08 left) | 6 |

---

## File Structure

| Path | Responsibility |
|---|---|
| Modify `src/opaque/view/layouts/flow.py` | Use the right margin for each axis. |
| Modify `src/opaque/view/widgets/mdi_window.py` | A tabbed and a sub window view mode. |
| Modify `src/opaque/view/application.py` | A View menu that switches the mode. |
| Modify `src/opaque/view/widgets/notification_widget.py` | A level filter in the notification dock. |
| Create `src/opaque/view/widgets/busy.py` | `BusyOverlay`, the one busy state the framework offers. |
| Create `src/opaque/view/self_check.py` | The debug build interface self check. |
| Modify `src/opaque/services/*.py`, `src/opaque/models/console_model.py` | Logging instead of `print`. |
| Create `tests/view/test_flow_layout.py`, `tests/view/test_busy.py`, `tests/view/test_self_check.py` | Tests. |

---

### Task 1: The flow layout must use the right margin for each axis (O8)

`minimumSize` adds `2 * contentsMargins().top()` to **both** the width and the height. A layout with a left margin different from its top margin reports a width that is wrong.

**Files:**
- Modify: `src/opaque/view/layouts/flow.py`
- Test: `tests/view/test_flow_layout.py`

- [ ] **Step 1: Write the failing test**

Create `tests/view/test_flow_layout.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the flow layout."""

from PySide6.QtWidgets import QLabel, QWidget

from opaque.view.layouts.flow import FlowLayout


def _flow(qtbot, left, top, right, bottom):
    """Build a flow layout holding one label, with the given margins."""
    container = QWidget()
    qtbot.addWidget(container)
    layout = FlowLayout(container)
    layout.setContentsMargins(left, top, right, bottom)
    layout.addWidget(QLabel("item"))
    return layout


def test_the_width_uses_the_horizontal_margins(qtbot, light_palette_app):
    wide = _flow(qtbot, 40, 4, 40, 4)
    narrow = _flow(qtbot, 4, 4, 4, 4)
    assert wide.minimumSize().width() > narrow.minimumSize().width()


def test_the_height_uses_the_vertical_margins(qtbot, light_palette_app):
    tall = _flow(qtbot, 4, 40, 4, 40)
    short = _flow(qtbot, 4, 4, 4, 4)
    assert tall.minimumSize().height() > short.minimumSize().height()


def test_a_wide_margin_does_not_change_the_height(qtbot, light_palette_app):
    wide = _flow(qtbot, 40, 4, 40, 4)
    narrow = _flow(qtbot, 4, 4, 4, 4)
    assert wide.minimumSize().height() == narrow.minimumSize().height()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_flow_layout.py -q
```

Expected: FAIL. `test_the_width_uses_the_horizontal_margins` fails, because the width is built from the top margin.

- [ ] **Step 3: Write the implementation**

In `src/opaque/view/layouts/flow.py`, replace this block:

```python
        size += QSize(
            2 * self.contentsMargins().top(), 2 * self.contentsMargins().top()
        )
        return size
```

with exactly this:

```python
        # The width takes the left and the right margin. The height takes the
        # top and the bottom margin. The old code used the top margin for
        # both, so a layout with different margins reported a wrong width.
        margins = self.contentsMargins()
        size += QSize(
            margins.left() + margins.right(),
            margins.top() + margins.bottom(),
        )
        return size
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_flow_layout.py -q
```

Expected: PASS. `3 passed`.

- [ ] **Step 5: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `236 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/layouts/flow.py tests/view/test_flow_layout.py
git commit -m "fix(layout): use the horizontal margins for the width in FlowLayout"
```

---

### Task 2: Offer the tabbed MDI view mode (O3)

`QMdiArea` can show its windows as tabs instead of as floating windows. Many users prefer tabs on a small screen, and the framework never offers the choice. The toolbar already has Cascade and Tiled, which only make sense in the sub window mode.

**Files:**
- Modify: `src/opaque/view/widgets/mdi_window.py`
- Modify: `src/opaque/view/application.py`
- Test: `tests/test_application_shell.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/test_application_shell.py`:

```python
def test_the_mdi_area_starts_in_the_sub_window_mode(app_window):
    assert not app_window.mdi_area.is_tabbed()


def test_the_mdi_area_can_switch_to_tabs(app_window):
    app_window.mdi_area.set_tabbed(True)
    assert app_window.mdi_area.is_tabbed()
    app_window.mdi_area.set_tabbed(False)
    assert not app_window.mdi_area.is_tabbed()


def test_the_view_menu_offers_the_tabbed_mode(app_window):
    labels = [
        action.text().replace("&", "")
        for action in app_window.view_menu.actions()
        if not action.isSeparator()
    ]
    assert "Tabbed Windows" in labels


def test_the_tabbed_action_is_checkable_and_follows_the_area(app_window):
    action = next(
        action for action in app_window.view_menu.actions()
        if action.text().replace("&", "") == "Tabbed Windows"
    )
    assert action.isCheckable()

    action.setChecked(True)
    assert app_window.mdi_area.is_tabbed()

    action.setChecked(False)
    assert not app_window.mdi_area.is_tabbed()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: FAIL. The output contains `AttributeError: 'OpaqueMdiArea' object has no attribute 'is_tabbed'`.

- [ ] **Step 3: Add the two view modes**

In `src/opaque/view/widgets/mdi_window.py`, replace this block:

```python
class OpaqueMdiArea(QMdiArea):
    """A MDI area that emits a signal when the active subwindow changes."""

    subWindowActivated = Signal(QMdiSubWindow)
```

with exactly this:

```python
class OpaqueMdiArea(QMdiArea):
    """A MDI area that emits a signal when the active subwindow changes."""

    subWindowActivated = Signal(QMdiSubWindow)

    def is_tabbed(self) -> bool:
        """Return True when the windows are shown as tabs."""
        return self.viewMode() == QMdiArea.ViewMode.TabbedView

    def set_tabbed(self, tabbed: bool) -> None:
        """
        Show the windows as tabs, or as floating sub windows.

        Tabs suit a small screen, where a floating window wastes space and
        hides the window behind it. The choice belongs to the user.
        """
        if tabbed:
            self.setViewMode(QMdiArea.ViewMode.TabbedView)
            self.setTabsClosable(False)
            self.setTabsMovable(True)
        else:
            self.setViewMode(QMdiArea.ViewMode.SubWindowView)
```

`setTabsClosable(False)` matters. A feature window that closes is only hidden, and a close button on the tab would look like it destroys the feature.

- [ ] **Step 4: Add the View menu**

In `src/opaque/view/application.py`, add this method directly below `_setup_file_menu`:

```python
    def _setup_view_menu(self) -> None:
        """Build the View menu. It carries the MDI view mode."""
        self.view_menu = self.menuBar().addMenu(self.tr("&View"))

        self.tabbed_action = QAction(self.tr("Tabbed Windows"), self)
        self.tabbed_action.setCheckable(True)
        self.tabbed_action.setChecked(False)
        self.tabbed_action.setToolTip(
            self.tr("Show the feature windows as tabs"))
        self.tabbed_action.toggled.connect(self.mdi_area.set_tabbed)
        self.view_menu.addAction(self.tabbed_action)
```

Then replace this block:

```python
        self._setup_file_menu()
        self._setup_help_menu()
```

with exactly this:

```python
        self._setup_file_menu()
        self._setup_view_menu()
        self._setup_help_menu()
```

The View menu is added between File and Help, which is the order every desktop application uses.

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: PASS. `28 passed`.

- [ ] **Step 6: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `240 passed`.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/widgets/mdi_window.py src/opaque/view/application.py tests/test_application_shell.py
git commit -m "feat(mdi): offer the tabbed view mode from a View menu"
```

---

### Task 3: Filter the notification centre by level (O6)

The dock shows every notification in one flat list, newest first. After a burst of debug messages, an error from ten minutes ago is unreachable.

**Files:**
- Modify: `src/opaque/view/widgets/notification_widget.py`
- Test: `tests/view/test_notification_list.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_notification_list.py`:

```python
def test_a_new_list_shows_every_level(qtbot, light_palette_app, fake_service):
    widget = SimplifiedNotificationList()
    qtbot.addWidget(widget)
    assert widget.level_filter() is None


def test_filtering_hides_the_other_levels(
        qtbot, light_palette_app, fake_service, make_notification):
    widget = SimplifiedNotificationList()
    qtbot.addWidget(widget)
    widget.add_notification(make_notification(NotificationLevel.ERROR))
    widget.add_notification(make_notification(NotificationLevel.DEBUG))

    widget.set_level_filter(NotificationLevel.ERROR)

    visible = [
        item for item in widget.items.values() if item.isVisibleTo(widget)
    ]
    assert len(visible) == 1
    assert visible[0].notification.level is NotificationLevel.ERROR


def test_clearing_the_filter_shows_everything_again(
        qtbot, light_palette_app, fake_service, make_notification):
    widget = SimplifiedNotificationList()
    qtbot.addWidget(widget)
    widget.add_notification(make_notification(NotificationLevel.ERROR))
    widget.add_notification(make_notification(NotificationLevel.DEBUG))

    widget.set_level_filter(NotificationLevel.ERROR)
    widget.set_level_filter(None)

    visible = [
        item for item in widget.items.values() if item.isVisibleTo(widget)
    ]
    assert len(visible) == 2


def test_a_notification_added_while_filtering_obeys_the_filter(
        qtbot, light_palette_app, fake_service, make_notification):
    widget = SimplifiedNotificationList()
    qtbot.addWidget(widget)
    widget.set_level_filter(NotificationLevel.ERROR)

    widget.add_notification(make_notification(NotificationLevel.DEBUG))

    item = list(widget.items.values())[0]
    assert not item.isVisibleTo(widget)
```

Then replace this import line at the top of `tests/view/test_notification_list.py`:

```python
from opaque.services.service import ServiceLocator
```

with exactly this:

```python
from opaque.services.notification_service import NotificationLevel
from opaque.services.service import ServiceLocator
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_notification_list.py -q
```

Expected: FAIL. The output contains `AttributeError: 'SimplifiedNotificationList' object has no attribute 'level_filter'`.

- [ ] **Step 3: Add the filter box**

In `src/opaque/view/widgets/notification_widget.py`, replace this block inside `SimplifiedNotificationList._setup_ui`:

```python
        header.addStretch()

        self.clear_button = QPushButton(self.tr("Clear All"))
```

with exactly this:

```python
        header.addStretch()

        self.level_box = QComboBox()
        self.level_box.setAccessibleName(self.tr("Filter by level"))
        self.level_box.setToolTip(self.tr("Show only one notification level"))
        # The first entry carries None, which means show every level.
        self.level_box.addItem(self.tr("All levels"), None)
        for level in NotificationLevel:
            self.level_box.addItem(level.value.upper(), level)
        self.level_box.currentIndexChanged.connect(
            lambda _index: self._apply_level_filter())
        header.addWidget(self.level_box)

        self.clear_button = QPushButton(self.tr("Clear All"))
```

- [ ] **Step 4: Add the filter methods**

In the same file, add these three methods directly above `def _remove_item`:

```python
    def level_filter(self) -> Optional[NotificationLevel]:
        """Return the level the list is filtered to, or None for every level."""
        return self.level_box.currentData()

    def set_level_filter(self, level: Optional[NotificationLevel]) -> None:
        """
        Show only one level, or every level when level is None.

        Args:
            level: The level to show, or None.
        """
        index = self.level_box.findData(level)
        if index >= 0:
            self.level_box.setCurrentIndex(index)
        self._apply_level_filter()

    def _apply_level_filter(self) -> None:
        """Hide every row that does not match the chosen level."""
        wanted = self.level_filter()
        for item in self.items.values():
            item.setVisible(wanted is None or item.notification.level is wanted)
```

Then replace this line inside `add_notification`:

```python
        self._update_clear_button()
```

with exactly these two lines:

```python
        self._update_clear_button()
        self._apply_level_filter()
```

- [ ] **Step 5: Add `QComboBox` to the imports**

In the same file, add `QComboBox` to the `from PySide6.QtWidgets import (...)` list, in alphabetical position.

- [ ] **Step 6: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_notification_list.py -q
```

Expected: PASS. `8 passed`.

- [ ] **Step 7: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `244 passed`.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/widgets/notification_widget.py tests/view/test_notification_list.py
git commit -m "feat(notifications): filter the notification dock by level"
```

---

### Task 4: One busy state for the whole framework (O7)

Nothing in the framework tells the user that a long operation is running. Every feature that needs it will invent its own, and they will all look different. One primitive fixes that.

**Files:**
- Create: `src/opaque/view/widgets/busy.py`
- Test: `tests/view/test_busy.py`

- [ ] **Step 1: Write the failing test**

Create `tests/view/test_busy.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the shared busy state overlay."""

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from opaque.view.widgets.busy import BusyOverlay


def _host(qtbot):
    """Build a widget the overlay can cover."""
    host = QWidget()
    qtbot.addWidget(host)
    layout = QVBoxLayout(host)
    layout.addWidget(QLabel("content"))
    host.resize(320, 240)
    return host


def test_a_new_overlay_is_hidden(qtbot, light_palette_app):
    overlay = BusyOverlay(_host(qtbot))
    assert not overlay.isVisibleTo(overlay.parentWidget())


def test_starting_shows_the_overlay_and_the_message(qtbot, light_palette_app):
    overlay = BusyOverlay(_host(qtbot))
    overlay.start("Loading the workspace")
    assert overlay.isVisibleTo(overlay.parentWidget())
    assert overlay.message_label.text() == "Loading the workspace"


def test_stopping_hides_the_overlay(qtbot, light_palette_app):
    overlay = BusyOverlay(_host(qtbot))
    overlay.start("Working")
    overlay.stop()
    assert not overlay.isVisibleTo(overlay.parentWidget())


def test_the_overlay_reports_a_readable_state(qtbot, light_palette_app):
    overlay = BusyOverlay(_host(qtbot))
    overlay.start("Working")
    assert overlay.accessibleName() != ""
    assert "Working" in overlay.accessibleDescription()


def test_the_overlay_covers_the_whole_host(qtbot, light_palette_app):
    host = _host(qtbot)
    overlay = BusyOverlay(host)
    overlay.start("Working")
    assert overlay.size() == host.size()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_busy.py -q
```

Expected: FAIL, with `ModuleNotFoundError: No module named 'opaque.view.widgets.busy'`.

- [ ] **Step 3: Write the implementation**

Create `src/opaque/view/widgets/busy.py` with exactly this content:

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

One busy state for the whole framework.

A user must know within 400 milliseconds that the interface received the
action. An operation longer than one second must show a progress indicator.
Every feature uses this one overlay, so busy always looks the same.
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from opaque.view.theme import TypeScale, on_surface, surface_variant


class BusyOverlay(QWidget):
    """A panel that covers its parent while a long operation runs."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAccessibleName(self.tr("Busy"))
        self.setAutoFillBackground(True)
        self.setStyleSheet(
            f"BusyOverlay {{ background-color: {surface_variant()}; }}")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.message_label = QLabel("", self)
        self.message_label.setFont(TypeScale.body())
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet(f"color: {on_surface()};")
        layout.addWidget(self.message_label)

        # A busy bar, not a percentage. The framework cannot know how long an
        # arbitrary feature operation takes, and a false percentage is worse
        # than none.
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setMaximumWidth(240)
        self.progress.setAccessibleName(self.tr("Work in progress"))
        layout.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignCenter)

        self.hide()

    def start(self, message: str) -> None:
        """
        Cover the parent and say what is happening.

        Args:
            message: What the user is waiting for. Call tr() on the literal
                before you pass it here.
        """
        self.message_label.setText(message)
        self.setAccessibleDescription(message)
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
        self.raise_()
        self.show()

    def stop(self) -> None:
        """Uncover the parent."""
        self.hide()
        self.setAccessibleDescription("")

    def resizeEvent(self, event) -> None:
        """Keep covering the whole parent when it changes size."""
        super().resizeEvent(event)
        parent = self.parentWidget()
        if parent is not None and self.isVisible():
            self.setGeometry(parent.rect())
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_busy.py -q
```

Expected: PASS. `5 passed`.

- [ ] **Step 5: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `249 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/widgets/busy.py tests/view/test_busy.py
git commit -m "feat(ui): add one shared busy overlay for long operations"
```

---

### Task 5: A debug build interface self check (O5)

The sweep test in Plan 09 only sees the widgets the framework itself ships. An application built on the framework can still put a 16 pixel button on the screen. This task gives that application the same check, at run time, in a debug build.

**Files:**
- Create: `src/opaque/view/self_check.py`
- Test: `tests/view/test_self_check.py`

- [ ] **Step 1: Write the failing test**

Create `tests/view/test_self_check.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the debug build interface self check."""

from PySide6.QtWidgets import QLineEdit, QPushButton, QVBoxLayout, QWidget

from opaque.view.self_check import MINIMUM_TARGET, check_interface


def _host(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    QVBoxLayout(host)
    return host


def test_a_clean_widget_reports_nothing(qtbot, light_palette_app):
    host = _host(qtbot)
    button = QPushButton("Save", host)
    host.layout().addWidget(button)
    assert check_interface(host) == []


def test_a_small_button_is_reported(qtbot, light_palette_app):
    host = _host(qtbot)
    button = QPushButton("x", host)
    button.setFixedSize(16, 16)
    button.setAccessibleName("Close")
    host.layout().addWidget(button)

    problems = check_interface(host)

    assert len(problems) == 1
    assert str(MINIMUM_TARGET) in problems[0]


def test_a_button_with_no_readable_label_is_reported(
        qtbot, light_palette_app):
    host = _host(qtbot)
    button = QPushButton("...", host)
    host.layout().addWidget(button)

    problems = check_interface(host)

    assert len(problems) == 1
    assert "name" in problems[0].lower()


def test_a_text_box_with_no_name_is_reported(qtbot, light_palette_app):
    host = _host(qtbot)
    host.layout().addWidget(QLineEdit(host))
    assert len(check_interface(host)) == 1


def test_every_problem_names_the_widget_class(qtbot, light_palette_app):
    host = _host(qtbot)
    host.layout().addWidget(QLineEdit(host))
    assert "QLineEdit" in check_interface(host)[0]
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_self_check.py -q
```

Expected: FAIL, with `ModuleNotFoundError: No module named 'opaque.view.self_check'`.

- [ ] **Step 3: Write the implementation**

Create `src/opaque/view/self_check.py` with exactly this content:

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

A run time interface self check for a debug build.

The test suite checks the widgets the framework ships. An application built on
the framework can still put a target that is too small, or a control a screen
reader cannot name, on the screen. Call check_interface on a window in a debug
build and read the report.
"""

import logging
from typing import List

from PySide6.QtWidgets import QAbstractButton, QLineEdit, QTabBar, QWidget

logger = logging.getLogger(__name__)

# The smallest square a pointer can hit reliably.
MINIMUM_TARGET = 24


def _describe(widget: QWidget) -> str:
    """Return a name a developer can find in the source."""
    name = widget.objectName()
    if name:
        return f"{type(widget).__name__}('{name}')"
    return type(widget).__name__


def _has_a_readable_label(button: QAbstractButton) -> bool:
    """True when a screen reader can announce this button."""
    text = button.text().replace("&", "").strip()
    if len(text) >= 2 and any(character.isalnum() for character in text):
        return True
    return bool(button.accessibleName().strip())


def check_interface(root: QWidget) -> List[str]:
    """
    Walk a widget tree and report every accessibility problem found.

    Args:
        root: The window or panel to check. Every child is checked too.

    Returns:
        One plain sentence for each problem. An empty list means the tree is
        clean. Nothing is raised and nothing is changed.
    """
    problems: List[str] = []

    for button in root.findChildren(QAbstractButton):
        if isinstance(button.parent(), QTabBar):
            continue

        cap = button.maximumSize()
        if cap.width() < MINIMUM_TARGET or cap.height() < MINIMUM_TARGET:
            problems.append(
                f"{_describe(button)} is capped at "
                f"{cap.width()}x{cap.height()}, below the {MINIMUM_TARGET} "
                f"pixel minimum target."
            )

        if not _has_a_readable_label(button):
            problems.append(
                f"{_describe(button)} has no readable label. "
                f"Call setAccessibleName()."
            )

    for box in root.findChildren(QLineEdit):
        if not box.accessibleName().strip():
            problems.append(
                f"{_describe(box)} has no accessible name. "
                f"Call setAccessibleName()."
            )

    return problems


def log_interface_problems(root: QWidget) -> int:
    """
    Run check_interface and write every problem to the log.

    Args:
        root: The window to check.

    Returns:
        How many problems were found.
    """
    problems = check_interface(root)
    for problem in problems:
        logger.warning("Interface self check: %s", problem)
    return len(problems)
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_self_check.py -q
```

Expected: PASS. `5 passed`.

- [ ] **Step 5: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `254 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/self_check.py tests/view/test_self_check.py
git commit -m "feat(a11y): add a run time interface self check for a debug build"
```

---

### Task 6: Finish the `print` sweep in the service layer (W17)

Plan 08 replaced `print` in the interface layer and left the service layer. Finish it.

**Files:**
- Modify: `src/opaque/services/settings_service.py`
- Modify: `src/opaque/services/single_instance_service.py`
- Modify: `src/opaque/services/theme_service.py`
- Modify: `src/opaque/services/workspace_service.py`
- Modify: `src/opaque/models/console_model.py`
- Test: `tests/test_application_shell.py`

`src/opaque/build_tools/`, `src/opaque/services/console_service.py` and `src/opaque/services/logger_service.py` stay out of scope, for the same reasons Plan 08 gave: the build tools are command line programs, and the other two are the machinery that captures and writes the output.

- [ ] **Step 1: Write the failing test**

In `tests/test_application_shell.py`, replace this block:

```python
_UI_MODULES = [
    "src/opaque/view/application.py",
    "src/opaque/presenters/presenter.py",
    "src/opaque/presenters/notification_presenter.py",
    "src/opaque/presenters/console_presenter.py",
    "src/opaque/view/widgets/closeable_tab_widget.py",
]
```

with exactly this:

```python
_UI_MODULES = [
    "src/opaque/view/application.py",
    "src/opaque/presenters/presenter.py",
    "src/opaque/presenters/notification_presenter.py",
    "src/opaque/presenters/console_presenter.py",
    "src/opaque/view/widgets/closeable_tab_widget.py",
    "src/opaque/services/settings_service.py",
    "src/opaque/services/single_instance_service.py",
    "src/opaque/services/theme_service.py",
    "src/opaque/services/workspace_service.py",
    "src/opaque/models/console_model.py",
]
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py::test_no_ui_module_reports_an_error_with_print -q
```

Expected: FAIL. The assertion lists the file and line of every remaining `print`.

- [ ] **Step 3: Apply the same rule as Plan 08**

In each of the five files listed under **Files**, do exactly what Plan 08 Task 3 Step 3 and Step 4 described:

1. Add `import logging` at the top of the import block.
2. Add `logger = logging.getLogger(__name__)` below the last import, after one blank line.
3. Replace a `print` inside an `except` block with
   `logger.exception("<the message text, without the exception part>")`.
4. Replace a `print` anywhere else with `logger.warning("<the same text>")`.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_application_shell.py -q
```

Expected: PASS. `28 passed`.

- [ ] **Step 5: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `254 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/services src/opaque/models/console_model.py tests/test_application_shell.py
git commit -m "fix(services): report failures through logging instead of print"
```

---

## Definition of done

- [ ] `venv\Scripts\python.exe -m pytest -q` reports zero failures and at least `254 passed`.
- [ ] `grep -rn "^\s*print(" src/opaque/ | grep -v build_tools | grep -v console_service | grep -v logger_service` returns no output.
- [ ] In the example application: open the View menu and tick Tabbed Windows. The feature windows become tabs. Untick it and they float again.
- [ ] In the example application: open the notification dock, choose ERROR in the filter box, and only error rows stay on the screen.
