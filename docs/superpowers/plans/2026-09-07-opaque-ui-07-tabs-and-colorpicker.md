# Plan 07 — Tabs and ColorPicker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `CloseableTabWidget` identify its add button by role instead of by its label, stop it from opening a modal dialog out of a selection change, ask before it destroys a tab, and make `ColorPicker` show the colour it holds.

**Architecture:** The tab widget currently asks `tabText(i) == "+"` in fourteen places. A label is presentation, not identity. This plan stores a marker in `QTabBar.setTabData` and asks that instead. `ColorPicker` currently sets `QPalette.Button`, which every stylesheet theme overrides, so the swatch never appears. This plan paints the swatch with a style sheet, which a stylesheet theme cannot silently win against.

**Tech Stack:** PySide6, pytest, pytest-qt.

Read **Rules for the executing agent** in `2026-09-07-opaque-ui-00-index.md` before you start.

**Depends on:** Plan 01 and Plan 02.

**About the totals:** the `pytest -q` totals assume Plan 01 to Plan 06 are already merged and that this plan runs after them. If you ran the plans in parallel, compare only the per-file counts and require zero failures in the whole suite.

---

## Findings closed by this plan

| ID | Finding | Task |
|---|---|---|
| W10 | `"+"` tab identified by label text | 1 |
| W11 | Modal dialog opened from `currentChanged` | 2 |
| C13b | Tab close destroys content with no confirmation | 3 |
| W12 | Minimum-tab rule enforced with a warning box | 3 |
| W8 | ColorPicker swatch invisible under stylesheet themes | 4 |
| W9 | ColorPicker gives no validation feedback | 5 |
| C9 | Hit targets 16–30 px (ColorPicker part) | 5 |

**Task order note:** the index file lists these findings in a different task order. This plan is the authority. W10 must come first, because every later task needs a reliable way to tell the add tab from a content tab.

---

## A defect the audit named but understated

`remove_tab` calls `widget.deleteLater()` **before** `self.tab_widget.removeTab(index)`. That schedules the destruction of a widget that is still a child of the tab widget. Task 3 puts the two calls in the safe order: remove the tab from the bar first, then release the widget.

---

## File Structure

| Path | Responsibility |
|---|---|
| Modify `src/opaque/view/widgets/closeable_tab_widget.py` | Tab identity, close confirmation, and the add flow. |
| Modify `src/opaque/view/widgets/color_picker.py` | The swatch, the validation feedback and the button size. |
| Create `tests/view/test_closeable_tab_widget.py` | Tab tests. |
| Create `tests/view/test_color_picker.py` | Colour picker tests. |

---

### Task 1: Identify the add tab by role, not by its label (W10)

`tabText(i) == "+"` appears fourteen times. A user who renames a tab to `+` breaks all fourteen. A translator who translates the label breaks all fourteen. The label is presentation. The identity belongs in `QTabBar.setTabData`.

**Files:**
- Modify: `src/opaque/view/widgets/closeable_tab_widget.py`
- Test: `tests/view/test_closeable_tab_widget.py`

- [ ] **Step 1: Write the failing test**

Create `tests/view/test_closeable_tab_widget.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the closeable tab widget."""

from PySide6.QtWidgets import QWidget

from opaque.view.widgets.closeable_tab_widget import CloseableTabWidget


def _tabs(qtbot, minimum_tabs=1, show_plus_tab=True):
    """Build a tab widget holding plain QWidget content."""
    widget = CloseableTabWidget(
        widget_type=QWidget,
        minimum_tabs=minimum_tabs,
        show_plus_tab=show_plus_tab,
    )
    qtbot.addWidget(widget)
    return widget


def test_the_add_tab_is_found_by_its_role(qtbot, light_palette_app):
    widget = _tabs(qtbot)
    assert widget.add_tab_index() == widget.tab_widget.count() - 1
    assert widget.is_add_tab(widget.add_tab_index())


def test_a_content_tab_is_not_the_add_tab(qtbot, light_palette_app):
    widget = _tabs(qtbot)
    assert not widget.is_add_tab(0)


def test_a_tab_renamed_to_a_plus_is_still_a_content_tab(
        qtbot, light_palette_app):
    widget = _tabs(qtbot)
    # Set the label directly. This is what a stubborn user or a translation
    # would produce. The tab must keep its identity as content.
    widget.tab_widget.setTabText(0, "+")
    assert not widget.is_add_tab(0)
    assert widget.get_tab_name(0) == "+"
    assert widget.get_widget_at_index(0) is not None


def test_the_real_tab_count_ignores_the_add_tab(qtbot, light_palette_app):
    widget = _tabs(qtbot, minimum_tabs=2)
    assert widget.tab_widget.count() == 3
    assert widget.get_tab_count() == 2


def test_new_tabs_are_inserted_before_the_add_tab(qtbot, light_palette_app):
    widget = _tabs(qtbot)
    widget.add_tab("Second")
    assert widget.is_add_tab(widget.tab_widget.count() - 1)
    assert widget.get_tab_name(widget.tab_widget.count() - 2) == "Second"


def test_without_the_add_tab_nothing_is_an_add_tab(qtbot, light_palette_app):
    widget = _tabs(qtbot, show_plus_tab=False)
    assert widget.add_tab_index() == -1
    assert not widget.is_add_tab(0)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_closeable_tab_widget.py -q
```

