# Plan 05 — Notification System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the notification centre and the toast popups, so a toast lands where the user can see it, tells its level in text, dismisses itself at a speed that matches its severity, and never destroys a large list without a question.

**Architecture:** The toast geometry becomes a pure function in a new module, `opaque.view.layouts.toast_stack`. A pure function can be tested with no window on screen, so the position bug can be proven instead of eyeballed. The widgets stop writing Bootstrap hex colours and take every colour and every font from `opaque.view.theme`, built in Plan 02.

**Tech Stack:** PySide6, pytest, pytest-qt.

Read **Rules for the executing agent** in `2026-09-07-opaque-ui-00-index.md` before you start.

**Depends on:** Plan 01 and Plan 02. Do not start this plan until `venv\Scripts\python.exe -m pytest -q` reports `93 passed`.

---

## Findings closed by this plan

| ID | Finding | Task |
|---|---|---|
| C7 | Notification level uses colour as the only cue | 2 |
| C6 | Hardcoded greys fail 4.5:1 contrast | 3 |
| C9 | Hit targets 16–30 px | 3 |
| W1 | Toast position uses widget-local coordinates as global | 1, 4 |
| W4 | Toast stack has no cap | 1, 4 |
| C13a | `Clear All` destroys the list with no confirmation | 5 |
| W2 | Toast exit animation never plays, object deleted early | 6 |
| W3 | Fixed 4 s dismiss, no hover pause | 7 |
| W5 | Two startup toasts report that nothing happened | 8 |
| W7 | Notification dock steals space at startup | 8 |

---

## One decision you must not undo

`ToastWidget` sets `Qt.WidgetAttribute.WA_ShowWithoutActivating`. **Keep it.** Without it, every notification steals keyboard focus from the window the user is typing in. That is worse than the problem it would solve.

The keyboard path to a notification is the notification dock, not the toast. Task 6 still adds an Escape key handler to the toast, for the case where the user has clicked the toast and it holds focus. Do not remove `WA_ShowWithoutActivating` to make Escape easier to test.

---

## File Structure

| Path | Responsibility |
|---|---|
| Create `src/opaque/view/layouts/toast_stack.py` | Pure geometry. `stacked_toast_positions`, `overflow_count`, `toast_anchor`. No widget state, no service, no signal. |
| Modify `src/opaque/view/widgets/notification_widget.py` | `ToastWidget`, `NotificationListItem`, `SimplifiedNotificationList`. Colours and fonts come from `opaque.view.theme`. |
| Modify `src/opaque/presenters/notification_presenter.py` | Places the toast stack, caps it, and stops the startup toast. |
| Create `tests/view/conftest.py` | The `make_notification` factory fixture. Owned by this plan. |
| Create `tests/view/test_toast_stack.py` | Proves the geometry and the cap. |
| Create `tests/view/test_notification_widget.py` | Proves the level text, the contrast, the hit targets, the animation and the timers. |
| Create `tests/view/test_notification_list.py` | Proves the `Clear All` confirmation. |

---

### Task 1: Pure toast stack geometry

The current code reads `main_window.width()` and gives it to `toast.move()`. A toast is a top level window, so `move()` takes **global screen** coordinates while `width()` is a widget local length. The stack therefore lands near the top left corner of the screen. This task builds the maths on its own, where it can be tested.

**Files:**
- Create: `src/opaque/view/layouts/toast_stack.py`
- Create: `tests/view/conftest.py`
- Test: `tests/view/test_toast_stack.py`

- [ ] **Step 1: Write the factory fixture**

Create `tests/view/conftest.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Shared fixtures for the view tests."""

from datetime import datetime

import pytest

from opaque.services.notification_service import Notification, NotificationLevel


@pytest.fixture
def make_notification():
    """
    Return a factory that builds a Notification.

    The default is persistent. A persistent notification starts no auto close
    timer, so a test cannot leave a timer behind that fires after the widget is
    gone. A test that needs the timer must pass persistent=False.
    """
    counter = {"value": 0}

    def _make(
        level: NotificationLevel = NotificationLevel.INFO,
        title: str = "Title",
        message: str = "Message",
        persistent: bool = True,
    ) -> Notification:
        counter["value"] += 1
        return Notification(
            id=f"test-{counter['value']}",
            level=level,
            title=title,
            message=message,
            source="Test",
            timestamp=datetime(2026, 9, 7, 12, 30, 45),
            persistent=persistent,
        )

    return _make
```

- [ ] **Step 2: Write the failing test**

Create `tests/view/test_toast_stack.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the pure toast stack geometry."""

from PySide6.QtCore import QPoint, QRect, QSize

from opaque.view.layouts.toast_stack import (
    MAX_VISIBLE_TOASTS,
    overflow_count,
    stacked_toast_positions,
)

ANCHOR = QRect(0, 0, 800, 600)
TOAST = QSize(300, 80)


def test_an_empty_stack_gives_no_positions():
    assert stacked_toast_positions(ANCHOR, []) == []


def test_the_first_toast_sits_in_the_bottom_right_corner():
    positions = stacked_toast_positions(ANCHOR, [TOAST], margin=12)
    assert positions[0] == QPoint(800 - 12 - 300, 600 - 12 - 80)


def test_the_second_toast_sits_above_the_first():
    positions = stacked_toast_positions(
        ANCHOR, [TOAST, TOAST], margin=12, spacing=8)
    assert positions[1].x() == positions[0].x()
    assert positions[1].y() == positions[0].y() - 80 - 8


def test_the_stack_never_leaves_the_anchor_on_the_left():
    tiny = QRect(0, 0, 200, 400)
    positions = stacked_toast_positions(tiny, [TOAST], margin=12)
    assert positions[0].x() == 12


def test_the_stack_never_leaves_the_anchor_on_the_top():
    tiny = QRect(0, 0, 800, 60)
    positions = stacked_toast_positions(tiny, [TOAST], margin=12)
    assert positions[0].y() == 12


def test_the_anchor_offset_is_added_to_every_position():
    moved = QRect(1000, 500, 800, 600)
    positions = stacked_toast_positions(moved, [TOAST], margin=12)
    assert positions[0] == QPoint(1000 + 800 - 12 - 300, 500 + 600 - 12 - 80)


def test_no_toast_overflows_below_the_limit():
    assert overflow_count(0) == 0
    assert overflow_count(MAX_VISIBLE_TOASTS - 2) == 0


def test_one_toast_overflows_when_the_stack_is_full():
    assert overflow_count(MAX_VISIBLE_TOASTS - 1) == 0
    assert overflow_count(MAX_VISIBLE_TOASTS) == 1


def test_a_larger_backlog_overflows_by_more():
    assert overflow_count(MAX_VISIBLE_TOASTS + 3) == 4
```

