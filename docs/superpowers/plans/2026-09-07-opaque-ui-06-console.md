# Plan 06 — Console Widget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the console obey the theme, make its search actually find and show a match, and give it a keyboard layer.

**Architecture:** The console display is a `QTextEdit`. The model returns a match as an **index into the filtered item list**, but the widget only knows **text blocks**. This plan adds one list, `_item_block_numbers`, that records the block each item started at. That list is the whole missing link between the model and the display.

**Tech Stack:** PySide6, pytest, pytest-qt.

Read **Rules for the executing agent** in `2026-09-07-opaque-ui-00-index.md` before you start.

**Depends on:** Plan 01 and Plan 02.

**About the totals:** the `pytest -q` totals in this plan assume Plan 01 to Plan 05 are already merged, and that this plan runs after them. If you ran the plans in parallel, compare only the per-file counts and require zero failures in the whole suite.

---

## Findings closed by this plan

| ID | Finding | Task |
|---|---|---|
| W22 | Fonts hardcoded by family and point size | 2 |
| C5 | Console hardcodes colours and ignores the theme | 2 |
| C12 | Console search never highlights or navigates | 1, 3, 4 |
| C8 | No keyboard layer (console part) | 5 |
| C9 | Hit targets 16–30 px (console part) | 5 |

---

## A correction to the audit

The audit said the console search does nothing. That is too broad. `ConsolePresenter._perform_search` **does** call `ConsoleModel.search_output`, and `search_output` **does** return the right indices. Counting works today.

What is broken is everything after the count:

1. `ConsoleWidget._perform_search` is `pass`, so pressing Return in the search box reaches nothing.
2. `ConsoleWidget._highlight_search_result` always moves the cursor to `Start`, whatever the match was.
3. Nothing maps a match index onto a text block, so a highlight is not even possible.

A fourth defect was found while writing this plan and is **not** in the audit:

4. `ConsolePresenter._refresh_display` calls `console_widget.console_display.clear()` instead of `console_widget.clear_display()`. After this plan adds the block tracking list, that call would leave the list holding stale block numbers. Task 4 fixes it.

---

## File Structure

| Path | Responsibility |
|---|---|
| Modify `src/opaque/view/widgets/console_widget.py` | The display, the search panel, the block tracking list and the keyboard layer. |
| Modify `src/opaque/presenters/console_presenter.py` | Connects the search signal, the theme signal, and rebuilds the display correctly. |
| Create `tests/view/test_console_widget.py` | Every test in this plan. |

---

### Task 1: Record where each output item starts

`ConsoleModel.search_output` returns the index of an item in the filtered list. A `QTextEdit` knows nothing about items, only about text blocks. Without a map between the two, no highlight is possible.

**Files:**
- Modify: `src/opaque/view/widgets/console_widget.py`
- Test: `tests/view/test_console_widget.py`

- [ ] **Step 1: Write the failing test**

Create `tests/view/test_console_widget.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the console widget."""

from datetime import datetime

from opaque.models.console_model import ConsoleOutputItem
from opaque.view.widgets.console_widget import ConsoleWidget

TIMESTAMP = datetime(2026, 9, 7, 12, 0, 0)


def _console_with_lines(qtbot, lines):
    """Build a console showing one plain line for each string in lines."""
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    # Without the timestamp prefix the block text is exactly the line text,
    # which keeps every assertion below readable.
    widget.show_timestamps_checkbox.setChecked(False)
    for text in lines:
        widget.add_output_item(ConsoleOutputItem("stdout", text, TIMESTAMP))
    return widget


def test_a_new_console_has_no_displayed_items(qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    assert widget.displayed_item_count() == 0


def test_each_added_item_records_a_block_number(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta"])
    assert widget.displayed_item_count() == 2


def test_block_numbers_increase_with_each_item(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta", "gamma"])
    numbers = widget.block_number_for_items()
    assert numbers == sorted(numbers)
    assert numbers[0] < numbers[-1]


def test_clearing_the_display_forgets_the_block_numbers(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta"])
    widget.clear_display()
    assert widget.displayed_item_count() == 0


def test_a_multi_line_item_records_only_one_entry(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["one\ntwo", "three"])
    numbers = widget.block_number_for_items()
    assert len(numbers) == 2
    assert numbers[1] - numbers[0] == 2
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_console_widget.py -q
```