Expected: FAIL. The output contains `AttributeError: 'CloseableTabWidget' object has no attribute 'add_tab_index'`.

- [ ] **Step 3: Add the role marker and the two lookup methods**

In `src/opaque/view/widgets/closeable_tab_widget.py`, replace this block:

```python
    # Emitted when tab is renamed (index, old_name, new_name)
    tabRenamed = Signal(int, str, str)
```

with exactly this:

```python
    # Emitted when tab is renamed (index, old_name, new_name)
    tabRenamed = Signal(int, str, str)

    # The value stored in QTabBar.setTabData for the tab that adds new tabs.
    # Identity must never come from the label. A label can be renamed by the
    # user and it can be translated. Tab data cannot.
    ADD_TAB_ROLE = "opaque.add_tab"

    # The label of that tab. Presentation only. Never compare against it.
    ADD_TAB_LABEL = "+"

    def is_add_tab(self, index: int) -> bool:
        """Return True when the tab at index is the add button, not content."""
        if not self._show_plus_tab:
            return False
        if not (0 <= index < self.tab_widget.count()):
            return False
        return self.tab_widget.tabBar().tabData(index) == self.ADD_TAB_ROLE

    def add_tab_index(self) -> int:
        """Return the index of the add tab, or -1 when there is none."""
        for i in range(self.tab_widget.count()):
            if self.is_add_tab(i):
                return i
        return -1
```

- [ ] **Step 4: Mark the add tab when it is created**

In the same file, replace this block:

```python
        # Add the plus tab
        self.tab_widget.addTab(plus_widget, "+")

        # Make the plus tab non-closable by removing the close button
        plus_index = self.tab_widget.count() - 1
        self.tab_widget.tabBar().setTabButton(
            plus_index, QTabBar.ButtonPosition.RightSide, None)
```

with exactly this:

```python
        self.tab_widget.addTab(plus_widget, self.ADD_TAB_LABEL)

        plus_index = self.tab_widget.count() - 1
        # The marker moves with the tab when other tabs are inserted before it.
        self.tab_widget.tabBar().setTabData(plus_index, self.ADD_TAB_ROLE)
        self.tab_widget.tabBar().setTabButton(
            plus_index, QTabBar.ButtonPosition.RightSide, None)
```

- [ ] **Step 5: Replace the insert lookup**

In the same file, replace this block inside `add_tab`:

```python
        # Find plus tab index and insert before it
        plus_tab_index = -1
        if self._show_plus_tab:
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "+":
                    plus_tab_index = i
                    break
```

with exactly this:

```python
        # Insert before the add tab so the add tab always stays last.
        plus_tab_index = self.add_tab_index()
```

- [ ] **Step 6: Replace the remove guard and the count**

In the same file, replace this line:

```python
        if index >= 0 and self._show_plus_tab and self.tab_widget.tabText(index) == "+":
```

with exactly this:

```python
        if self.is_add_tab(index):
```

Then replace this block:

```python
    def _get_real_tab_count(self) -> int:
        """Get the number of real tabs (excluding plus tab)."""
        count = self.tab_widget.count()
        if self._show_plus_tab:
            for i in range(count):
                if self.tab_widget.tabText(i) == "+":
                    count -= 1
                    break
        return count

    def _is_tab_name_unique(self, name: str, exclude_index: int = -1) -> bool:
        """Check if a tab name is unique."""
        name = name.strip()
        if not name or (self._show_plus_tab and name == "+"):
            return False

        for i in range(self.tab_widget.count()):
            if i != exclude_index and self.tab_widget.tabText(i) == name:
                return False
        return True
```

with exactly this:

```python
    def _get_real_tab_count(self) -> int:
        """Get the number of content tabs, not counting the add tab."""
        return sum(
            1 for i in range(self.tab_widget.count())
            if not self.is_add_tab(i)
        )

    def _is_tab_name_unique(self, name: str, exclude_index: int = -1) -> bool:
        """Check if a tab name is free for a content tab to use."""
        name = name.strip()
        if not name:
            return False

        for i in range(self.tab_widget.count()):
            if i == exclude_index or self.is_add_tab(i):
                continue
            if self.tab_widget.tabText(i) == name:
                return False
        return True
```

A content tab may now be named `+`. That is no longer a problem, because the add tab is found by its data.

- [ ] **Step 7: Replace the selection helpers**

In the same file, replace this block:

```python
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            self._current_widget = self.tab_widget.widget(current_index)
            # If current tab is plus tab, switch to last real tab
            if self._show_plus_tab and self.tab_widget.tabText(current_index) == "+":
                for i in range(self.tab_widget.count() - 1, -1, -1):
                    if self.tab_widget.tabText(i) != "+":
                        self.tab_widget.setCurrentIndex(i)
                        self._current_widget = self.tab_widget.widget(i)
                        break
        else:
            self._current_widget = None
```