- [ ] **Step 3: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_toast_stack.py -q
```

Expected: FAIL, with `ModuleNotFoundError: No module named 'opaque.view.layouts.toast_stack'`.

- [ ] **Step 4: Write the implementation**

Create `src/opaque/view/layouts/toast_stack.py` with exactly this content:

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

Pure geometry for the toast notification stack.

Every function here takes plain values and returns plain values. No function
reads widget state and no function moves a widget. The presenter does that.
This split lets the position rule be tested with no window on the screen.
"""

from typing import List

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtWidgets import QWidget

# More than four toasts at the same time cannot be read before they expire.
MAX_VISIBLE_TOASTS: int = 4

DEFAULT_MARGIN: int = 12
DEFAULT_SPACING: int = 8


def stacked_toast_positions(
    anchor: QRect,
    sizes: List[QSize],
    margin: int = DEFAULT_MARGIN,
    spacing: int = DEFAULT_SPACING,
) -> List[QPoint]:
    """
    Return the top left corner for each toast in a bottom right stack.

    Args:
        anchor: The area the stack must stay inside, in the same coordinate
            system that the caller will give to QWidget.move(). For a top level
            toast that is the global screen coordinate system.
        sizes: The size of each toast, newest first. The newest toast is the
            one closest to the bottom right corner.
        margin: The gap between the stack and the edge of the anchor.
        spacing: The gap between two toasts.

    Returns:
        One QPoint for each item in sizes, in the same order.
    """
    right_edge = anchor.x() + anchor.width() - margin
    bottom_edge = anchor.y() + anchor.height() - margin
    left_limit = anchor.x() + margin
    top_limit = anchor.y() + margin

    positions: List[QPoint] = []
    for size in sizes:
        x = max(right_edge - size.width(), left_limit)
        y = max(bottom_edge - size.height(), top_limit)
        positions.append(QPoint(x, y))
        bottom_edge = y - spacing
    return positions


def overflow_count(active: int, limit: int = MAX_VISIBLE_TOASTS) -> int:
    """
    Return how many of the oldest toasts must go before one more is added.

    Args:
        active: The number of toasts on the screen now.
        limit: The largest number of toasts allowed on the screen.

    Returns:
        Zero when there is room. A positive count when the oldest toasts must
        be removed first.
    """
    return max(0, active + 1 - limit)


def toast_anchor(window: QWidget) -> QRect:
    """
    Return the area the toast stack must stay inside, in global coordinates.

    A toast is a top level window, so QWidget.move() takes global screen
    coordinates. The width and the height of the main window are widget local
    lengths and must never be used as coordinates.

    Args:
        window: The main window the stack belongs to.

    Returns:
        The main window rectangle in global coordinates, clipped to the
        available area of the screen it is on.
    """
    area = QRect(window.mapToGlobal(QPoint(0, 0)), window.size())
    screen = window.screen()
    if screen is not None:
        clipped = area.intersected(screen.availableGeometry())
        if not clipped.isEmpty():
            return clipped
    return area
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_toast_stack.py -q
```

Expected: PASS. `9 passed`.