Expected: FAIL. The output contains `AttributeError: 'ConsoleWidget' object has no attribute 'displayed_item_count'`.

- [ ] **Step 3: Add the tracking list**

In `src/opaque/view/widgets/console_widget.py`, replace this block:

```python
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setup_ui()
        self._last_search_matches: List[int] = []
        self._current_search_index = 0
```

with exactly this:

```python
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # The block number where each displayed item starts. The model returns
        # a match as an index into this list, and a QTextEdit can only find a
        # line by its block number, so this list joins the two.
        self._item_block_numbers: List[int] = []
        self.setup_ui()
        self._last_search_matches: List[int] = []
        self._current_search_index = 0
```

- [ ] **Step 4: Record the block on every insert**

In the same file, replace this block inside `add_output_item`:

```python
        # Move cursor to end and insert text
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.console_display.setTextCursor(cursor)
```

with exactly this:

```python
        # Move cursor to end and insert text
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.console_display.setTextCursor(cursor)

        # Remember where this item starts, before any text is inserted.
        self._item_block_numbers.append(cursor.blockNumber())
```

- [ ] **Step 5: Forget the blocks when the display is cleared**

In the same file, replace this block:

```python
    def clear_display(self):
        """Clear the console display."""
        self.console_display.clear()
        self.status_label.setText("Console cleared")
```

with exactly this:

```python
    def clear_display(self):
        """Clear the console display and forget every recorded block."""
        self.console_display.clear()
        self._item_block_numbers.clear()
        self._last_search_matches = []
        self._current_search_index = 0
        self.status_label.setText(self.tr("Console cleared"))

    def displayed_item_count(self) -> int:
        """Return how many output items the display currently holds."""
        return len(self._item_block_numbers)

    def block_number_for_items(self) -> List[int]:
        """Return the starting block number of every displayed item, in order."""
        return list(self._item_block_numbers)
```

- [ ] **Step 6: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_console_widget.py -q
```

Expected: PASS. `5 passed`.

- [ ] **Step 7: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `135 passed`.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/widgets/console_widget.py tests/view/test_console_widget.py
git commit -m "feat(console): record the text block where each output item starts"
```

---

### Task 2: The console must obey the theme (C5, W22)

The console paints the Visual Studio Code dark palette into a style sheet, whatever theme the user picked. Inside a light theme it is a black rectangle. The font is `QFont("Consolas", 9)`, a family that does not exist on every machine and a size that ignores the operating system font scale.

**Files:**
- Modify: `src/opaque/view/widgets/console_widget.py`
- Modify: `src/opaque/presenters/console_presenter.py`
- Test: `tests/view/test_console_widget.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_console_widget.py`:

```python
def test_the_console_does_not_hardcode_the_editor_palette(qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    sheet = widget.console_display.styleSheet()
    assert "#1e1e1e" not in sheet
    assert "#d4d4d4" not in sheet
    assert "#264f78" not in sheet


def test_the_console_background_comes_from_the_theme(qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    assert widget.background_colour == surface()
    assert surface() in widget.console_display.styleSheet()


def test_the_console_font_is_the_system_fixed_font(qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    assert widget.console_display.font().family() == TypeScale.mono().family()


def test_console_text_passes_contrast_on_a_light_theme(qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    assert contrast_ratio(
        widget.stdout_colour, widget.background_colour) >= TEXT_CONTRAST_MINIMUM
    assert contrast_ratio(
        widget.stderr_colour, widget.background_colour) >= TEXT_CONTRAST_MINIMUM


def test_console_text_passes_contrast_on_a_dark_theme(qtbot, dark_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    assert contrast_ratio(
        widget.stdout_colour, widget.background_colour) >= TEXT_CONTRAST_MINIMUM
    assert contrast_ratio(
        widget.stderr_colour, widget.background_colour) >= TEXT_CONTRAST_MINIMUM
```

Then add these imports at the top of `tests/view/test_console_widget.py`, below the `from opaque.models...` line:

```python
from opaque.view.theme import StatusRole, TypeScale, contrast_ratio, surface
from opaque.view.theme.contrast import TEXT_CONTRAST_MINIMUM
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_console_widget.py -q
```

Expected: FAIL. The output contains `assert '#1e1e1e' not in`.

- [ ] **Step 3: Replace the widget imports**

In `src/opaque/view/widgets/console_widget.py`, replace this block:

```python
from PySide6.QtGui import QFont, QTextCursor, QColor, QTextCharFormat, QIcon, QAction

from opaque.view.view import BaseView
from opaque.models.console_model import ConsoleOutputItem
```

with exactly this:

```python
from PySide6.QtGui import QTextCursor, QColor, QTextCharFormat, QIcon, QAction

from opaque.view.view import BaseView
from opaque.models.console_model import ConsoleOutputItem
from opaque.view.theme import (
    StatusRole,
    TypeScale,
    interactive,
    on_interactive,
    on_surface,
    outline,
    status_colors,
    surface,
)
```

- [ ] **Step 4: Replace the hardcoded display style**

In the same file, replace this block inside `setup_ui`:

```python
        # Console display area
        self.console_display = QTextEdit()
        self.console_display.setReadOnly(True)
        self.console_display.setFont(QFont("Consolas", 9))
        self.console_display.setLineWrapMode(
            QTextEdit.LineWrapMode.WidgetWidth)

        # Set colors for better contrast
        self.console_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                selection-background-color: #264f78;
            }
        """)
```

with exactly this:

```python
        self.console_display = QTextEdit()
        self.console_display.setReadOnly(True)
        self.console_display.setLineWrapMode(
            QTextEdit.LineWrapMode.WidgetWidth)
        self.apply_theme()
```

- [ ] **Step 5: Add the theme method**

In the same file, add this method directly above `def _create_toolbar`:

```python
    def apply_theme(self) -> None:
        """
        Take every console colour and the console font from the active theme.

        The console used to paint one editor palette into a style sheet, so it
        stayed dark inside a light theme and its text failed the contrast
        minimum. Call this method again after the theme changes.
        """
        self.background_colour = surface()
        self.stdout_colour = on_surface()
        self.stderr_colour = status_colors(StatusRole.ERROR).background

        self.console_display.setFont(TypeScale.mono())
        self.console_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.background_colour};
                color: {self.stdout_colour};
                border: 1px solid {outline()};
                selection-background-color: {interactive()};
                selection-color: {on_interactive()};
            }}
        """)
```

- [ ] **Step 6: Use the theme colours for the text itself**

In the same file, replace this block inside `add_output_item`:

```python
        # Set text color based on output type
        char_format = QTextCharFormat()
        if item.output_type == 'stderr':
            char_format.setForeground(
                QColor("#f48771"))  # Light red for errors
        else:
            # Light gray for normal output
            char_format.setForeground(QColor("#d4d4d4"))
```

with exactly this:

```python
        # The colour says which stream the line came from. The [ERROR] prefix
        # added by _format_output_item says the same thing in text, so the
        # colour is never the only cue.
        char_format = QTextCharFormat()
        if item.output_type == 'stderr':
            char_format.setForeground(QColor(self.stderr_colour))
        else:
            char_format.setForeground(QColor(self.stdout_colour))
```

- [ ] **Step 7: Follow the theme change in the presenter**

In `src/opaque/presenters/console_presenter.py`, replace this block:

```python
        # Connect model settings to view checkboxes
        console_widget.auto_scroll_checkbox.toggled.connect(
            lambda checked: setattr(self.model, '_auto_scroll', checked)
        )
        console_widget.word_wrap_checkbox.toggled.connect(
            lambda checked: setattr(self.model, '_word_wrap', checked)
        )
```

with exactly this:

```python
        # Connect model settings to view checkboxes
        console_widget.auto_scroll_checkbox.toggled.connect(
            lambda checked: setattr(self.model, '_auto_scroll', checked)
        )
        console_widget.word_wrap_checkbox.toggled.connect(
            lambda checked: setattr(self.model, '_word_wrap', checked)
        )

        # Repaint the console when the user picks another theme.
        theme_service = ServiceLocator.get_service("theme")
        if theme_service is not None and hasattr(theme_service, "theme_changed"):
            theme_service.theme_changed.connect(
                lambda _name: console_widget.apply_theme())
```