with exactly this:

```python
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            self._current_widget = self.tab_widget.widget(current_index)
            # The add tab is a button, not a page. Fall back to the last
            # content tab when it somehow becomes current.
            if self.is_add_tab(current_index):
                for i in range(self.tab_widget.count() - 1, -1, -1):
                    if not self.is_add_tab(i):
                        self.tab_widget.setCurrentIndex(i)
                        self._current_widget = self.tab_widget.widget(i)
                        break
        else:
            self._current_widget = None
```

Then replace this block:

```python
    def _on_tab_changed(self, index: int):
        """Handle tab change events."""
        # Check if plus tab was clicked
        if (index >= 0 and self._show_plus_tab and
                self.tab_widget.tabText(index) == "+" and not self._removing_tab):
            self._show_add_tab_dialog()
            return
```

with exactly this:

```python
    def _on_tab_changed(self, index: int):
        """Handle tab change events."""
        if self.is_add_tab(index) and not self._removing_tab:
            self._show_add_tab_dialog()
            return
```

Then replace this block:

```python
        current_name = self.tab_widget.tabText(index)

        # Don't allow renaming the plus tab
        if self._show_plus_tab and current_name == "+":
            return

        while True:
```

with exactly this:

```python
        current_name = self.tab_widget.tabText(index)

        if self.is_add_tab(index):
            return

        while True:
```

Then replace this block inside `rename_tab`:

```python
        current_name = self.tab_widget.tabText(index)

        # Don't allow renaming the plus tab
        if self._show_plus_tab and current_name == "+":
            return False
```

with exactly this:

```python
        current_name = self.tab_widget.tabText(index)

        if self.is_add_tab(index):
            return False
```

- [ ] **Step 8: Replace the public API guards**

In the same file, replace this block:

```python
    def get_current_widget(self) -> Optional[QWidget]:
        """Get the currently active widget."""
        if (self._current_widget and
            self._show_plus_tab and
            isinstance(self._current_widget.parent(), QWidget) and
                self.tab_widget.tabText(self.tab_widget.currentIndex()) == "+"):
            return None
        return self._current_widget

    def get_widget_at_index(self, index: int) -> Optional[QWidget]:
        """Get the widget at the specified tab index."""
        if 0 <= index < self.tab_widget.count():
            widget = self.tab_widget.widget(index)
            # Don't return plus tab widget
            if self._show_plus_tab and self.tab_widget.tabText(index) == "+":
                return None
            return widget
        return None
```

with exactly this:

```python
    def get_current_widget(self) -> Optional[QWidget]:
        """Get the currently active widget, or None when the add tab is current."""
        if self.is_add_tab(self.tab_widget.currentIndex()):
            return None
        return self._current_widget

    def get_widget_at_index(self, index: int) -> Optional[QWidget]:
        """Get the content widget at the specified tab index."""
        if not (0 <= index < self.tab_widget.count()):
            return None
        if self.is_add_tab(index):
            return None
        return self.tab_widget.widget(index)
```

Then replace this block:

```python
    def set_current_tab(self, index: int) -> bool:
        """Set the current tab by index."""
        if 0 <= index < self.tab_widget.count():
            # Don't allow selecting plus tab directly
            if self._show_plus_tab and self.tab_widget.tabText(index) == "+":
                return False
            self.tab_widget.setCurrentIndex(index)
            return True
        return False

    def get_tab_name(self, index: int) -> Optional[str]:
        """Get the name of the tab at the specified index."""
        if 0 <= index < self.tab_widget.count():
            name = self.tab_widget.tabText(index)
            if self._show_plus_tab and name == "+":
                return None
            return name
        return None
```

with exactly this:

```python
    def set_current_tab(self, index: int) -> bool:
        """Set the current tab by index. The add tab cannot be selected."""
        if not (0 <= index < self.tab_widget.count()):
            return False
        if self.is_add_tab(index):
            return False
        self.tab_widget.setCurrentIndex(index)
        return True

    def get_tab_name(self, index: int) -> Optional[str]:
        """Get the name of the content tab at the specified index."""
        if not (0 <= index < self.tab_widget.count()):
            return None
        if self.is_add_tab(index):
            return None
        return self.tab_widget.tabText(index)
```

- [ ] **Step 9: Replace the workspace guards**

In the same file, replace this block:

```python
        for i in range(self.tab_widget.count()):
            tab_name = self.tab_widget.tabText(i)
            # Skip plus tab
            if self._show_plus_tab and tab_name == "+":
                continue
```

with exactly this:

```python
        for i in range(self.tab_widget.count()):
            if self.is_add_tab(i):
                continue
            tab_name = self.tab_widget.tabText(i)
```

Then replace this block:

```python
            # Clear existing tabs except plus tab
            while self._get_real_tab_count() > 0:
                for i in range(self.tab_widget.count()):
                    if not (self._show_plus_tab and self.tab_widget.tabText(i) == "+"):
                        widget = self.tab_widget.widget(i)
                        if widget:
                            widget.deleteLater()
                        self.tab_widget.removeTab(i)
                        break
```