- [ ] **Step 6: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `102 passed`.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/layouts/toast_stack.py tests/view/conftest.py tests/view/test_toast_stack.py
git commit -m "feat(notifications): add pure toast stack geometry with a visible limit"
```

---

### Task 2: The notification level must be readable as text (C7)

Today the level is carried by an 8 by 8 pixel coloured dot in the list, and by four Bootstrap hex colours in the toast. A user with a colour vision deficiency reads none of it. This task writes the level as text and takes every colour from the status token table.

**Files:**
- Modify: `src/opaque/view/widgets/notification_widget.py`
- Test: `tests/view/test_notification_widget.py`

- [ ] **Step 1: Write the failing test**

Create `tests/view/test_notification_widget.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the toast widget and the notification list item."""

from opaque.services.notification_service import NotificationLevel
from opaque.view.theme import StatusRole, status_colors
from opaque.view.widgets.notification_widget import (
    NotificationListItem,
    ToastWidget,
    status_role_for_level,
)


def test_each_level_maps_to_a_status_role():
    assert status_role_for_level(NotificationLevel.DEBUG) is StatusRole.NEUTRAL
    assert status_role_for_level(NotificationLevel.INFO) is StatusRole.INFO
    assert status_role_for_level(NotificationLevel.WARNING) is StatusRole.WARNING


def test_critical_and_error_share_the_error_role():
    assert status_role_for_level(NotificationLevel.ERROR) is StatusRole.ERROR
    assert status_role_for_level(NotificationLevel.CRITICAL) is StatusRole.ERROR


def test_the_toast_does_not_use_a_bootstrap_colour(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification(NotificationLevel.ERROR))
    qtbot.addWidget(toast)
    sheet = toast.container.styleSheet()
    assert "#dc3545" not in sheet
    assert "#ffc107" not in sheet
    assert "#0dcaf0" not in sheet
    assert "#6c757d" not in sheet


def test_the_toast_uses_the_status_background(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification(NotificationLevel.ERROR))
    qtbot.addWidget(toast)
    expected = status_colors(StatusRole.ERROR).background
    assert expected in toast.container.styleSheet()


def test_the_list_item_shows_the_level_as_text(
        qtbot, light_palette_app, make_notification):
    item = NotificationListItem(make_notification(NotificationLevel.WARNING))
    qtbot.addWidget(item)
    assert item.level_label.text() == "WARNING"


def test_the_list_item_level_text_follows_the_level(
        qtbot, light_palette_app, make_notification):
    for level in NotificationLevel:
        item = NotificationListItem(make_notification(level))
        qtbot.addWidget(item)
        assert item.level_label.text() == level.value.upper()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_notification_widget.py -q
```

Expected: FAIL, with `ImportError: cannot import name 'status_role_for_level'`.

- [ ] **Step 3: Replace the import block**

In `src/opaque/view/widgets/notification_widget.py`, replace this block:

```python
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QPoint, QSize, QRect
from PySide6.QtGui import QIcon, QFont, QColor, QPainter, QBrush, QPen

from opaque.services.service import ServiceLocator
from opaque.services.notification_service import NotificationService, Notification, NotificationLevel
```

with exactly this:

```python
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation

from opaque.services.service import ServiceLocator
from opaque.services.notification_service import NotificationService, Notification, NotificationLevel
from opaque.view.theme import (
    StatusColors,
    StatusRole,
    TypeScale,
    muted_on_surface,
    status_colors,
)


# A notification level says how bad the news is. A status role says how the
# interface must show it. Two levels can share one role.
_STATUS_BY_LEVEL = {
    NotificationLevel.DEBUG: StatusRole.NEUTRAL,
    NotificationLevel.INFO: StatusRole.INFO,
    NotificationLevel.WARNING: StatusRole.WARNING,
    NotificationLevel.ERROR: StatusRole.ERROR,
    NotificationLevel.CRITICAL: StatusRole.ERROR,
}


def status_role_for_level(level: NotificationLevel) -> StatusRole:
    """Return the status role that shows this notification level."""
    return _STATUS_BY_LEVEL.get(level, StatusRole.NEUTRAL)
```

`QIcon`, `QColor`, `QPainter`, `QBrush`, `QPen`, `QPoint`, `QSize` and `QRect` were imported and never used. `QFont` is replaced by `TypeScale`.

- [ ] **Step 4: Replace the toast colour methods**

In the same file, replace this block:

```python
    def _get_level_colors(self):
        level = self.notification.level
        if level == NotificationLevel.ERROR or level == NotificationLevel.CRITICAL:
            return {"bg": "#dc3545", "text": "white", "border": "#bd2130"}
        elif level == NotificationLevel.WARNING:
            return {"bg": "#ffc107", "text": "black", "border": "#d39e00"}
        elif level == NotificationLevel.INFO:
            return {"bg": "#0dcaf0", "text": "black", "border": "#0aa2c0"}
        else: # DEBUG
            return {"bg": "#6c757d", "text": "white", "border": "#545b62"}

    def _get_stylesheet(self):
        colors = self._get_level_colors()
        return f"""
            QFrame#ToastContainer {{
                background-color: {colors['bg']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
            }}
        """
```

with exactly this:

```python
    def _get_level_colors(self) -> StatusColors:
        """Return the status colour triple for this notification level."""
        return status_colors(status_role_for_level(self.notification.level))

    def _get_stylesheet(self) -> str:
        """Return the container style sheet for this notification level."""
        colors = self._get_level_colors()
        return f"""
            QFrame#ToastContainer {{
                background-color: {colors.background};
                border: 1px solid {colors.border};
                border-radius: 4px;
            }}
        """
```

- [ ] **Step 5: Replace the toast body**

In the same file, replace this block:

```python
        # Title row
        title_layout = QHBoxLayout()
        level_label = QLabel(self.notification.level.value.upper())
        level_label.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        # Set level color
        colors = self._get_level_colors()
        level_label.setStyleSheet(f"color: {colors['text']};")
        
        title_label = QLabel(self.notification.title)
        title_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {colors['text']};")
        
        title_layout.addWidget(level_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setFlat(True)
        close_btn.setStyleSheet(f"color: {colors['text']}; font-weight: bold;")
        close_btn.clicked.connect(self.close_toast)
        title_layout.addWidget(close_btn)
        
        container_layout.addLayout(title_layout)
        
        # Message
        msg_label = QLabel(self.notification.message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"color: {colors['text']};")
        container_layout.addWidget(msg_label)
```

with exactly this:

```python
        colors = self._get_level_colors()

        title_layout = QHBoxLayout()

        self.level_label = QLabel(self.notification.level.value.upper())
        self.level_label.setFont(TypeScale.emphasis(TypeScale.caption()))
        self.level_label.setStyleSheet(f"color: {colors.foreground};")

        self.title_label = QLabel(self.notification.title)
        self.title_label.setFont(TypeScale.emphasis(TypeScale.body()))
        self.title_label.setStyleSheet(f"color: {colors.foreground};")

        title_layout.addWidget(self.level_label)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(20, 20)
        self.close_button.setFlat(True)
        self.close_button.setStyleSheet(
            f"color: {colors.foreground}; font-weight: bold;")
        self.close_button.clicked.connect(self.close_toast)
        title_layout.addWidget(self.close_button)

        container_layout.addLayout(title_layout)

        self.message_label = QLabel(self.notification.message)
        self.message_label.setWordWrap(True)
        self.message_label.setFont(TypeScale.body())
        self.message_label.setStyleSheet(f"color: {colors.foreground};")
        container_layout.addWidget(self.message_label)
```

- [ ] **Step 6: Replace the whole `NotificationListItem` class**

In the same file, replace the whole `NotificationListItem` class, from the line `class NotificationListItem(QFrame):` down to and including the last line of its `_get_color` method, with exactly this:

```python
class NotificationListItem(QFrame):
    """One notification row inside the notification dock."""

    removed = Signal(str)

    def __init__(self, notification: Notification, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.notification = notification
        self.status = status_colors(status_role_for_level(notification.level))
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()

        # The level is written as text, not only painted as a colour. Colour
        # alone is not readable for a user with a colour vision deficiency.
        self.level_label = QLabel(self.notification.level.value.upper())
        self.level_label.setFont(TypeScale.emphasis(TypeScale.caption()))
        self.level_label.setStyleSheet(
            f"color: {self.status.foreground};"
            f"background-color: {self.status.background};"
            f"border-radius: 3px; padding: 1px 5px;"
        )
        header.addWidget(self.level_label)

        self.title_label = QLabel(self.notification.title)
        self.title_label.setFont(TypeScale.emphasis(TypeScale.body()))
        header.addWidget(self.title_label)

        header.addStretch()

        self.time_label = QLabel(
            self.notification.timestamp.strftime("%H:%M:%S"))
        self.time_label.setStyleSheet("color: gray; font-size: 10px;")
        header.addWidget(self.time_label)

        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(16, 16)
        self.close_button.setFlat(True)
        self.close_button.clicked.connect(
            lambda: self.removed.emit(self.notification.id))
        header.addWidget(self.close_button)

        layout.addLayout(header)

        self.message_label = QLabel(self.notification.message)
        self.message_label.setWordWrap(True)
        self.message_label.setFont(TypeScale.body())
        layout.addWidget(self.message_label)

        self.setStyleSheet("""
            NotificationListItem {
                background-color: transparent;
                border-bottom: 1px solid palette(mid);
            }
        """)
```

The grey timestamp and the 16 pixel close button stay for now. Task 3 removes them.

- [ ] **Step 7: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_notification_widget.py -q
```

Expected: PASS. `6 passed`.

- [ ] **Step 8: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `108 passed`.

- [ ] **Step 9: Commit**

```bash
git add src/opaque/view/widgets/notification_widget.py tests/view/test_notification_widget.py
git commit -m "fix(notifications): show the level as text and take colours from the status tokens"
```

---

### Task 3: Readable secondary text and usable hit targets (C6, C9)

`color: gray; font-size: 10px` gives 3.9:1 on a white surface and 3.3:1 on a dark surface. Both fail the WCAG 4.5:1 text minimum. The two close buttons are 16 and 20 pixels, below any usable target size.

**Files:**
- Modify: `src/opaque/view/widgets/notification_widget.py`
- Test: `tests/view/test_notification_widget.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_notification_widget.py`:

```python
def test_the_timestamp_is_not_a_grey_literal(
        qtbot, light_palette_app, make_notification):
    item = NotificationListItem(make_notification())
    qtbot.addWidget(item)
    sheet = item.time_label.styleSheet()
    assert "gray" not in sheet
    assert "font-size" not in sheet


def test_the_timestamp_passes_contrast_on_a_light_surface(
        qtbot, light_palette_app, make_notification):
    item = NotificationListItem(make_notification())
    qtbot.addWidget(item)
    ratio = contrast_ratio(item.timestamp_colour, surface())
    assert ratio >= TEXT_CONTRAST_MINIMUM


def test_the_timestamp_passes_contrast_on_a_dark_surface(
        qtbot, dark_palette_app, make_notification):
    item = NotificationListItem(make_notification())
    qtbot.addWidget(item)
    ratio = contrast_ratio(item.timestamp_colour, surface())
    assert ratio >= TEXT_CONTRAST_MINIMUM


def test_the_list_item_close_button_is_large_enough(
        qtbot, light_palette_app, make_notification):
    item = NotificationListItem(make_notification())
    qtbot.addWidget(item)
    assert item.close_button.width() >= NotificationListItem.CLOSE_BUTTON_SIZE
    assert NotificationListItem.CLOSE_BUTTON_SIZE >= 24


def test_the_toast_close_button_is_large_enough(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification())
    qtbot.addWidget(toast)
    assert toast.close_button.width() >= 24
    assert toast.close_button.height() >= 24


def test_both_close_buttons_have_an_accessible_name(
        qtbot, light_palette_app, make_notification):
    item = NotificationListItem(make_notification())
    qtbot.addWidget(item)
    toast = ToastWidget(make_notification())
    qtbot.addWidget(toast)
    assert item.close_button.accessibleName() != ""
    assert toast.close_button.accessibleName() != ""
```

Then add these two imports at the top of `tests/view/test_notification_widget.py`, below the existing `from opaque.services...` line:

```python
from opaque.view.theme import contrast_ratio, surface
from opaque.view.theme.contrast import TEXT_CONTRAST_MINIMUM
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_notification_widget.py -q
```

Expected: FAIL. The output contains `AttributeError: 'NotificationListItem' object has no attribute 'timestamp_colour'`.

- [ ] **Step 3: Fix the list item timestamp and close button**

In `src/opaque/view/widgets/notification_widget.py`, add this line directly below `removed = Signal(str)` in `NotificationListItem`:

```python

    # 24 pixels is the smallest close target that a pointer can hit reliably.
    CLOSE_BUTTON_SIZE = 24
```

Then replace this block inside `NotificationListItem._setup_ui`:

```python
        self.time_label = QLabel(
            self.notification.timestamp.strftime("%H:%M:%S"))
        self.time_label.setStyleSheet("color: gray; font-size: 10px;")
        header.addWidget(self.time_label)

        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(16, 16)
        self.close_button.setFlat(True)
        self.close_button.clicked.connect(
            lambda: self.removed.emit(self.notification.id))
        header.addWidget(self.close_button)
```

with exactly this:

```python
        self.time_label = QLabel(
            self.notification.timestamp.strftime("%H:%M:%S"))
        self.time_label.setFont(TypeScale.caption())
        self.time_label.setStyleSheet(f"color: {self.timestamp_colour};")
        header.addWidget(self.time_label)

        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(
            self.CLOSE_BUTTON_SIZE, self.CLOSE_BUTTON_SIZE)
        self.close_button.setFlat(True)
        self.close_button.setAccessibleName(self.tr("Dismiss notification"))
        self.close_button.setToolTip(self.tr("Dismiss this notification"))
        self.close_button.clicked.connect(
            lambda: self.removed.emit(self.notification.id))
        header.addWidget(self.close_button)
```

Then replace this line in `NotificationListItem.__init__`:

```python
        self.status = status_colors(status_role_for_level(notification.level))
```

with exactly these two lines:

```python
        self.status = status_colors(status_role_for_level(notification.level))
        self.timestamp_colour = muted_on_surface()
```

- [ ] **Step 4: Fix the toast close button**

In the same file, replace this block inside `ToastWidget._setup_ui`:

```python
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(20, 20)
        self.close_button.setFlat(True)
        self.close_button.setStyleSheet(
            f"color: {colors.foreground}; font-weight: bold;")
        self.close_button.clicked.connect(self.close_toast)
```

with exactly this:

```python
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(
            self.CLOSE_BUTTON_SIZE, self.CLOSE_BUTTON_SIZE)
        self.close_button.setFlat(True)
        self.close_button.setAccessibleName(self.tr("Close notification"))
        self.close_button.setToolTip(self.tr("Close this notification"))
        self.close_button.setStyleSheet(
            f"color: {colors.foreground}; font-weight: bold;")
        self.close_button.clicked.connect(self.close_toast)
```

Then add this line directly below `closed = Signal(str)  # notification_id` in `ToastWidget`:

```python

    # 24 pixels is the smallest close target that a pointer can hit reliably.
    CLOSE_BUTTON_SIZE = 24
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_notification_widget.py -q
```

Expected: PASS. `12 passed`.

- [ ] **Step 6: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `114 passed`.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/widgets/notification_widget.py tests/view/test_notification_widget.py
git commit -m "fix(notifications): readable timestamp colour and 24 px close targets"
```

---

### Task 4: Put the toast stack where the user can see it, and cap it (W1, W4)

`_reposition_toasts` gives widget local lengths to `move()`, which expects global screen coordinates. The stack also grows without a limit, so a burst of log errors covers the window.

**Files:**
- Modify: `src/opaque/presenters/notification_presenter.py`
- Test: `tests/view/test_toast_stack.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_toast_stack.py`:

```python
def test_the_anchor_uses_global_coordinates_not_widget_coordinates(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    window.resize(320, 240)
    window.move(40, 60)
    window.show()
    qtbot.waitExposed(window)

    anchor = toast_anchor(window)
    top_left = window.mapToGlobal(QPoint(0, 0))
    bottom_right = window.mapToGlobal(QPoint(window.width(), window.height()))

    assert anchor.left() >= top_left.x()
    assert anchor.top() >= top_left.y()
    assert anchor.left() + anchor.width() <= bottom_right.x()
    assert anchor.top() + anchor.height() <= bottom_right.y()


def test_the_anchor_is_never_empty(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    window.resize(320, 240)
    window.show()
    qtbot.waitExposed(window)

    assert not toast_anchor(window).isEmpty()
```

Then replace the import block at the top of `tests/view/test_toast_stack.py`:

```python
from PySide6.QtCore import QPoint, QRect, QSize

from opaque.view.layouts.toast_stack import (
    MAX_VISIBLE_TOASTS,
    overflow_count,
    stacked_toast_positions,
)
```

with exactly this:

```python
from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtWidgets import QWidget

from opaque.view.layouts.toast_stack import (
    MAX_VISIBLE_TOASTS,
    overflow_count,
    stacked_toast_positions,
    toast_anchor,
)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_toast_stack.py -q
```

Expected: FAIL, with `ImportError: cannot import name 'toast_anchor'`.

Note: `toast_anchor` was written in Task 1. If this step passes instead of failing, Task 1 was not completed. Stop and report it.

- [ ] **Step 3: Add the import to the presenter**

In `src/opaque/presenters/notification_presenter.py`, add this block directly below the line `from opaque.services.service import ServiceLocator`:

```python
from opaque.view.layouts.toast_stack import (
    MAX_VISIBLE_TOASTS,
    overflow_count,
    stacked_toast_positions,
    toast_anchor,
)
```

- [ ] **Step 4: Replace the toast placement methods**

In the same file, replace this block:

```python
    def _show_toast(self, notification: Notification):
        if not self._main_window:
            return

        toast = ToastWidget(notification, self._main_window)
        toast.closed.connect(self._on_toast_closed)
        
        # Position logic (bottom right stack)
        self._active_toasts.append(toast)
        self._reposition_toasts()
        
        toast.show()

    def _on_toast_closed(self, notification_id: str):
        # Find and remove toast
        for toast in self._active_toasts[:]:
            if toast.notification.id == notification_id:
                self._active_toasts.remove(toast)
                toast.deleteLater()
        self._reposition_toasts()

    def _reposition_toasts(self):
        if not self._main_window: return
        
        margin = 10
        spacing = 5
        x = self._main_window.width() - margin
        y = self._main_window.height() - margin
        
        for toast in reversed(self._active_toasts):
            width = toast.sizeHint().width()
            height = toast.sizeHint().height()
            
            # Ensure proper size
            toast.adjustSize()
            width = toast.width()
            height = toast.height()
            
            toast.move(x - width, y - height)
            y -= (height + spacing)
```

with exactly this:

```python
    def _show_toast(self, notification: Notification) -> None:
        """Show one toast and keep the stack inside the visible limit."""
        if not self._main_window:
            return

        self._drop_oldest_toasts()

        toast = ToastWidget(notification, self._main_window)
        toast.closed.connect(self._on_toast_closed)
        self._active_toasts.append(toast)
        toast.show()
        self._reposition_toasts()

    def _drop_oldest_toasts(self) -> None:
        """
        Remove the oldest toasts so that one more toast still fits.

        More than MAX_VISIBLE_TOASTS toasts at the same time cannot be read
        before they expire, and they hide the window behind them.
        """
        for _ in range(overflow_count(len(self._active_toasts),
                                      MAX_VISIBLE_TOASTS)):
            oldest = self._active_toasts.pop(0)
            oldest.hide()
            oldest.deleteLater()

    def _on_toast_closed(self, notification_id: str) -> None:
        """Drop a toast that has finished its fade out, then close the gap."""
        for toast in self._active_toasts[:]:
            if toast.notification.id == notification_id:
                self._active_toasts.remove(toast)
                toast.deleteLater()
        self._reposition_toasts()

    def _reposition_toasts(self) -> None:
        """
        Place the toast stack in the bottom right corner of the main window.

        A toast is a top level window, so move() takes global screen
        coordinates. The width and the height of the main window are widget
        local lengths and must never be used as coordinates here.
        """
        if not self._main_window:
            return

        newest_first = list(reversed(self._active_toasts))
        for toast in newest_first:
            toast.adjustSize()

        sizes = [toast.size() for toast in newest_first]
        positions = stacked_toast_positions(
            toast_anchor(self._main_window), sizes)
        for toast, position in zip(newest_first, positions):
            toast.move(position)
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_toast_stack.py -q
```

Expected: PASS. `11 passed`.

- [ ] **Step 6: Prove the presenter still imports**

Run:

```
venv\Scripts\python.exe -c "from opaque.presenters.notification_presenter import NotificationPresenter; print(NotificationPresenter._reposition_toasts.__doc__.splitlines()[1].strip())"
```

Expected: the single line `Place the toast stack in the bottom right corner of the main window.`

- [ ] **Step 7: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `116 passed`.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/presenters/notification_presenter.py tests/view/test_toast_stack.py
git commit -m "fix(notifications): place toasts in global coordinates and cap the stack"
```

---

### Task 5: Ask before clearing every notification (C13a)

`Clear All` destroys the whole notification history with one click and gives no way back.

**Files:**
- Modify: `src/opaque/view/widgets/notification_widget.py`
- Test: `tests/view/test_notification_list.py`

- [ ] **Step 1: Write the failing test**

Create `tests/view/test_notification_list.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the notification list widget."""