`ThemeService.theme_changed` is added in Plan 02 Task 6. The `hasattr` guard keeps this working if the theme service is missing.

- [ ] **Step 8: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_console_widget.py -q
```

Expected: PASS. `10 passed`.

- [ ] **Step 9: Prove no hardcoded colour is left**

Run:

```bash
grep -n "1e1e1e\|d4d4d4\|f48771\|264f78\|3c3c3c\|QFont(" src/opaque/view/widgets/console_widget.py
```

Expected: no output at all.

- [ ] **Step 10: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `140 passed`.

- [ ] **Step 11: Commit**

```bash
git add src/opaque/view/widgets/console_widget.py src/opaque/presenters/console_presenter.py tests/view/test_console_widget.py
git commit -m "fix(console): take colours and the monospace font from the theme"
```

---

### Task 3: The search must reach the presenter and highlight the match (C12)

`ConsoleWidget._perform_search` is `pass`, so pressing Return in the search box reaches nothing. `_highlight_search_result` moves the cursor to `Start` whatever the match was.

**Files:**
- Modify: `src/opaque/view/widgets/console_widget.py`
- Test: `tests/view/test_console_widget.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_console_widget.py`:

```python
def test_search_is_requested_when_the_user_presses_return(
        qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    with qtbot.waitSignal(widget.search_requested, timeout=1000):
        widget.search_input.returnPressed.emit()


def test_highlighting_selects_the_matching_line(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta", "gamma"])
    widget.set_search_results([1])
    assert widget.console_display.textCursor().selectedText() == "beta"


def test_highlighting_a_later_match_moves_the_cursor_down(
        qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta", "gamma"])
    widget.set_search_results([0, 2])
    first = widget.console_display.textCursor().blockNumber()
    widget._search_next()
    second = widget.console_display.textCursor().blockNumber()
    assert second > first


def test_no_matches_leaves_the_cursor_alone(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta"])
    before = widget.console_display.textCursor().position()
    widget.set_search_results([])
    assert widget.console_display.textCursor().position() == before
    assert widget.status_label.text() == "No matches found"


def test_the_status_shows_the_match_position(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta", "gamma"])
    widget.set_search_results([0, 1, 2])
    assert widget.status_label.text() == "Match 1 of 3"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_console_widget.py -q
```

Expected: FAIL. The output contains `AttributeError: 'ConsoleWidget' object has no attribute 'search_requested'`.

- [ ] **Step 3: Add the search signal**

In `src/opaque/view/widgets/console_widget.py`, replace this block:

```python
    # Signals
    clear_requested = Signal()
    export_requested = Signal(str)  # file path
```

with exactly this:

```python
    # Signals
    clear_requested = Signal()
    export_requested = Signal(str)  # file path
    search_requested = Signal()
```

- [ ] **Step 4: Send Return to the signal**

In the same file, replace this line inside `_create_search_panel`:

```python
        self.search_input.returnPressed.connect(self._perform_search)
```

with exactly this:

```python
        self.search_input.returnPressed.connect(self.search_requested.emit)
```

- [ ] **Step 5: Delete the empty search method**

In the same file, delete this whole block:

```python
    def _perform_search(self):
        """Perform search in console output."""
        # This will be connected to the presenter to perform actual search
        pass

```

The presenter owns the search. A method with the same name in the widget that does nothing only hides that.

- [ ] **Step 6: Make the highlight find the real line**

In the same file, replace this block:

```python
    def _highlight_search_result(self):
        """Highlight the current search result."""
        if not self._last_search_matches:
            return

        # Move cursor to the current match
        cursor = self.console_display.textCursor()
        # This is a simplified implementation - would need actual line-to-position mapping
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.console_display.setTextCursor(cursor)
```

with exactly this:

```python
    def _highlight_search_result(self) -> None:
        """Select the line of the current match and scroll it into view."""
        if not self._last_search_matches:
            return

        item_index = self._last_search_matches[self._current_search_index]
        if item_index < 0 or item_index >= len(self._item_block_numbers):
            return

        block = self.console_display.document().findBlockByNumber(
            self._item_block_numbers[item_index])
        if not block.isValid():
            return

        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                            QTextCursor.MoveMode.KeepAnchor)
        self.console_display.setTextCursor(cursor)
        self.console_display.ensureCursorVisible()
        self._update_search_status()

    def _update_search_status(self) -> None:
        """Say which match of how many the user is looking at."""
        total = len(self._last_search_matches)
        if total == 0:
            self.status_label.setText(self.tr("No matches found"))
            return
        position = self._current_search_index + 1
        self.status_label.setText(
            self.tr("Match {0} of {1}").format(position, total))
```

`self.tr("Match {0} of {1}")` keeps a literal inside `tr`, so `lupdate` can read it, and `.format` fills it afterwards. Never write `self.tr(f"Match {position} ...")`.

- [ ] **Step 7: Report the count through one method**

In the same file, replace this block:

```python
        self._last_search_matches = matches
        self._current_search_index = 0

        self.prev_button.setEnabled(len(matches) > 1)
        self.next_button.setEnabled(len(matches) > 1)

        if matches:
            self.status_label.setText(f"Found {len(matches)} matches")
            self._highlight_search_result()
        else:
            self.status_label.setText("No matches found")
```

with exactly this:

```python
        self._last_search_matches = matches
        self._current_search_index = 0

        self.prev_button.setEnabled(len(matches) > 1)
        self.next_button.setEnabled(len(matches) > 1)

        if matches:
            self._highlight_search_result()
        else:
            self._update_search_status()
```

- [ ] **Step 8: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_console_widget.py -q
```

Expected: PASS. `15 passed`.

- [ ] **Step 9: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `145 passed`.

- [ ] **Step 10: Commit**

```bash
git add src/opaque/view/widgets/console_widget.py tests/view/test_console_widget.py
git commit -m "fix(console): highlight the real matching line and report the match position"
```

---

### Task 4: Navigation must wrap, and a rebuild must not leave stale blocks (C12)

`_search_next` stops at the last match and `_search_previous` stops at the first, with no message, so the buttons look broken. `ConsolePresenter._refresh_display` also clears the `QTextEdit` directly, which would leave `_item_block_numbers` holding block numbers of text that no longer exists.

**Files:**
- Modify: `src/opaque/view/widgets/console_widget.py`
- Modify: `src/opaque/presenters/console_presenter.py`
- Test: `tests/view/test_console_widget.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_console_widget.py`:

```python
def test_next_wraps_to_the_first_match(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta", "gamma"])
    widget.set_search_results([0, 1, 2])
    widget._search_next()
    widget._search_next()
    widget._search_next()
    assert widget.status_label.text() == "Match 1 of 3"


def test_previous_wraps_to_the_last_match(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha", "beta", "gamma"])
    widget.set_search_results([0, 1, 2])
    widget._search_previous()
    assert widget.status_label.text() == "Match 3 of 3"


def test_navigation_does_nothing_without_matches(qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha"])
    widget.set_search_results([])
    widget._search_next()
    widget._search_previous()
    assert widget.status_label.text() == "No matches found"


def test_navigation_buttons_are_disabled_without_matches(
        qtbot, light_palette_app):
    widget = _console_with_lines(qtbot, ["alpha"])
    widget.set_search_results([])
    assert not widget.next_button.isEnabled()
    assert not widget.prev_button.isEnabled()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_console_widget.py -q
```

Expected: FAIL. `test_next_wraps_to_the_first_match` fails with `assert 'Match 3 of 3' == 'Match 1 of 3'`.

- [ ] **Step 3: Make the navigation wrap**

In `src/opaque/view/widgets/console_widget.py`, replace this block:

```python
    def _search_previous(self):
        """Navigate to previous search result."""
        if self._last_search_matches and self._current_search_index > 0:
            self._current_search_index -= 1
            self._highlight_search_result()

    def _search_next(self):
        """Navigate to next search result."""
        if self._last_search_matches and self._current_search_index < len(self._last_search_matches) - 1:
            self._current_search_index += 1
            self._highlight_search_result()
```

with exactly this:

```python
    def _search_previous(self) -> None:
        """Go to the previous match. Wrap to the last match at the start."""
        if not self._last_search_matches:
            return
        self._current_search_index = (
            self._current_search_index - 1) % len(self._last_search_matches)
        self._highlight_search_result()

    def _search_next(self) -> None:
        """Go to the next match. Wrap to the first match at the end."""
        if not self._last_search_matches:
            return
        self._current_search_index = (
            self._current_search_index + 1) % len(self._last_search_matches)
        self._highlight_search_result()
```

- [ ] **Step 4: Connect the search signal in the presenter**

In `src/opaque/presenters/console_presenter.py`, replace this block:

```python
        # Connect search functionality
        search_input = console_widget.search_input
        search_input.textChanged.connect(self._perform_search)
        console_widget.case_sensitive_checkbox.toggled.connect(
            self._perform_search)
```

with exactly this:

```python
        # Connect search functionality
        search_input = console_widget.search_input
        search_input.textChanged.connect(self._perform_search)
        console_widget.search_requested.connect(self._perform_search)
        console_widget.case_sensitive_checkbox.toggled.connect(
            self._perform_search)
```

- [ ] **Step 5: Rebuild the display through the widget**

In the same file, replace this block:

```python
    def _refresh_display(self):
        """Refresh the console display with current filters."""
        try:
            # Clear the current display
            console_widget = self.view.get_console_widget()
            console_widget.console_display.clear()

            # Re-add filtered output
            filtered_output = self.model.get_filtered_output()
            for output_item in filtered_output:
                console_widget.add_output_item(output_item)

        except Exception as e:
            print(f"Error refreshing display: {e}")
```

with exactly this:

```python
    def _refresh_display(self):
        """Refresh the console display with current filters."""
        try:
            console_widget = self.view.get_console_widget()
            # clear_display() also forgets the recorded block numbers.
            # console_display.clear() would leave them pointing at text that
            # no longer exists, and every later highlight would be wrong.
            console_widget.clear_display()

            filtered_output = self.model.get_filtered_output()
            for output_item in filtered_output:
                console_widget.add_output_item(output_item)

            # The match indices belong to the list that was just rebuilt.
            self._perform_search()

        except Exception as e:
            print(f"Error refreshing display: {e}")
```

- [ ] **Step 6: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_console_widget.py -q
```

Expected: PASS. `19 passed`.

- [ ] **Step 7: Prove the direct clear is gone**

Run:

```bash
grep -n "console_display.clear()" src/opaque/presenters/console_presenter.py
```

Expected: no output at all.

- [ ] **Step 8: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `149 passed`.

- [ ] **Step 9: Commit**

```bash
git add src/opaque/view/widgets/console_widget.py src/opaque/presenters/console_presenter.py tests/view/test_console_widget.py
git commit -m "fix(console): wrap search navigation and rebuild the block map on refresh"
```

---

### Task 5: A keyboard layer and usable targets (C8, C9)

Every console action needs a pointer today. There is no shortcut to open the search, no key to leave it, and no key to step through the matches. The close button of the search panel is 30 pixels wide at most.

**Files:**
- Modify: `src/opaque/view/widgets/console_widget.py`
- Test: `tests/view/test_console_widget.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_console_widget.py`:

```python
def test_the_search_action_uses_the_standard_find_shortcut(
        qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    expected = QKeySequence(QKeySequence.StandardKey.Find)
    assert widget.search_action.shortcut() == expected


def test_the_clear_and_export_actions_have_shortcuts(qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    assert not widget.clear_action.shortcut().isEmpty()
    assert not widget.export_action.shortcut().isEmpty()


def test_the_next_and_previous_shortcuts_are_set(qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    assert widget.next_shortcut.key() == QKeySequence(
        QKeySequence.StandardKey.FindNext)
    assert widget.prev_shortcut.key() == QKeySequence(
        QKeySequence.StandardKey.FindPrevious)


def test_escape_closes_the_search_panel(qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    widget.show_search()
    assert widget.search_panel.isVisibleTo(widget)

    widget.keyPressEvent(QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Escape,
        Qt.KeyboardModifier.NoModifier,
    ))

    assert not widget.search_panel.isVisibleTo(widget)


def test_the_search_close_button_is_large_enough(qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    assert widget.close_search_button.width() >= 24
    assert widget.close_search_button.height() >= 24


def test_the_search_input_and_display_have_accessible_names(
        qtbot, light_palette_app):
    widget = ConsoleWidget()
    qtbot.addWidget(widget)
    assert widget.search_input.accessibleName() != ""
    assert widget.console_display.accessibleName() != ""
```

Then add these imports at the top of `tests/view/test_console_widget.py`, above the `from opaque...` lines:

```python
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_console_widget.py -q
```

Expected: FAIL. The output contains `AttributeError: 'ConsoleWidget' object has no attribute 'search_action'`.

- [ ] **Step 3: Add `QShortcut` and `QKeySequence` to the widget imports**

In `src/opaque/view/widgets/console_widget.py`, replace this line:

```python
from PySide6.QtGui import QTextCursor, QColor, QTextCharFormat, QIcon, QAction
```

with exactly this:

```python
from PySide6.QtGui import (
    QTextCursor, QColor, QTextCharFormat, QIcon, QAction, QKeySequence,
    QShortcut,
)
```

- [ ] **Step 4: Give every toolbar action a shortcut**

In the same file, replace this block inside `_create_toolbar`:

```python
        # Clear button
        clear_action = QAction(QIcon.fromTheme("edit-clear"), "Clear", self)
        clear_action.setToolTip("Clear console output")
        clear_action.triggered.connect(self.clear_requested.emit)
        toolbar.addAction(clear_action)
```

with exactly this:

```python
        self.clear_action = QAction(
            QIcon.fromTheme("edit-clear"), self.tr("Clear"), self)
        self.clear_action.setShortcut(QKeySequence("Ctrl+L"))
        self.clear_action.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.clear_action.setToolTip(self.tr("Clear console output (Ctrl+L)"))
        self.clear_action.triggered.connect(self.clear_requested.emit)
        self.addAction(self.clear_action)
        toolbar.addAction(self.clear_action)
```

Then replace this block in the same method:

```python
        # Search button
        search_action = QAction(QIcon.fromTheme("edit-find"), "Search", self)
        search_action.setToolTip("Search console output")
        search_action.triggered.connect(self._toggle_search)
        toolbar.addAction(search_action)

        # Export button
        export_icon = QIcon.fromTheme("document-save")
        if export_icon.isNull():
            # Create a simple fallback icon using Unicode
            export_icon = QIcon()
        export_action = QAction(export_icon, "Export", self)
        export_action.setToolTip("Export console output to file")
        export_action.triggered.connect(self._export_output)
        toolbar.addAction(export_action)

        return toolbar
```

with exactly this:

```python
        self.search_action = QAction(
            QIcon.fromTheme("edit-find"), self.tr("Search"), self)
        self.search_action.setShortcut(QKeySequence.StandardKey.Find)
        self.search_action.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.search_action.setToolTip(self.tr("Search console output (Ctrl+F)"))
        self.search_action.triggered.connect(self._toggle_search)
        self.addAction(self.search_action)
        toolbar.addAction(self.search_action)

        export_icon = QIcon.fromTheme("document-save")
        if export_icon.isNull():
            # Create a simple fallback icon using Unicode
            export_icon = QIcon()
        self.export_action = QAction(export_icon, self.tr("Export"), self)
        self.export_action.setShortcut(QKeySequence("Ctrl+E"))
        self.export_action.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.export_action.setToolTip(
            self.tr("Export console output to file (Ctrl+E)"))
        self.export_action.triggered.connect(self._export_output)
        self.addAction(self.export_action)
        toolbar.addAction(self.export_action)

        return toolbar
```

- [ ] **Step 5: Give the search panel a real close button and an accessible name**

In the same file, replace this block inside `_create_search_panel`:

```python
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search text...")
```

with exactly this:

```python
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Enter search text..."))
        self.search_input.setAccessibleName(self.tr("Search console output"))
```

Then replace this block in the same method:

```python
        # Close search button
        close_button = QPushButton("×")
        close_button.setMaximumWidth(30)
        close_button.clicked.connect(
            lambda: self.search_panel.setVisible(False))
        layout.addWidget(close_button)
```

with exactly this:

```python
        self.close_search_button = QPushButton("×")
        self.close_search_button.setFixedSize(28, 28)
        self.close_search_button.setAccessibleName(self.tr("Close search"))
        self.close_search_button.setToolTip(self.tr("Close search (Escape)"))
        self.close_search_button.clicked.connect(self.hide_search)
        layout.addWidget(self.close_search_button)
```

- [ ] **Step 6: Name the display and add the navigation shortcuts**

In the same file, replace this line inside `setup_ui`:

```python
        self.apply_theme()
```

with exactly this:

```python
        self.console_display.setAccessibleName(self.tr("Console output"))
        self.apply_theme()
```

Then add this block at the very end of `setup_ui`, after `layout.addWidget(self.status_bar)`:

```python

        # F3 and Shift+F3 on most platforms. QKeySequence picks the right key
        # for the platform, so do not write the key names by hand.
        self.next_shortcut = QShortcut(
            QKeySequence.StandardKey.FindNext, self)
        self.next_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.next_shortcut.activated.connect(self._search_next)

        self.prev_shortcut = QShortcut(
            QKeySequence.StandardKey.FindPrevious, self)
        self.prev_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.prev_shortcut.activated.connect(self._search_previous)
```

- [ ] **Step 7: Open, close and leave the search panel**

In the same file, replace this block:

```python
    def _toggle_search(self):
        """Toggle the search panel visibility."""
        visible = not self.search_panel.isVisible()
        self.search_panel.setVisible(visible)
        if visible:
            self.search_input.setFocus()
```

with exactly this:

```python
    def show_search(self) -> None:
        """Open the search panel and put the caret in the search box."""
        self.search_panel.setVisible(True)
        self.search_input.setFocus()

    def hide_search(self) -> None:
        """Close the search panel and give the focus back to the output."""
        self.search_panel.setVisible(False)
        self.console_display.setFocus()

    def _toggle_search(self) -> None:
        """Open the search panel, or close it if it is already open."""
        # isVisibleTo() answers for this widget alone. isVisible() would answer
        # False whenever the console window itself is not on the screen.
        if self.search_panel.isVisibleTo(self):
            self.hide_search()
        else:
            self.show_search()

    def keyPressEvent(self, event) -> None:
        """Escape closes the search panel and returns to the output."""
        if (event.key() == Qt.Key.Key_Escape
                and self.search_panel.isVisibleTo(self)):
            self.hide_search()
            event.accept()
            return
        super().keyPressEvent(event)
```

- [ ] **Step 8: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_console_widget.py -q
```

Expected: PASS. `25 passed`.

- [ ] **Step 9: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `155 passed`.

- [ ] **Step 10: Commit**

```bash
git add src/opaque/view/widgets/console_widget.py tests/view/test_console_widget.py
git commit -m "feat(console): add a keyboard layer and usable search targets"
```

---

## Definition of done

- [ ] `venv\Scripts\python.exe -m pytest tests/view/test_console_widget.py -q` prints `25 passed`.
- [ ] `venv\Scripts\python.exe -m pytest -q` reports zero failures.
- [ ] `grep -n "1e1e1e\|d4d4d4\|f48771\|264f78\|3c3c3c\|QFont(" src/opaque/view/widgets/console_widget.py` returns no output.
- [ ] `grep -n "console_display.clear()" src/opaque/presenters/console_presenter.py` returns no output.
- [ ] In the example application: open the console, type text that exists in the output, press Return, and the matching line is selected. Press F3 and the selection moves to the next match. Press Escape and the search panel closes.

## Left for another plan

- The remaining `tr()` work across the whole framework is Plan 10.
- The wider keyboard map, including a shortcut list the user can read, is Plan 09 Task 1 and Task 2.
- The console still has no busy state for a long running capture. That is Opportunity O7, in Plan 11 Task 3.