with exactly this:

```python
            # Clear the content tabs. Keep the add tab.
            while self._get_real_tab_count() > 0:
                for i in range(self.tab_widget.count()):
                    if not self.is_add_tab(i):
                        widget = self.tab_widget.widget(i)
                        self.tab_widget.removeTab(i)
                        if widget:
                            widget.deleteLater()
                        break
```

- [ ] **Step 10: Prove no label comparison is left**

Run:

```bash
grep -n '== "+"' src/opaque/view/widgets/closeable_tab_widget.py
```

Expected: no output at all.

- [ ] **Step 11: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_closeable_tab_widget.py -q
```

Expected: PASS. `6 passed`.

- [ ] **Step 12: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `161 passed`.

- [ ] **Step 13: Commit**

```bash
git add src/opaque/view/widgets/closeable_tab_widget.py tests/view/test_closeable_tab_widget.py
git commit -m "fix(tabs): identify the add tab by tab data instead of its label"
```

---

### Task 2: The add tab must not open a modal dialog (W11)

`_on_tab_changed` runs while the tab bar is in the middle of changing the current tab. Opening `QInputDialog.getText` there starts a nested event loop inside a signal handler, and the tab bar is left half changed behind the dialog. If the user cancels, the widget has to guess where to go back to.

The fix removes the prompt. Clicking the add tab adds a tab at once, with a free default name, the way a browser does. The user renames it by double clicking, which already works.

**Files:**
- Modify: `src/opaque/view/widgets/closeable_tab_widget.py`
- Test: `tests/view/test_closeable_tab_widget.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_closeable_tab_widget.py`:

```python
def test_selecting_the_add_tab_creates_a_new_tab(qtbot, light_palette_app):
    widget = _tabs(qtbot)
    before = widget.get_tab_count()
    widget.tab_widget.setCurrentIndex(widget.add_tab_index())
    assert widget.get_tab_count() == before + 1


def test_selecting_the_add_tab_does_not_leave_it_current(
        qtbot, light_palette_app):
    widget = _tabs(qtbot)
    widget.tab_widget.setCurrentIndex(widget.add_tab_index())
    assert not widget.is_add_tab(widget.tab_widget.currentIndex())


def test_the_new_tab_names_are_unique(qtbot, light_palette_app):
    widget = _tabs(qtbot)
    widget.tab_widget.setCurrentIndex(widget.add_tab_index())
    widget.tab_widget.setCurrentIndex(widget.add_tab_index())
    names = [
        widget.get_tab_name(i) for i in range(widget.tab_widget.count())
    ]
    names = [name for name in names if name is not None]
    assert len(names) == 3
    assert len(names) == len(set(names))


def test_no_dialog_is_opened_from_a_selection_change(
        qtbot, light_palette_app, monkeypatch):
    widget = _tabs(qtbot)

    def _explode(*args, **kwargs):
        raise AssertionError("a modal dialog was opened from currentChanged")

    monkeypatch.setattr(QInputDialog, "getText", _explode)
    widget.tab_widget.setCurrentIndex(widget.add_tab_index())
    assert widget.get_tab_count() == 2
```

Then replace this import line at the top of `tests/view/test_closeable_tab_widget.py`:

```python
from PySide6.QtWidgets import QWidget
```

with exactly this:

```python
from PySide6.QtWidgets import QInputDialog, QWidget
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_closeable_tab_widget.py -q
```

Expected: FAIL. `test_no_dialog_is_opened_from_a_selection_change` fails with `AssertionError: a modal dialog was opened from currentChanged`.

If instead the run **hangs** with no output, a real modal dialog is on the screen. Press Escape, then stop and report it.

- [ ] **Step 3: Add the re-entrancy flag**

In `src/opaque/view/widgets/closeable_tab_widget.py`, replace this line:

```python
        self._removing_tab = False  # Flag to prevent dialog during tab removal
```

with exactly these two lines:

```python
        self._removing_tab = False  # Flag to prevent dialog during tab removal
        self._adding_tab = False    # Flag to stop add_tab calling itself
```

- [ ] **Step 4: Replace the add flow**

In the same file, replace this block:

```python
    def _show_add_tab_dialog(self):
        """Show dialog to add a new tab with custom name."""
        name, ok = QInputDialog.getText(
            self,
            'Add New Tab',
            'Enter tab name:',
            text=f"{self._default_tab_name} {self._tab_counter + 1}"
        )

        if not ok:
            # Switch back to previous tab
            self._update_current_widget()
            return

        name = name.strip()
        if not name:
            QMessageBox.warning(
                self,
                "Invalid Name",
                "Tab name cannot be empty."
            )
            self._update_current_widget()
            return

        if not self._is_tab_name_unique(name):
            QMessageBox.warning(
                self,
                "Duplicate Name",
                f"A tab with the name '{name}' already exists. Please choose a different name."
            )
            self._update_current_widget()
            return

        self.add_tab(name)