import pytest

from opaque.services.service import ServiceLocator
from opaque.view.widgets.notification_widget import SimplifiedNotificationList


class _FakeNotificationService:
    """Records the calls the widget makes, so a test can check them."""

    def __init__(self):
        self.clear_calls = 0
        self.removed_ids = []

    def clear_notifications(self, level_filter=None):
        self.clear_calls += 1

    def remove_notification(self, notification_id):
        self.removed_ids.append(notification_id)


@pytest.fixture
def fake_service():
    """Put a recording service in the locator for the length of one test."""
    previous = ServiceLocator._services.get("notification")
    service = _FakeNotificationService()
    ServiceLocator._services["notification"] = service
    yield service
    if previous is None:
        ServiceLocator._services.pop("notification", None)
    else:
        ServiceLocator._services["notification"] = previous


def _list_with_one_item(qtbot, make_notification):
    widget = SimplifiedNotificationList()
    qtbot.addWidget(widget)
    widget.add_notification(make_notification())
    return widget


def test_clear_all_does_not_ask_when_the_list_is_empty(
        qtbot, light_palette_app, fake_service):
    widget = SimplifiedNotificationList()
    qtbot.addWidget(widget)
    asked = []
    widget._confirm_clear_all = lambda: asked.append(True) or True

    widget._clear_all()

    assert asked == []
    assert fake_service.clear_calls == 0


def test_clear_all_asks_before_removing_items(
        qtbot, light_palette_app, fake_service, make_notification):
    widget = _list_with_one_item(qtbot, make_notification)
    asked = []
    widget._confirm_clear_all = lambda: asked.append(True) or True

    widget._clear_all()

    assert asked == [True]


def test_declining_the_confirmation_leaves_the_service_untouched(
        qtbot, light_palette_app, fake_service, make_notification):
    widget = _list_with_one_item(qtbot, make_notification)
    widget._confirm_clear_all = lambda: False

    widget._clear_all()

    assert fake_service.clear_calls == 0


def test_accepting_the_confirmation_calls_the_service(
        qtbot, light_palette_app, fake_service, make_notification):
    widget = _list_with_one_item(qtbot, make_notification)
    widget._confirm_clear_all = lambda: True

    widget._clear_all()

    assert fake_service.clear_calls == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_notification_list.py -q
```

Expected: FAIL. `test_clear_all_does_not_ask_when_the_list_is_empty` and `test_declining_the_confirmation_leaves_the_service_untouched` fail on `assert fake_service.clear_calls == 0`, because the current code always calls the service.

- [ ] **Step 3: Add `QMessageBox` to the imports**

In `src/opaque/view/widgets/notification_widget.py`, replace this block:

```python
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QApplication, QGraphicsOpacityEffect
)
```

with exactly this:

```python
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QGraphicsOpacityEffect, QMessageBox
)
```

`QApplication` was imported and never used.

- [ ] **Step 4: Add the confirmation**

In the same file, replace this block at the end of `SimplifiedNotificationList`:

```python
    def _clear_all(self):
        service = ServiceLocator.get_service("notification")
        if service:
            service.clear_notifications()