```

with exactly this:

```python
    def _request_new_tab(self) -> None:
        """
        Add a tab because the user chose the add tab.

        No dialog opens here. A modal dialog started from currentChanged runs
        a nested event loop inside a signal handler, and the tab bar is left
        half changed behind it. The tab is created at once with a free name.
        Double click the tab to rename it.
        """
        if self._adding_tab:
            return
        self._adding_tab = True
        try:
            self.add_tab(self._next_free_tab_name())
        finally:
            self._adding_tab = False

    def _next_free_tab_name(self) -> str:
        """Return a default tab name that no other tab is using."""
        number = self._tab_counter + 1
        name = f"{self._default_tab_name} {number}"
        while not self._is_tab_name_unique(name):
            number += 1
            name = f"{self._default_tab_name} {number}"
        return name
```

- [ ] **Step 5: Call the new flow**

In the same file, replace this line inside `_on_tab_changed`:

```python
            self._show_add_tab_dialog()
```

with exactly this:

```python
            self._request_new_tab()
```

- [ ] **Step 6: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_closeable_tab_widget.py -q
```

Expected: PASS. `10 passed`.

- [ ] **Step 7: Prove the old method is gone**

Run:

```bash
grep -n "_show_add_tab_dialog" src/opaque/view/widgets/closeable_tab_widget.py
```

Expected: no output at all.

- [ ] **Step 8: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `165 passed`.

- [ ] **Step 9: Commit**

```bash
git add src/opaque/view/widgets/closeable_tab_widget.py tests/view/test_closeable_tab_widget.py
git commit -m "fix(tabs): add a tab directly instead of opening a modal dialog from a signal"
```

---

### Task 3: Ask before a tab is destroyed, and never offer a close that cannot work (C13b, W12)

Closing a tab destroys its widget and everything the user typed into it, with no question and no undo. When only the minimum number of tabs is left, the close button still looks live and answers with a warning box, which is a dead end.

`remove_tab` also calls `widget.deleteLater()` **before** `removeTab(index)`, so it schedules the destruction of a widget that is still a page of the tab widget.

**Files:**
- Modify: `src/opaque/view/widgets/closeable_tab_widget.py`
- Test: `tests/view/test_closeable_tab_widget.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_closeable_tab_widget.py`:

```python
def test_the_last_tab_cannot_be_closed(qtbot, light_palette_app):
    widget = _tabs(qtbot, minimum_tabs=1)
    assert not widget.can_close_tab(0)


def test_a_tab_can_be_closed_when_more_than_the_minimum_exist(
        qtbot, light_palette_app):
    widget = _tabs(qtbot, minimum_tabs=1)
    widget.add_tab("Second")
    assert widget.can_close_tab(0)


def test_closing_asks_for_confirmation_first(qtbot, light_palette_app):
    widget = _tabs(qtbot, minimum_tabs=1)
    widget.add_tab("Second")
    asked = []
    widget._confirm_close_tab = lambda name: asked.append(name) or True

    assert widget.remove_tab(0)

    assert len(asked) == 1
    assert widget.get_tab_count() == 1


def test_declining_the_confirmation_keeps_the_tab(qtbot, light_palette_app):
    widget = _tabs(qtbot, minimum_tabs=1)
    widget.add_tab("Second")
    widget._confirm_close_tab = lambda name: False

    assert not widget.remove_tab(0)

    assert widget.get_tab_count() == 2


def test_the_minimum_rule_opens_no_message_box(
        qtbot, light_palette_app, monkeypatch):
    widget = _tabs(qtbot, minimum_tabs=1)

    def _explode(*args, **kwargs):
        raise AssertionError("a warning box was opened for the minimum rule")

    monkeypatch.setattr(QMessageBox, "warning", _explode)
    assert not widget.remove_tab(0)
    assert widget.get_tab_count() == 1
```

Then replace this import line at the top of `tests/view/test_closeable_tab_widget.py`:

```python
from PySide6.QtWidgets import QInputDialog, QWidget
```

with exactly this:

```python
from PySide6.QtWidgets import QInputDialog, QMessageBox, QWidget
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_closeable_tab_widget.py -q
```

Expected: FAIL. The output contains `AttributeError: 'CloseableTabWidget' object has no attribute 'can_close_tab'`.

- [ ] **Step 3: Replace `remove_tab`**

In `src/opaque/view/widgets/closeable_tab_widget.py`, replace the whole `remove_tab` method, from `    def remove_tab(self, index: int) -> bool:` down to and including the line `            self._removing_tab = False`, with exactly this:

```python
    def can_close_tab(self, index: int) -> bool:
        """Return True when the tab at index may be closed right now."""
        if not (0 <= index < self.tab_widget.count()):
            return False
        if self.is_add_tab(index):
            return False
        return self._get_real_tab_count() > self._minimum_tabs

    def _confirm_close_tab(self, name: str) -> bool:
        """
        Ask before a tab and everything in it are destroyed.

        A test replaces this method, so the question box never opens in a test
        run. Keep the question in this method and nothing else.
        """
        answer = QMessageBox.question(
            self,
            self.tr("Close this tab?"),
            self.tr("The tab and everything in it will be removed."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return answer == QMessageBox.StandardButton.Yes

    def remove_tab(self, index: int, confirm: bool = True) -> bool:
        """
        Remove a tab at the specified index.

        Args:
            index: Index of the tab to remove
            confirm: Ask the user first. Pass False from code that has already
                asked, for example a workspace reload.

        Returns:
            True if tab was removed, False otherwise
        """
        if not self.can_close_tab(index):
            # The close button is already hidden in this case, so reaching
            # here means a call from code. Answer False and say nothing. A
            # warning box would be a dead end for the user.
            return False

        if confirm and not self._confirm_close_tab(
                self.tab_widget.tabText(index)):
            return False

        self._removing_tab = True

        try:
            tab_name = self.tab_widget.tabText(index)
            widget = self.tab_widget.widget(index)

            # Take the page out of the tab widget first. deleteLater() on a
            # widget that is still a page schedules the destruction of a live
            # child of the tab widget.
            self.tab_widget.removeTab(index)
            if widget:
                widget.setParent(None)
                widget.deleteLater()

            self._update_current_widget()
            self._update_close_buttons()

            self.tabRemoved.emit(index, tab_name)

            return True

        finally:
            self._removing_tab = False
```

- [ ] **Step 4: Add the close button rule**

In the same file, add this method directly above `def _update_current_widget`:

```python
    def _update_close_buttons(self) -> None:
        """
        Show a close button only on the tabs that may actually be closed.

        A control that cannot do its job must not be offered. The old code
        offered the close button always and answered with a warning box.
        """
        can_close = self._get_real_tab_count() > self._minimum_tabs
        tab_bar = self.tab_widget.tabBar()
        for i in range(self.tab_widget.count()):
            if self.is_add_tab(i):
                continue
            button = tab_bar.tabButton(i, QTabBar.ButtonPosition.RightSide)
            if button is not None:
                button.setVisible(can_close)
                button.setEnabled(can_close)
```

- [ ] **Step 5: Keep the rule up to date when a tab is added**

In the same file, replace this block at the end of `add_tab`:

```python
        # Emit signal
        self.tabAdded.emit(index, name)

        return index
```

with exactly this:

```python
        self._update_close_buttons()

        # Emit signal
        self.tabAdded.emit(index, name)

        return index
```

- [ ] **Step 6: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_closeable_tab_widget.py -q
```

Expected: PASS. `15 passed`.

- [ ] **Step 7: Prove the deletion order is safe**

Run:

```bash
grep -n -A 4 "self.tab_widget.removeTab(index)" src/opaque/view/widgets/closeable_tab_widget.py
```

Expected: the `removeTab` line comes **before** the `deleteLater()` line in the output.

- [ ] **Step 8: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `170 passed`.

- [ ] **Step 9: Commit**

```bash
git add src/opaque/view/widgets/closeable_tab_widget.py tests/view/test_closeable_tab_widget.py
git commit -m "fix(tabs): confirm before closing, hide a close button that cannot work"
```

---

### Task 4: The colour swatch must be visible (W8)

`_update_button_color` writes the colour into `QPalette.Button`. Every theme this framework ships, `qdarkstyle`, `qt-material` and `qt-themes`, installs an **application wide style sheet**, and a style sheet beats the palette for every property it names. The swatch therefore never appears. A colour picker that does not show its colour is a text box with a decoration.

**Files:**
- Modify: `src/opaque/view/widgets/color_picker.py`
- Test: `tests/view/test_color_picker.py`

- [ ] **Step 1: Write the failing test**

Create `tests/view/test_color_picker.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the colour picker widget."""

from PySide6.QtGui import QPalette

from opaque.view.theme import contrast_ratio
from opaque.view.theme.contrast import TEXT_CONTRAST_MINIMUM
from opaque.view.widgets.color_picker import ColorPicker


def test_the_swatch_is_painted_with_a_style_sheet(qtbot, light_palette_app):
    picker = ColorPicker("#ff0000")
    qtbot.addWidget(picker)
    assert "#ff0000" in picker.button.styleSheet()


def test_the_swatch_follows_the_colour(qtbot, light_palette_app):
    picker = ColorPicker("#ff0000")
    qtbot.addWidget(picker)
    picker.setColor("#00ff00")
    assert "#00ff00" in picker.button.styleSheet()
    assert "#ff0000" not in picker.button.styleSheet()


def test_the_button_text_stays_readable_on_the_swatch(
        qtbot, light_palette_app):
    # Mid grey is the hardest background for a black or white foreground.
    picker = ColorPicker("#808080")
    qtbot.addWidget(picker)
    ratio = contrast_ratio(picker.button_text_colour, picker.color())
    assert ratio >= TEXT_CONTRAST_MINIMUM


def test_the_palette_is_not_used_for_the_swatch(qtbot, light_palette_app):
    picker = ColorPicker("#ff0000")
    qtbot.addWidget(picker)
    button_role = picker.button.palette().color(QPalette.ColorRole.Button)
    assert button_role.name() != "#ff0000"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_color_picker.py -q
```

Expected: FAIL. `test_the_swatch_is_painted_with_a_style_sheet` fails with `assert '#ff0000' in ''`.

- [ ] **Step 3: Replace the widget imports**

In `src/opaque/view/widgets/color_picker.py`, replace this block:

```python
from PySide6.QtWidgets import QWidget, QPushButton, QColorDialog, QHBoxLayout, QLineEdit
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Signal, Slot
```

with exactly this:

```python
from PySide6.QtWidgets import QWidget, QPushButton, QColorDialog, QHBoxLayout, QLineEdit
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal, Slot

from opaque.view.theme import (
    StatusRole,
    interactive,
    outline,
    readable_foreground,
    status_colors,
)
```

- [ ] **Step 4: Paint the swatch with a style sheet**

In the same file, replace this block:

```python
    def _update_button_color(self):
        palette = self.button.palette()
        palette.setColor(QPalette.Button, self._color)
        self.button.setPalette(palette)
        self.button.update()
```

with exactly this:

```python
    def _update_button_color(self) -> None:
        """
        Paint the swatch with a style sheet.

        The palette cannot be used here. Every theme this framework ships
        installs an application wide style sheet, and a style sheet beats the
        palette for every property it names, so a swatch set through
        QPalette.Button never appeared on the screen.
        """
        self.button_text_colour = readable_foreground(self._color.name())
        self.button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color.name()};
                color: {self.button_text_colour};
                border: 1px solid {outline()};
                border-radius: 3px;
            }}
            QPushButton:focus {{
                border: 2px solid {interactive()};
            }}
        """)