```

with exactly this:

```python
    def _confirm_clear_all(self) -> bool:
        """
        Ask the user before the whole notification history is destroyed.

        A test replaces this method, so the question box never opens in a test
        run. Keep the question in this method and nothing else.
        """
        answer = QMessageBox.question(
            self,
            self.tr("Clear all notifications?"),
            self.tr("All notifications will be removed. This cannot be undone."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _clear_all(self) -> None:
        """Clear every notification, after the user confirms it."""
        if not self.items:
            return
        if not self._confirm_clear_all():
            return
        service = ServiceLocator.get_service("notification")
        if service:
            service.clear_notifications()
```

- [ ] **Step 5: Translate the header and disable the button when the list is empty**

In the same file, replace this block inside `SimplifiedNotificationList._setup_ui`:

```python
        # Header with Clear All
        header = QHBoxLayout()
        title = QLabel("Notifications")
        title.setStyleSheet("font-weight: bold; padding: 4px;")
        header.addWidget(title)
        header.addStretch()
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_all)
        header.addWidget(clear_btn)
        layout.addLayout(header)
```

with exactly this:

```python
        header = QHBoxLayout()
        self.title_label = QLabel(self.tr("Notifications"))
        self.title_label.setFont(TypeScale.emphasis(TypeScale.body()))
        header.addWidget(self.title_label)
        header.addStretch()

        self.clear_button = QPushButton(self.tr("Clear All"))
        self.clear_button.setToolTip(self.tr("Remove every notification"))
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self._clear_all)
        header.addWidget(self.clear_button)
        layout.addLayout(header)
```

Then replace these three methods in the same class:

```python
    def add_notification(self, notification: Notification):
        item = NotificationListItem(notification)
        item.removed.connect(self._remove_item)
        self.container_layout.insertWidget(0, item)
        self.items[notification.id] = item

    def remove_notification(self, notification_id: str):
        if notification_id in self.items:
            item = self.items.pop(notification_id)
            item.setParent(None)
            item.deleteLater()

    def clear(self):
        for item in self.items.values():
            item.setParent(None)
            item.deleteLater()
        self.items.clear()
```

with exactly this:

```python
    def add_notification(self, notification: Notification) -> None:
        """Add one notification row at the top of the list."""
        item = NotificationListItem(notification)
        item.removed.connect(self._remove_item)
        self.container_layout.insertWidget(0, item)
        self.items[notification.id] = item
        self._update_clear_button()

    def remove_notification(self, notification_id: str) -> None:
        """Remove one notification row."""
        if notification_id in self.items:
            item = self.items.pop(notification_id)
            item.setParent(None)
            item.deleteLater()
            self._update_clear_button()

    def clear(self) -> None:
        """Remove every notification row."""
        for item in self.items.values():
            item.setParent(None)
            item.deleteLater()
        self.items.clear()
        self._update_clear_button()

    def _update_clear_button(self) -> None:
        """Enable Clear All only when there is something to clear."""
        self.clear_button.setEnabled(bool(self.items))
```

Note: `self.items = {}` is assigned in `__init__` **after** `_setup_ui()` runs. Move it. Replace this block:

```python
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.items = {}
```

with exactly this:

```python
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.items: Dict[str, NotificationListItem] = {}
        self._setup_ui()
```

- [ ] **Step 6: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_notification_list.py -q
```

Expected: PASS. `4 passed`.

- [ ] **Step 7: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `120 passed`.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/widgets/notification_widget.py tests/view/test_notification_list.py
git commit -m "fix(notifications): confirm before Clear All destroys the history"
```

---

### Task 6: The toast must finish its fade out before it is deleted (W2)

`close_toast` emits `closed` on its first line. The presenter answers that signal with `deleteLater()`, so the widget is destroyed while the fade out is still running and the user never sees it. The same method also calls `self.anim.finished.connect(self.close)` on every call, which adds one more connection each time.

**Files:**
- Modify: `src/opaque/view/widgets/notification_widget.py`
- Test: `tests/view/test_notification_widget.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_notification_widget.py`:

```python
def test_closed_is_not_emitted_immediately_on_close(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification())
    qtbot.addWidget(toast)
    seen = []
    toast.closed.connect(seen.append)

    toast.close_toast()

    assert seen == []


def test_closed_is_emitted_after_the_fade_out_finishes(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification())
    qtbot.addWidget(toast)

    with qtbot.waitSignal(toast.closed, timeout=2000) as blocker:
        toast.close_toast()

    assert blocker.args == [toast.notification.id]