```

The `:focus` rule is the visible focus indicator. A keyboard user must be able to see where the focus is.

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_color_picker.py -q
```

Expected: PASS. `4 passed`.

- [ ] **Step 6: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `174 passed`.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/widgets/color_picker.py tests/view/test_color_picker.py
git commit -m "fix(colorpicker): paint the swatch with a style sheet so a theme cannot hide it"
```

---

### Task 5: Say when the typed colour is wrong, and give the button a usable size (W9, C9)

`_on_text_changed` silently drops anything that is not a colour, so the user gets no answer at all. It also commits and emits `colorChanged` on every keystroke, so typing `#336699` emits seven times and six of those are colours the user never asked for. The button is 30 pixels wide and has no height rule at all.

**Files:**
- Modify: `src/opaque/view/widgets/color_picker.py`
- Test: `tests/view/test_color_picker.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_color_picker.py`:

```python
def test_the_button_is_large_enough(qtbot, light_palette_app):
    picker = ColorPicker("#ff0000")
    qtbot.addWidget(picker)
    assert picker.button.width() >= 28
    assert picker.button.height() >= 28


def test_the_button_and_the_box_have_accessible_names(
        qtbot, light_palette_app):
    picker = ColorPicker("#ff0000")
    qtbot.addWidget(picker)
    assert picker.button.accessibleName() != ""
    assert picker.line_edit.accessibleName() != ""


def test_invalid_text_is_marked(qtbot, light_palette_app):
    picker = ColorPicker("#ff0000")
    qtbot.addWidget(picker)
    picker.line_edit.setText("not a colour")
    assert not picker.is_text_valid()
    assert picker.line_edit.styleSheet() != ""
    assert picker.line_edit.accessibleDescription() != ""


def test_invalid_text_does_not_change_the_colour(qtbot, light_palette_app):
    picker = ColorPicker("#ff0000")
    qtbot.addWidget(picker)
    seen = []
    picker.colorChanged.connect(seen.append)

    picker.line_edit.setText("not a colour")

    assert picker.color() == "#ff0000"
    assert seen == []


def test_leaving_the_box_with_invalid_text_restores_the_last_colour(
        qtbot, light_palette_app):
    picker = ColorPicker("#ff0000")
    qtbot.addWidget(picker)
    picker.line_edit.setText("not a colour")

    picker.line_edit.editingFinished.emit()

    assert picker.line_edit.text() == "#ff0000"
    assert picker.is_text_valid()
    assert picker.line_edit.styleSheet() == ""


def test_valid_text_is_taken_when_the_user_leaves_the_box(
        qtbot, light_palette_app):
    picker = ColorPicker("#ff0000")
    qtbot.addWidget(picker)
    seen = []
    picker.colorChanged.connect(seen.append)

    picker.line_edit.setText("#0000ff")
    assert seen == []

    picker.line_edit.editingFinished.emit()

    assert picker.color() == "#0000ff"
    assert seen == ["#0000ff"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_color_picker.py -q
```

Expected: FAIL. The output contains `AttributeError: 'ColorPicker' object has no attribute 'is_text_valid'`.

- [ ] **Step 3: Replace the constructor**

In `src/opaque/view/widgets/color_picker.py`, replace this block:

```python
    def __init__(self, initial_color: str = "#ffffff", parent=None):
        super().__init__(parent)
        self._color = QColor(initial_color)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.line_edit = QLineEdit(self._color.name())
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.layout.addWidget(self.line_edit)

        self.button = QPushButton("...")
        self.button.setFixedWidth(30)
        self.button.clicked.connect(self._on_button_clicked)
        self.layout.addWidget(self.button)

        self._update_button_color()
```

with exactly this:

```python
    # 28 pixels is the smallest square a pointer can hit reliably.
    BUTTON_SIZE = 28

    def __init__(self, initial_color: str = "#ffffff", parent=None):
        super().__init__(parent)
        self._color = QColor(initial_color)
        self._text_is_valid = True

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.line_edit = QLineEdit(self._color.name())
        self.line_edit.setAccessibleName(self.tr("Colour value"))
        self.line_edit.textChanged.connect(self._on_text_changed)
        # The colour is taken when the user leaves the box, not on every key.
        self.line_edit.editingFinished.connect(self._commit_text)
        self.layout.addWidget(self.line_edit)

        self.button = QPushButton("...")
        self.button.setFixedSize(self.BUTTON_SIZE, self.BUTTON_SIZE)
        self.button.setAccessibleName(self.tr("Choose a colour"))
        self.button.setToolTip(self.tr("Open the colour dialog"))
        self.button.clicked.connect(self._on_button_clicked)
        self.layout.addWidget(self.button)

        self._update_button_color()
        self._update_validation_style()
```

- [ ] **Step 4: Replace the text handling**

In the same file, replace this block:

```python
    @Slot(str)
    def _on_text_changed(self, text: str):
        new_color = QColor(text)
        if new_color.isValid() and self._color != new_color:
            self._color = new_color
            self._update_button_color()
            self.colorChanged.emit(self._color.name())
```

with exactly this:

```python
    def is_text_valid(self) -> bool:
        """Return True when the text in the box names a colour Qt understands."""
        return self._text_is_valid

    @Slot(str)
    def _on_text_changed(self, text: str) -> None:
        """
        Say whether the typed text is a colour. Do not take it yet.

        The old code took the value on every key press, so typing a six digit
        hex value emitted six colours the user never asked for, and it said
        nothing at all when the text was not a colour.
        """
        self._text_is_valid = QColor(text).isValid()
        self._update_validation_style()

    def _update_validation_style(self) -> None:
        """Mark the box when the text is not a colour."""
        if self._text_is_valid:
            self.line_edit.setStyleSheet("")
            self.line_edit.setAccessibleDescription("")
            self.line_edit.setToolTip(
                self.tr("A colour name or a hex value, for example #3366cc"))
            return

        # The border colour is not the only cue. The tooltip and the
        # accessible description say the same thing in words.
        error = status_colors(StatusRole.ERROR)
        self.line_edit.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {error.border}; }}")
        message = self.tr("This is not a colour. Use a name or a hex value.")
        self.line_edit.setAccessibleDescription(message)
        self.line_edit.setToolTip(message)

    def _commit_text(self) -> None:
        """Take the typed colour when the user leaves the box."""
        if not self._text_is_valid:
            # Put the last good colour back. The box must never keep a value
            # that the widget does not hold.
            self.line_edit.setText(self._color.name())
            self._text_is_valid = True
            self._update_validation_style()
            return
        self.setColor(self.line_edit.text())
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_color_picker.py -q
```

Expected: PASS. `10 passed`.

- [ ] **Step 6: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `180 passed`.

If `tests/view/test_settings_dialog.py` fails here, read the failure. The Settings dialog from Plan 04 records a pending value from `colorChanged`, and that signal now arrives once when the box loses the focus instead of once per key press. Fix the test to emit `editingFinished` after it sets the text. Do not put the per key press behaviour back.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/widgets/color_picker.py tests/view/test_color_picker.py
git commit -m "fix(colorpicker): report invalid text and commit the colour on edit finish"
```

---

## Definition of done

- [ ] `venv\Scripts\python.exe -m pytest tests/view/test_closeable_tab_widget.py -q` prints `15 passed`.
- [ ] `venv\Scripts\python.exe -m pytest tests/view/test_color_picker.py -q` prints `10 passed`.
- [ ] `venv\Scripts\python.exe -m pytest -q` reports zero failures.
- [ ] `grep -n '== "+"' src/opaque/view/widgets/closeable_tab_widget.py` returns no output.
- [ ] `grep -n "_show_add_tab_dialog\|QPalette" src/opaque/view/widgets/closeable_tab_widget.py src/opaque/view/widgets/color_picker.py` returns no output.
- [ ] In the example application: click the `+` tab and a new tab appears at once with no dialog. Close a tab and a question appears first. With one tab left, the close button is gone.

## Left for another plan

- The class docstring of `CloseableTabWidget` still says "Closeable tabs with confirmation" and "+ tab for adding new tabs". Both are now true. Do not change the docstring.
- The remaining `tr()` work across the framework is Plan 10.
- The wider keyboard map is Plan 09.