def test_closing_twice_emits_closed_once(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification())
    qtbot.addWidget(toast)
    seen = []
    toast.closed.connect(seen.append)

    with qtbot.waitSignal(toast.closed, timeout=2000):
        toast.close_toast()
        toast.close_toast()
    qtbot.wait(400)

    assert seen == [toast.notification.id]


def test_escape_closes_the_toast(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification())
    qtbot.addWidget(toast)
    escape = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Escape,
        Qt.KeyboardModifier.NoModifier,
    )

    with qtbot.waitSignal(toast.closed, timeout=2000):
        toast.keyPressEvent(escape)
```

Then add these two imports at the top of `tests/view/test_notification_widget.py`, above the `from opaque...` lines:

```python
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_notification_widget.py -q
```

Expected: FAIL. `4 failed, 12 passed`. `test_closed_is_not_emitted_immediately_on_close` fails on `assert [] == ['test-1']`, because the current code emits the signal on its first line.

- [ ] **Step 3: Add the closing flag**

In `src/opaque/view/widgets/notification_widget.py`, replace this line inside `ToastWidget.__init__`:

```python
        self.notification = notification
```

with exactly these two lines:

```python
        self.notification = notification
        self._closing = False
```

- [ ] **Step 4: Connect the animation once**

In the same file, replace this block:

```python
    def _setup_animation(self):
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()
```

with exactly this:

```python
    def _setup_animation(self) -> None:
        """Build the fade animation. It runs forward to open, backward to close."""
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        # Connect once, in the constructor. A connection made inside
        # close_toast would be added again on every call.
        self.anim.finished.connect(self._on_fade_finished)
        self.anim.start()
```

- [ ] **Step 5: Rewrite the close path**

In the same file, replace this block:

```python
    def close_toast(self):
        self.anim.setDirection(QPropertyAnimation.Direction.Backward)
        self.anim.finished.connect(self.close)
        self.anim.start()
        self.closed.emit(self.notification.id)
```

with exactly this:

```python
    def close_toast(self) -> None:
        """
        Start the fade out. The closed signal comes when the fade has finished.

        The old code reported the close at once, so the presenter deleted the
        widget while the animation was still running and the fade out never
        appeared on the screen.
        """
        if self._closing:
            return
        self._closing = True
        self.anim.setDirection(QPropertyAnimation.Direction.Backward)
        self.anim.start()

    def _on_fade_finished(self) -> None:
        """Report the close after the fade out. Do nothing after the fade in."""
        if not self._closing:
            return
        self.close()
        self.closed.emit(self.notification.id)

    def keyPressEvent(self, event) -> None:
        """Escape closes the toast when the toast holds the keyboard focus."""
        if event.key() == Qt.Key.Key_Escape:
            self.close_toast()
            event.accept()
            return
        super().keyPressEvent(event)
```

- [ ] **Step 6: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_notification_widget.py -q
```

Expected: PASS. `16 passed`.

- [ ] **Step 7: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `124 passed`.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/widgets/notification_widget.py tests/view/test_notification_widget.py
git commit -m "fix(notifications): emit closed after the fade out and add an Escape key path"
```

---

### Task 7: Dismiss speed must follow severity, and hover must pause it (W3)

Every toast closes after exactly 4 seconds, whatever it says. An error message needs longer than a debug message. A toast that vanishes while the user is reading it also has to stop when the pointer is over it.

**Files:**
- Modify: `src/opaque/view/widgets/notification_widget.py`
- Test: `tests/view/test_notification_widget.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_notification_widget.py`:

```python
def test_info_closes_after_four_seconds():
    assert ToastWidget.duration_for_level(NotificationLevel.INFO) == 4000
    assert ToastWidget.duration_for_level(NotificationLevel.DEBUG) == 4000


def test_warning_stays_longer_than_info():
    warning = ToastWidget.duration_for_level(NotificationLevel.WARNING)
    info = ToastWidget.duration_for_level(NotificationLevel.INFO)
    assert warning > info


def test_error_stays_longer_than_warning():
    error = ToastWidget.duration_for_level(NotificationLevel.ERROR)
    warning = ToastWidget.duration_for_level(NotificationLevel.WARNING)
    assert error > warning


def test_critical_never_closes_on_its_own():
    assert ToastWidget.duration_for_level(NotificationLevel.CRITICAL) is None


def test_a_persistent_notification_has_no_running_timer(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification(persistent=True))
    qtbot.addWidget(toast)
    assert not toast.close_timer.isActive()


def test_pause_and_resume_control_the_timer(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification(
        NotificationLevel.INFO, persistent=False))
    qtbot.addWidget(toast)
    assert toast.close_timer.isActive()

    toast.pause_auto_close()
    assert not toast.close_timer.isActive()

    toast.resume_auto_close()
    assert toast.close_timer.isActive()

    toast.pause_auto_close()
```

The last line stops the timer again, so the test cannot leave a live timer behind.

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_notification_widget.py -q
```

Expected: FAIL. The output contains `AttributeError: type object 'ToastWidget' has no attribute 'duration_for_level'`.

- [ ] **Step 3: Add the duration table**

In `src/opaque/view/widgets/notification_widget.py`, replace this block at the top of `ToastWidget`:

```python
    closed = Signal(str)  # notification_id

    # 24 pixels is the smallest close target that a pointer can hit reliably.
    CLOSE_BUTTON_SIZE = 24
```

with exactly this:

```python
    closed = Signal(str)  # notification_id

    # 24 pixels is the smallest close target that a pointer can hit reliably.
    CLOSE_BUTTON_SIZE = 24

    # How long each level stays on the screen, in milliseconds. A worse level
    # needs more reading time. None means the toast never closes on its own.
    DURATION_BY_LEVEL = {
        NotificationLevel.DEBUG: 4000,
        NotificationLevel.INFO: 4000,
        NotificationLevel.WARNING: 7000,
        NotificationLevel.ERROR: 10000,
        NotificationLevel.CRITICAL: None,
    }

    @staticmethod
    def duration_for_level(level: NotificationLevel) -> Optional[int]:
        """Return the auto close delay in milliseconds, or None to never close."""
        return ToastWidget.DURATION_BY_LEVEL.get(level, 4000)
```

- [ ] **Step 4: Replace the single shot timer**

In the same file, replace this block at the end of `ToastWidget.__init__`:

```python
        self._setup_ui()
        self._setup_animation()
        
        # Timer to auto-close
        if not notification.persistent:
            QTimer.singleShot(4000, self.close_toast)
```

with exactly this:

```python
        self._setup_ui()
        self._setup_animation()

        # A persistent notification waits for the user. Every other level
        # closes itself after a delay that matches how bad the news is.
        self.duration = (
            None if notification.persistent
            else self.duration_for_level(notification.level)
        )
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.close_toast)
        if self.duration is not None:
            self.close_timer.start(self.duration)
```

The timer is a child of the toast, so it dies with the toast. `QTimer.singleShot` had no owner and could fire after the widget was gone.

- [ ] **Step 5: Add the hover pause**

In the same file, add these four methods directly below `keyPressEvent`:

```python
    def pause_auto_close(self) -> None:
        """Stop the auto close delay. The user is reading the toast."""
        self.close_timer.stop()

    def resume_auto_close(self) -> None:
        """Start the auto close delay again, from the beginning."""
        if self.duration is not None and not self._closing:
            self.close_timer.start(self.duration)

    def enterEvent(self, event) -> None:
        """The pointer is over the toast, so hold it on the screen."""
        self.pause_auto_close()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """The pointer has left the toast, so let it close again."""
        self.resume_auto_close()
        super().leaveEvent(event)
```

- [ ] **Step 6: Stop the timer when the toast closes**

In the same file, replace this line inside `close_toast`:

```python
        self._closing = True
```

with exactly these two lines:

```python
        self._closing = True
        self.close_timer.stop()
```

- [ ] **Step 7: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_notification_widget.py -q
```

Expected: PASS. `22 passed`.

- [ ] **Step 8: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `130 passed`.

- [ ] **Step 9: Commit**

```bash
git add src/opaque/view/widgets/notification_widget.py tests/view/test_notification_widget.py
git commit -m "feat(notifications): dismiss delay follows the level and pauses on hover"
```

---

### Task 8: Stop the empty startup report (W5, W7)

At start up the framework sends a log line and a toast that both say the notification system started. The user did not ask for that and it hides the window corner. The notification dock also opens expanded at the bottom, and takes height from the MDI area before there is anything to read.

**Files:**
- Modify: `src/opaque/presenters/notification_presenter.py`

- [ ] **Step 1: Remove the welcome toast**

In `src/opaque/presenters/notification_presenter.py`, replace this block:

```python
    def initialize(self) -> None:
        """Initialize the notification system"""
        try:
            # Log system initialization
            self.log_info("Notification system initialized",
                          "NotificationPresenter")

            # Add welcome notification
            self.notify_info(
                "System Ready",
                "Notification and logging system is now active",
                "System"
            )
        except Exception as e:
            print(f"Failed to initialize notification system: {e}")
            # Still continue - don't let this crash the application
```

with exactly this:

```python
    def initialize(self) -> None:
        """
        Initialize the notification system.

        Nothing is shown to the user here. A start up toast that reports that
        the notification system started tells the user nothing, and it covers
        the corner of the window before the user has done anything.
        """
        try:
            self.log_info("Notification system initialized",
                          "NotificationPresenter")
        except Exception as e:
            print(f"Failed to initialize notification system: {e}")
            # Still continue - don't let this crash the application
```

- [ ] **Step 2: Start the dock hidden and give it a name**

In the same file, replace this block:

```python
            # Wrap in a dock widget for layout compatibility
            self._dock_widget = QDockWidget("Notifications", self._main_window)
            self._dock_widget.setWidget(self._notification_list)
            self._dock_widget.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)

            # Add to main window as dock widget if available
            if self._main_window:
                self._main_window.addDockWidget(
                    Qt.DockWidgetArea.BottomDockWidgetArea,
                    self._dock_widget
                )
```

with exactly this:

```python
            self._dock_widget = QDockWidget(
                self.tr("Notifications"), self._main_window)
            # QMainWindow.saveState() drops any dock without an object name.
            self._dock_widget.setObjectName("NotificationDock")
            self._dock_widget.setWidget(self._notification_list)
            self._dock_widget.setAllowedAreas(
                Qt.DockWidgetArea.AllDockWidgetAreas)

            if self._main_window:
                self._main_window.addDockWidget(
                    Qt.DockWidgetArea.BottomDockWidgetArea,
                    self._dock_widget
                )
                # The dock starts closed. The toolbar button opens it. An empty
                # panel must not take height from the MDI area at start up.
                self._dock_widget.hide()
```

`NotificationPresenter` is a `QObject`, so `self.tr(...)` is available.

- [ ] **Step 3: Prove the welcome toast is gone**

Run:

```bash
grep -n "System Ready" src/opaque/presenters/notification_presenter.py
```

Expected: no output at all.

- [ ] **Step 4: Prove the dock starts hidden**

Run:

```bash
grep -n "_dock_widget.hide()" src/opaque/presenters/notification_presenter.py
```

Expected: two lines. One inside `_setup_views`, one inside `hide_notifications`.

- [ ] **Step 5: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `130 passed`. This task adds no test. It removes behaviour that the user never asked for.

- [ ] **Step 6: Start the example application**

Run:

```
venv\Scripts\python.exe examples\basic_example\main.py
```

Expected: the window opens with the whole MDI area free. No notification panel at the bottom. No toast in the corner. Close the window to end the check.

If a toast appears, Step 1 was not applied. Stop and report it.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/presenters/notification_presenter.py
git commit -m "fix(notifications): remove the empty startup toast and start the dock hidden"
```

---

## Definition of done

- [ ] `venv\Scripts\python.exe -m pytest -q` prints `130 passed`.
- [ ] `grep -n "dc3545\|ffc107\|0dcaf0\|6c757d\|color: gray" src/opaque/view/widgets/notification_widget.py` returns no output.
- [ ] `grep -n "QFont(" src/opaque/view/widgets/notification_widget.py` returns no output.
- [ ] `grep -n "System Ready" src/opaque/presenters/notification_presenter.py` returns no output.
- [ ] `venv\Scripts\python.exe examples\basic_example\main.py` starts with no toast and no open notification dock.

## Left for another plan

- The toolbar notification button is not connected to the dock yet. `OpaqueMainToolbar.set_notifications_visible` and `set_notification_count` are added in Plan 03. Plan 08 Task 7 connects them to this dock and to `NotificationModel.notification_count_changed`. Do not wire them here.
- Grouping and filtering the notification centre is Opportunity O6, in Plan 11 Task 2.
- `NotificationSettingsModel.notification_widget_position` is still ignored. That setting is out of the audit scope. Do not act on it in this plan.
