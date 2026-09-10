# Review Follow-up Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> This file already sits at `docs/superpowers/plans/2026-09-09-review-followup-fixes.md`, untracked, together with `docs/ENGINEERING_REVIEW_2026-09-09.md` and a `SKIPPED_FILES` entry in `tests/test_documentation.py` (this plan shows imports its Tasks 6-7 have not built yet). Commit all three with Task 1. Remove the `SKIPPED_FILES` entry in Task 12, after Tasks 6-7 make the imports real.

**Goal:** Close every open item in `docs/ENGINEERING_REVIEW_2026-09-09.md`: five small code defects, four decided features (validator runs, four settings widgets, self-check wired, examples fixed), and one documentation truth pass.

**Architecture:** No structural change. Each task is a small TDD fix inside the existing MVP framework. New code follows the existing rules: tokens for colours, `self.tr()` for user text, one commit per task, docs updated in the same commit that changes a public name.

**Tech Stack:** Python 3.11, PySide6, pytest (headless, `QT_QPA_PLATFORM=offscreen` set by `tests/conftest.py`), mypy, pylint. All commands run through `uv run`.

**Decisions of record (owner answered 2026-09-09):**
- `validator=` runs in the generated setter.
- All four missing `UIType` widgets get built (TEXTAREA, SLIDER, LIST_VIEW, FILE_SELECTOR).
- `self_check.py` is wired to the `OPAQUE_SELF_CHECK` environment variable.
- Examples: fix five, delete `examples/my_example`, add guard tests.
- `create_services` seam: NOT built. Record as accepted (Task 12).

**Context for a fresh engineer:**
- `CLAUDE.md` at the repo root states the framework rules. Read it first.
- Full suite: `uv run python -m pytest tests -q` (~945 tests, ~17 s). Type check: `uv run python -m mypy src/opaque`. Lint: `uv run python -m pylint src/opaque`. All three must stay clean; CI enforces them.
- `tests/test_quickstart.py` proves the README block between `<!-- quickstart:begin -->` and `<!-- quickstart:end -->` is byte-identical to `examples/quickstart/main.py`. Any change to that file must update README.md in the same commit.
- Commit style: `type(scope): summary`, plain English, matching `git log`.

---

### Task 1: Make `BasePresenter.cleanup()` idempotent (kills 14 libpyside warnings)

The full suite prints 14 `RuntimeWarning: libpyside: Failed to disconnect ...` lines. Cause: `cleanup()` runs twice — once when the view closes (`_handle_view_closed`), once at shell `closeEvent`. The second disconnect fails; `except RuntimeError` catches the exception but not the warning.

**Files:**
- Modify: `src/opaque/presenters/presenter.py` (attribute near line 64, method at lines 229-245)
- Test: `tests/test_presenter_contract.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_presenter_contract.py`; reuse the module's existing presenter/model/view doubles — read the file first and build the presenter the same way its other tests do):

```python
def test_cleanup_runs_once_even_when_called_twice(make_presenter):
    """Shell closeEvent calls cleanup() after the view already closed.

    The second call must be a no-op: no second detach, no failed
    disconnect, no libpyside RuntimeWarning.
    """
    presenter = make_presenter()
    presenter.cleanup()
    detach_calls = presenter.model.detach_call_count

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        presenter.cleanup()

    assert presenter.model.detach_call_count == detach_calls
```

If `tests/test_presenter_contract.py` has no `make_presenter` fixture or no detach counter on its model double, add the counter to the module's existing model double (`detach_call_count` incremented in `detach`) and a small local fixture that builds the module's existing presenter double — copy the construction pattern already used by the first test in that file.

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run python -m pytest tests/test_presenter_contract.py -q`
Expected: the new test FAILS (second `detach` runs, or `RuntimeWarning` raised as error).

- [ ] **Step 3: Implement.** In `src/opaque/presenters/presenter.py`:

Below the `_closed` attribute (line 64), add:

```python
        # True after cleanup() has run. The shell calls cleanup() for every
        # feature at closeEvent, and a presenter whose view already closed
        # has run it once by then. Disconnecting twice does not raise (the
        # RuntimeError is caught below) but libpyside emits a RuntimeWarning
        # that no except clause can silence, so the second call must not
        # reach the disconnect at all.
        self._cleaned: bool = False
```

Change `cleanup()` (line 229) to:

```python
    def cleanup(self) -> None:
        """
        Clean up presenter resources. Safe to call twice: the second call
        returns without touching the model or the view.
        """
        if self._cleaned:
            return
        self._cleaned = True

        # Detach from model
        self._model.detach(self)

        # Disconnect from view events
        try:
            self._view.window_closed.disconnect(self._handle_view_closed)
            self._view.window_opened.disconnect(self.on_view_show)
        except RuntimeError:
            # Already disconnected
            pass

        # Clean up model
        self._model.cleanup()
```

- [ ] **Step 4: Verify**

Run: `uv run python -m pytest tests -q 2>&1 | grep -c "Failed to disconnect"`
Expected: `0`. Then `uv run python -m pytest tests -q` → all pass.

- [ ] **Step 5: Commit**

```bash
git add src/opaque/presenters/presenter.py tests/test_presenter_contract.py
git commit -m "fix(presenter): make cleanup idempotent so a second call cannot warn"
```

---

### Task 2: Remove the silent 0-99 clamp on unbounded spinboxes

`settings.py:429-439` sets a spinbox range only when the field declares one. Qt's default range is 0-99, so an `IntField` without `max_value` silently clamps a stored 5000 to 99 and any negative value to 0.

**Files:**
- Modify: `src/opaque/view/dialogs/settings.py:429-450`
- Test: `tests/view/test_settings_dialog.py`

- [ ] **Step 1: Write the failing test** (append to `tests/view/test_settings_dialog.py`; the file already has `service` and `dialog` fixtures and a `DemoModel` — add a second model with an unbounded field):

```python
class UnboundedModel(AbstractModel):
    FEATURE_ID = "unbounded"

    big = IntField(default=5000, description="Big", settings=True)
    ratio = FloatField(default=1e6, description="Ratio", settings=True)

    def feature_name(self) -> str:
        return "Unbounded"

    def feature_icon(self):
        from PySide6.QtGui import QIcon
        return QIcon()


@pytest.fixture
def unbounded_dialog(qtbot, service):
    presenter = DemoPresenter(UnboundedModel())
    presenter.feature_id = "unbounded"
    widget = SettingsDialog([presenter], parent=None)
    qtbot.addWidget(widget)
    return widget


def test_a_spinbox_without_declared_bounds_is_not_clamped_to_99(unbounded_dialog):
    """Qt's default QSpinBox range is 0-99; a stored 5000 was clamped."""
    spin = _widget_of_type(unbounded_dialog, QSpinBox)
    assert spin.value() == 5000
    assert spin.minimum() < 0


def test_a_double_spinbox_without_declared_bounds_keeps_a_large_value(unbounded_dialog):
    spin = _widget_of_type(unbounded_dialog, QDoubleSpinBox)
    assert spin.value() == 1e6
```

- [ ] **Step 2: Run and confirm both fail** (`spin.value() == 99` and `== 99.0`)

Run: `uv run python -m pytest tests/view/test_settings_dialog.py -q`

- [ ] **Step 3: Implement.** In `src/opaque/view/dialogs/settings.py`, in the `UIType.SPINBOX` branch (line 429), replace the two conditional bound calls with:

```python
            elif hasattr(field, 'ui_type') and field.ui_type == UIType.SPINBOX:
                widget = QSpinBox()
                # Qt's default range is 0-99, which silently clamped every
                # unbounded field. Open the full int32 range first; a
                # declared bound then narrows it.
                widget.setRange(-2**31, 2**31 - 1)
                if hasattr(field, 'min_value') and field.min_value is not None:
                    widget.setMinimum(int(field.min_value))
                if hasattr(field, 'max_value') and field.max_value is not None:
                    widget.setMaximum(int(field.max_value))
                widget.setValue(int(current_value))
```

And in the `UIType.DOUBLE_SPINBOX` branch (line 440), insert after `widget = QDoubleSpinBox()`:

```python
                # Same reason as the QSpinBox above: Qt's default is 0-99.
                widget.setRange(-1.0e15, 1.0e15)
                widget.setDecimals(6)
```

(keep the two conditional `setMinimum`/`setMaximum` calls that follow).

- [ ] **Step 4: Verify**

Run: `uv run python -m pytest tests/view/test_settings_dialog.py -q` → all pass.

- [ ] **Step 5: Commit**

```bash
git add src/opaque/view/dialogs/settings.py tests/view/test_settings_dialog.py
git commit -m "fix(settings): open the spinbox range when the field declares no bounds"
```

---

### Task 3: Run the `validator=` callable in the generated setter

`Field.validator` is documented but never runs: the generated setter checks only `choices`/`min_value`/`max_value` (`abstract_model.py:74-83`), and nothing calls `AbstractModel.validate()`.

**Files:**
- Modify: `src/opaque/models/abstract_model.py:74-84`
- Test: `tests/models/test_abstract_model.py`

- [ ] **Step 1: Write the failing test** (append to `tests/models/test_abstract_model.py`, following the module's existing model-declaration pattern):

```python
def test_the_validator_callable_rejects_a_write():
    from opaque.models.abstract_model import AbstractModel
    from opaque.models.annotations import IntField

    class EvenModel(AbstractModel):
        FEATURE_ID = "even"
        value = IntField(default=0, validator=lambda v: v % 2 == 0)

    model = EvenModel()
    model.value = 4
    assert model.value == 4
    with pytest.raises(ValueError, match="validator"):
        model.value = 3
    assert model.value == 4
```

- [ ] **Step 2: Run and confirm it fails** (`model.value = 3` succeeds today)

Run: `uv run python -m pytest tests/models/test_abstract_model.py -q`

- [ ] **Step 3: Implement.** In `src/opaque/models/abstract_model.py`, inside the generated `setter` (line 71), after the `max_value` check (line 83) and before the `# ------------------` line, add:

```python
                    if field.validator is not None and not field.validator(value):
                        raise ValueError(
                            f"Value '{value}' for '{name}' was rejected by "
                            f"the field's validator callable")
```

- [ ] **Step 4: Verify the setter and the dialog agree.** The settings dialog writes through this same setter in `_apply_settings` (`settings.py:236`) and already catches `ValueError` and reports the field as rejected, so no dialog change is needed.

Run: `uv run python -m pytest tests -q` → all pass.
Run: `uv run python -m mypy src/opaque` → clean.

- [ ] **Step 5: Commit**

```bash
git add src/opaque/models/abstract_model.py tests/models/test_abstract_model.py
git commit -m "fix(models): the validator callable now runs on every field write"
```

---

### Task 4: `apply_theme()` for the two widgets that keep stale colours

The repaint contract (`shell.py:268-293`): a widget that caches a token declares `apply_theme()`; the shell walk calls it after every theme change. `BusyOverlay` and `NotificationListItem` bake tokens into f-string stylesheets in their constructors and declare no `apply_theme()`.

**Files:**
- Modify: `src/opaque/view/widgets/busy.py:27-55`
- Modify: `src/opaque/view/widgets/notification_widget.py:252-300`
- Test: `tests/view/test_busy.py`, `tests/view/test_notification_list.py`

- [ ] **Step 1: Write the failing tests.**

Append to `tests/view/test_busy.py`:

```python
def test_the_overlay_repaints_after_a_theme_change(qtbot):
    from PySide6.QtWidgets import QApplication, QWidget
    from opaque.view.theme import build_dark_palette, build_light_palette, surface_variant
    from opaque.view.widgets.busy import BusyOverlay

    parent = QWidget()
    qtbot.addWidget(parent)
    QApplication.setPalette(build_light_palette())
    overlay = BusyOverlay(parent)
    before = overlay.styleSheet()

    QApplication.setPalette(build_dark_palette())
    overlay.apply_theme()

    assert overlay.styleSheet() != before
    assert surface_variant() in overlay.styleSheet()
```

Append to `tests/view/test_notification_list.py` (reuse the `make_notification` fixture from `tests/view/conftest.py`):

```python
def test_the_list_item_repaints_after_a_theme_change(qtbot, make_notification):
    from PySide6.QtWidgets import QApplication
    from opaque.view.theme import build_dark_palette, build_light_palette
    from opaque.view.widgets.notification_widget import NotificationListItem

    QApplication.setPalette(build_light_palette())
    item = NotificationListItem(make_notification())
    qtbot.addWidget(item)
    before = item.level_label.styleSheet()

    QApplication.setPalette(build_dark_palette())
    item.apply_theme()

    assert item.level_label.styleSheet() != before
```

- [ ] **Step 2: Run and confirm both fail** (`AttributeError: apply_theme` or unchanged stylesheet)

Run: `uv run python -m pytest tests/view/test_busy.py tests/view/test_notification_list.py -q`

- [ ] **Step 3: Implement `BusyOverlay`.** In `src/opaque/view/widgets/busy.py`, replace the two `setStyleSheet` lines in `__init__` (lines 31-32 and 41) with a call to the new method, added after `stop()`:

In `__init__`, line 31-32 becomes (keep `setAutoFillBackground(True)`):

```python
        self.setAutoFillBackground(True)
```

Line 41 (`self.message_label.setStyleSheet(...)`) is deleted. At the end of `__init__`, before `self.hide()`, add:

```python
        self.apply_theme()
```

After `stop()` (line 76), add:

```python
    def apply_theme(self) -> None:
        """Re-read the theme tokens. The shell calls this after a theme change.

        A token is a string, not a live binding, so a stylesheet built in the
        constructor keeps its colours for ever without this hook.
        """
        self.setStyleSheet(
            f"BusyOverlay {{ background-color: {surface_variant()}; }}")
        self.message_label.setStyleSheet(f"color: {on_surface()};")
```

- [ ] **Step 4: Implement `NotificationListItem`.** In `src/opaque/view/widgets/notification_widget.py`:

In `__init__` (lines 252-257), remove the two cached token reads so it reads:

```python
    def __init__(self, notification: Notification, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.notification = notification
        self._setup_ui()
        self.apply_theme()
```

In `_setup_ui`, delete the `self.level_label.setStyleSheet(...)` block (lines 269-273) and the `self.time_label.setStyleSheet(...)` line (line 278) — `apply_theme()` now owns both. After `_setup_ui`, add:

```python
    def apply_theme(self) -> None:
        """Re-read the theme tokens. The shell calls this after a theme change."""
        self.status = status_colors(status_role_for_level(self.notification.level))
        self.timestamp_colour = muted_on_surface()
        self.level_label.setStyleSheet(
            f"color: {self.status.foreground};"
            f"background-color: {self.status.background};"
            f"border-radius: 3px; padding: 1px 5px;"
        )
        self.time_label.setStyleSheet(f"color: {self.timestamp_colour};")
```

(`status_colors`, `status_role_for_level`, and `muted_on_surface` are already imported by this module — verify at the top of the file, they are used at lines 255-256 today.)

- [ ] **Step 5: Verify**

Run: `uv run python -m pytest tests/view -q` → all pass. Then the full suite, mypy, pylint.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/widgets/busy.py src/opaque/view/widgets/notification_widget.py tests/view/test_busy.py tests/view/test_notification_list.py
git commit -m "fix(widgets): busy overlay and notification rows repaint after a theme change"
```

---

### Task 5: Wire `self_check.py` to the `OPAQUE_SELF_CHECK` environment variable

`view/self_check.py` has zero production callers. Decision: the shell runs it on first show when `OPAQUE_SELF_CHECK` is set (any non-empty value).

**Files:**
- Modify: `src/opaque/shell.py` (imports; attribute in `__init__`; two new methods near `closeEvent`, line 659)
- Test: `tests/view/test_self_check.py`

- [ ] **Step 1: Write the failing test** (append to `tests/view/test_self_check.py`; the shell fixture `app_window` from `tests/conftest.py` is session-scoped and shared — do not close it):

```python
def test_the_shell_runs_the_check_only_when_the_variable_is_set(
        app_window, monkeypatch, caplog):
    import logging

    monkeypatch.delenv("OPAQUE_SELF_CHECK", raising=False)
    assert app_window.run_self_check() == -1

    monkeypatch.setenv("OPAQUE_SELF_CHECK", "1")
    with caplog.at_level(logging.WARNING, logger="opaque.view.self_check"):
        count = app_window.run_self_check()
    assert count >= 0
```

- [ ] **Step 2: Run and confirm it fails** (`AttributeError: run_self_check`)

Run: `uv run python -m pytest tests/view/test_self_check.py -q`

- [ ] **Step 3: Implement.** In `src/opaque/shell.py`:

Add to the imports: `import os` (top block, if absent) and `from opaque.view.self_check import log_interface_problems`.

In `__init__`, near the other private flags, add:

```python
        # The accessibility self check runs once, on the first show, and
        # only when OPAQUE_SELF_CHECK is set. It is a debug aid, not a
        # runtime cost every application pays.
        self._self_check_done: bool = False
```

Near `closeEvent` (line 659), add:

```python
    def run_self_check(self) -> int:
        """
        Walk the widget tree and log every accessibility problem found.

        Runs only when the OPAQUE_SELF_CHECK environment variable is set to
        a non-empty value. Returns the number of problems, or -1 when the
        check is disabled.
        """
        if not os.environ.get("OPAQUE_SELF_CHECK"):
            return -1
        return log_interface_problems(self)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._self_check_done:
            self._self_check_done = True
            self.run_self_check()
```

(`QShowEvent` comes from `PySide6.QtGui`; add it to the existing `QtGui` import that already brings `QCloseEvent`.)

- [ ] **Step 4: Verify**

Run: `uv run python -m pytest tests/view/test_self_check.py -q` → pass. Full suite, mypy, pylint → clean.

- [ ] **Step 5: Update the docs in the same commit.** In `src/opaque/view/self_check.py`, module docstring line 15-16: replace "Call check_interface on a window in a debug build and read the report." with:

```
Set the OPAQUE_SELF_CHECK environment variable and the shell runs
log_interface_problems on the main window at first show. check_interface
stays callable directly on any window.
```

In `CLAUDE.md`, add one line to the Architecture section (after the theme-repaint bullet):

```markdown
- **Accessibility self check**: set `OPAQUE_SELF_CHECK=1` and the shell logs every undersized or unlabeled control at first show (`view/self_check.py`, `BaseApplication.run_self_check()`).
```

- [ ] **Step 6: Commit**

```bash
git add src/opaque/shell.py src/opaque/view/self_check.py tests/view/test_self_check.py CLAUDE.md
git commit -m "feat(shell): run the accessibility self check when OPAQUE_SELF_CHECK is set"
```

---

### Task 6: `FileSelector` widget

A small widget for `UIType.FILE_SELECTOR`: a line edit plus a browse button. Lives in its own module, like `color_picker.py`.

**Files:**
- Create: `src/opaque/view/widgets/file_selector.py`
- Modify: `src/opaque/view/widgets/__init__.py` (add the export, matching how the file exports `CloseableTabWidget`)
- Test: `tests/view/test_file_selector.py`

- [ ] **Step 1: Write the failing test.** Create `tests/view/test_file_selector.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the FileSelector settings widget."""

from opaque.view.widgets.file_selector import FileSelector


def test_typing_a_path_emits_the_signal(qtbot):
    widget = FileSelector(initial_path="")
    qtbot.addWidget(widget)
    received = []
    widget.pathChanged.connect(received.append)

    widget.path_edit.setText("C:/data/input.csv")

    assert received == ["C:/data/input.csv"]
    assert widget.path() == "C:/data/input.csv"


def test_the_initial_path_is_shown(qtbot):
    widget = FileSelector(initial_path="C:/start.txt")
    qtbot.addWidget(widget)
    assert widget.path() == "C:/start.txt"


def test_the_controls_have_accessible_names(qtbot):
    widget = FileSelector(initial_path="")
    qtbot.addWidget(widget)
    assert widget.path_edit.accessibleName().strip()
    assert widget.browse_button.text().strip()
```

- [ ] **Step 2: Run and confirm it fails** (module does not exist)

Run: `uv run python -m pytest tests/view/test_file_selector.py -q`

- [ ] **Step 3: Implement.** Create `src/opaque/view/widgets/file_selector.py`:

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

A file path entry for the settings dialog: a line edit plus a browse button.
The settings dialog builds one for every field declared with
UIType.FILE_SELECTOR.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

from opaque.view.theme import MINIMUM_HIT_TARGET


class FileSelector(QWidget):
    """One file path, editable by hand or through the platform dialog."""

    pathChanged = Signal(str)

    def __init__(self, initial_path: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.path_edit = QLineEdit(initial_path)
        self.path_edit.setAccessibleName(self.tr("File path"))
        self.path_edit.textChanged.connect(self.pathChanged.emit)
        layout.addWidget(self.path_edit)

        self.browse_button = QPushButton(self.tr("Browse..."))
        self.browse_button.setMinimumHeight(MINIMUM_HIT_TARGET)
        self.browse_button.clicked.connect(self._browse)
        layout.addWidget(self.browse_button)

    def path(self) -> str:
        """The current path text."""
        return self.path_edit.text()

    def _browse(self) -> None:
        """Open the platform file dialog and take its answer."""
        chosen, _selected_filter = QFileDialog.getOpenFileName(
            self, self.tr("Select a file"), self.path_edit.text())
        if chosen:
            self.path_edit.setText(chosen)
```

- [ ] **Step 4: Verify**

Run: `uv run python -m pytest tests/view/test_file_selector.py -q` → 3 pass. mypy and pylint on `src/opaque` → clean.

- [ ] **Step 5: Commit**

```bash
git add src/opaque/view/widgets/file_selector.py src/opaque/view/widgets/__init__.py tests/view/test_file_selector.py
git commit -m "feat(widgets): a FileSelector widget for the settings dialog"
```

---

### Task 7: `ListEditor` widget

A small widget for `UIType.LIST_VIEW`: an editable list with add and remove buttons.

**Files:**
- Create: `src/opaque/view/widgets/list_editor.py`
- Modify: `src/opaque/view/widgets/__init__.py` (add the export)
- Test: `tests/view/test_list_editor.py`

- [ ] **Step 1: Write the failing test.** Create `tests/view/test_list_editor.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the ListEditor settings widget."""

from opaque.view.widgets.list_editor import ListEditor


def test_the_initial_items_are_shown(qtbot):
    widget = ListEditor(initial_items=["a", "b"])
    qtbot.addWidget(widget)
    assert widget.items() == ["a", "b"]


def test_adding_an_item_emits_the_new_list(qtbot):
    widget = ListEditor(initial_items=["a"])
    qtbot.addWidget(widget)
    received = []
    widget.itemsChanged.connect(received.append)

    widget.add_button.click()

    assert len(widget.items()) == 2
    assert received and len(received[-1]) == 2


def test_removing_the_selected_item_emits_the_new_list(qtbot):
    widget = ListEditor(initial_items=["a", "b"])
    qtbot.addWidget(widget)
    received = []
    widget.itemsChanged.connect(received.append)

    widget.list_widget.setCurrentRow(0)
    widget.remove_button.click()

    assert widget.items() == ["b"]
    assert received[-1] == ["b"]


def test_editing_an_item_emits_the_new_list(qtbot):
    widget = ListEditor(initial_items=["a"])
    qtbot.addWidget(widget)
    received = []
    widget.itemsChanged.connect(received.append)

    widget.list_widget.item(0).setText("changed")

    assert widget.items() == ["changed"]
    assert received[-1] == ["changed"]
```

- [ ] **Step 2: Run and confirm it fails** (module does not exist)

Run: `uv run python -m pytest tests/view/test_list_editor.py -q`

- [ ] **Step 3: Implement.** Create `src/opaque/view/widgets/list_editor.py`:

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

A list-of-strings editor for the settings dialog. The settings dialog builds
one for every field declared with UIType.LIST_VIEW; a ListField declares it
by default.
"""

from typing import List, Optional, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from opaque.view.theme import MINIMUM_HIT_TARGET


class ListEditor(QWidget):
    """An editable list of strings with add and remove buttons."""

    itemsChanged = Signal(list)

    def __init__(
            self,
            initial_items: Optional[Sequence[str]] = None,
            parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.list_widget = QListWidget()
        self.list_widget.setAccessibleName(self.tr("List items"))
        for text in (initial_items or []):
            self._append_item(str(text))
        layout.addWidget(self.list_widget)

        buttons = QHBoxLayout()
        self.add_button = QPushButton(self.tr("Add"))
        self.add_button.setMinimumHeight(MINIMUM_HIT_TARGET)
        self.add_button.clicked.connect(self._add_item)
        buttons.addWidget(self.add_button)

        self.remove_button = QPushButton(self.tr("Remove"))
        self.remove_button.setMinimumHeight(MINIMUM_HIT_TARGET)
        self.remove_button.clicked.connect(self._remove_selected)
        buttons.addWidget(self.remove_button)
        layout.addLayout(buttons)

        # Connected after the initial fill, so building the widget does not
        # announce a change nobody made.
        self.list_widget.itemChanged.connect(lambda _item: self._emit())

    def items(self) -> List[str]:
        """The current items, top to bottom."""
        return [
            self.list_widget.item(row).text()
            for row in range(self.list_widget.count())
        ]

    def _append_item(self, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.list_widget.addItem(item)

    def _add_item(self) -> None:
        self._append_item(self.tr("new item"))
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)
        self._emit()

    def _remove_selected(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0:
            return
        self.list_widget.takeItem(row)
        self._emit()

    def _emit(self) -> None:
        self.itemsChanged.emit(self.items())
```

- [ ] **Step 4: Verify**

Run: `uv run python -m pytest tests/view/test_list_editor.py -q` → 4 pass. mypy, pylint → clean.

- [ ] **Step 5: Commit**

```bash
git add src/opaque/view/widgets/list_editor.py src/opaque/view/widgets/__init__.py tests/view/test_list_editor.py
git commit -m "feat(widgets): a ListEditor widget for the settings dialog"
```

---

### Task 8: Settings dialog branches for TEXTAREA, SLIDER, LIST_VIEW, FILE_SELECTOR

The four `UIType` members fall to the `QLineEdit` catch-all today (`settings.py:473-480`). Build the four branches with the widgets from Tasks 6-7, and give `ListField` its `ui_type`.

**Files:**
- Modify: `src/opaque/view/dialogs/settings.py` (imports at lines 16-27; branches before the `else` at line 473)
- Modify: `src/opaque/models/annotations.py:26,189-190`
- Test: `tests/view/test_settings_dialog.py`

- [ ] **Step 1: Write the failing tests** (append to `tests/view/test_settings_dialog.py`):

```python
from PySide6.QtWidgets import QPlainTextEdit, QSlider

from opaque.models.annotations import UIType
from opaque.view.widgets.file_selector import FileSelector
from opaque.view.widgets.list_editor import ListEditor


class RichModel(AbstractModel):
    FEATURE_ID = "rich"

    notes = StringField(default="line one", description="Notes",
                        settings=True, ui_type=UIType.TEXTAREA)
    volume = IntField(default=3, min_value=0, max_value=10,
                      description="Volume", settings=True,
                      ui_type=UIType.SLIDER)
    tags = ListField(default=["a", "b"], description="Tags", settings=True)
    source = StringField(default="C:/in.csv", description="Source",
                         settings=True, ui_type=UIType.FILE_SELECTOR)

    def feature_name(self) -> str:
        return "Rich"

    def feature_icon(self):
        from PySide6.QtGui import QIcon
        return QIcon()


@pytest.fixture
def rich_dialog(qtbot, service):
    presenter = DemoPresenter(RichModel())
    presenter.feature_id = "rich"
    widget = SettingsDialog([presenter], parent=None)
    qtbot.addWidget(widget)
    return widget


def test_a_textarea_field_builds_a_plain_text_edit(rich_dialog):
    editor = _widget_of_type(rich_dialog, QPlainTextEdit)
    assert editor is not None
    assert editor.toPlainText() == "line one"
    editor.setPlainText("edited")
    assert rich_dialog.pending_value("rich", "notes") == "edited"


def test_a_slider_field_builds_a_slider_with_the_declared_bounds(rich_dialog):
    slider = _widget_of_type(rich_dialog, QSlider)
    assert slider is not None
    assert (slider.minimum(), slider.maximum()) == (0, 10)
    slider.setValue(7)
    assert rich_dialog.pending_value("rich", "volume") == 7


def test_a_list_field_builds_a_list_editor_and_keeps_the_list_type(rich_dialog):
    editor = _widget_of_type(rich_dialog, ListEditor)
    assert editor is not None
    assert editor.items() == ["a", "b"]
    editor.list_widget.setCurrentRow(0)
    editor.remove_button.click()
    assert rich_dialog.pending_value("rich", "tags") == ["b"]


def test_a_file_selector_field_builds_a_file_selector(rich_dialog):
    selector = _widget_of_type(rich_dialog, FileSelector)
    assert selector is not None
    assert selector.path() == "C:/in.csv"
    selector.path_edit.setText("C:/other.csv")
    assert rich_dialog.pending_value("rich", "source") == "C:/other.csv"
```

- [ ] **Step 2: Run and confirm all four fail** (each `_widget_of_type` returns `None` — the fields fall to `QLineEdit` today)

Run: `uv run python -m pytest tests/view/test_settings_dialog.py -q`

- [ ] **Step 3: Implement the dialog branches.** In `src/opaque/view/dialogs/settings.py`:

Extend the `QtWidgets` import (line 16-20) with `QPlainTextEdit, QSlider`, and add below the `ColorPicker` import (line 26):

```python
from opaque.view.widgets.file_selector import FileSelector
from opaque.view.widgets.list_editor import ListEditor
```

Insert the four branches after the `COLOR_PICKER` branch (line 467-472) and before the final `else` (line 473):

```python
            elif hasattr(field, 'ui_type') and field.ui_type == UIType.TEXTAREA:
                widget = QPlainTextEdit()
                widget.setPlainText(field.display(current_value))
                # textChanged carries no argument; read the widget instead.
                widget.textChanged.connect(
                    lambda fid=feature_id, name=name,
                    editor=widget: self._record_pending(
                        fid, name, editor.toPlainText())
                )
            elif hasattr(field, 'ui_type') and field.ui_type == UIType.SLIDER:
                widget = QSlider(Qt.Orientation.Horizontal)
                # A slider needs both ends. A field that declares neither
                # gets the Qt default of 0-99, which is at least visible on
                # the slider itself, unlike the spinbox case.
                if hasattr(field, 'min_value') and field.min_value is not None:
                    widget.setMinimum(int(field.min_value))
                if hasattr(field, 'max_value') and field.max_value is not None:
                    widget.setMaximum(int(field.max_value))
                widget.setValue(int(current_value))
                widget.valueChanged.connect(
                    lambda value, fid=feature_id, name=name: self._record_pending(
                        fid, name, value)
                )
            elif hasattr(field, 'ui_type') and field.ui_type == UIType.LIST_VIEW:
                widget = ListEditor(initial_items=[
                    str(item) for item in (current_value or [])])
                widget.itemsChanged.connect(
                    lambda items, fid=feature_id, name=name: self._record_pending(
                        fid, name, items)
                )
            elif hasattr(field, 'ui_type') and field.ui_type == UIType.FILE_SELECTOR:
                widget = FileSelector(initial_path=field.display(current_value))
                widget.pathChanged.connect(
                    lambda path, fid=feature_id, name=name: self._record_pending(
                        fid, name, path)
                )
```

- [ ] **Step 4: Give `ListField` its declared UI.** In `src/opaque/models/annotations.py`:

Line 26: remove the `# TODO TBD` comment from `FILE_SELECTOR` (the member is real now).

`ListField.__init__` (lines 189-190) becomes:

```python
    def __init__(self, **kwargs: Any):
        super().__init__(ui_type=UIType.LIST_VIEW, **kwargs)
```

Update the `ListField` class docstring (line 187): replace "Shown and edited as comma separated text." with "Shown and edited as a list; coerce() still accepts comma separated text for old settings files."

- [ ] **Step 5: Verify**

Run: `uv run python -m pytest tests -q` → all pass (watch `tests/models/test_field_coercion.py` and `tests/test_notification_settings.py` — if one asserted that a `ListField` renders a line edit, update that assertion to `ListEditor` in the same commit and say so in the commit body).
Run: `uv run python -m mypy src/opaque` and `uv run python -m pylint src/opaque` → clean.

- [ ] **Step 6: Update `docs/QUICK_REFERENCE.md` in the same commit.** In the field table section, document that `ListField` renders a list editor and that `UIType.TEXTAREA`, `UIType.SLIDER`, `UIType.LIST_VIEW`, `UIType.FILE_SELECTOR` are now real widgets (state which Qt widget each builds).

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/dialogs/settings.py src/opaque/models/annotations.py tests/view/test_settings_dialog.py docs/QUICK_REFERENCE.md
git commit -m "feat(settings): real widgets for TEXTAREA, SLIDER, LIST_VIEW and FILE_SELECTOR"
```

---

### Task 9: Delete `examples/my_example`; move the quickstart UI into `setup_ui()`

`my_example` duplicates `basic_example` patterns and contains the double-cleanup defect (`on_view_close` calling `cleanup()`). The quickstart — the file every user copies first — builds its UI in `__init__` although the documented recipe is `setup_ui()`.

**Files:**
- Delete: `examples/my_example/` (whole directory)
- Modify: `examples/quickstart/main.py:57-66`
- Modify: `README.md` (the quickstart block between `<!-- quickstart:begin -->` and `<!-- quickstart:end -->` — must stay byte-identical to the file)

- [ ] **Step 1: Delete the directory**

```bash
git rm -r examples/my_example
```

- [ ] **Step 2: Rewrite `GreetingView`.** In `examples/quickstart/main.py`, replace lines 57-66:

```python
class GreetingView(BaseView):
    """A feature view is one MDI sub-window. setup_ui() builds the widgets;
    the framework calls it at the end of __init__, once self.context exists."""

    def setup_ui(self) -> None:
        self.label = QLabel(self.tr("Hello OPAQUE"))
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self.label)
        self.setWidget(content)
```

- [ ] **Step 3: Sync the README.** Copy the full new text of `examples/quickstart/main.py` over the README block between `<!-- quickstart:begin -->` and `<!-- quickstart:end -->` (replace only what is inside the fenced python block between the markers). Also fix the README table row (line 159): "A widget tree, built in `__init__`, handed to `setWidget()`." becomes "A widget tree, built in `setup_ui()`, handed to `setWidget()`."

- [ ] **Step 4: Verify**

Run: `uv run python -m pytest tests/test_quickstart.py tests/test_documentation.py -q`
Expected: pass — the byte-identity test proves the README block matches, and the quickstart still builds headless.
Run: `uv run python -m pytest tests -q` → all pass.

- [ ] **Step 5: Commit**

```bash
git add examples/quickstart/main.py README.md
git commit -m "refactor(examples): quickstart builds its view in setup_ui, and my_example is gone"
```

---

### Task 10: Bring the remaining examples up to the framework rules, with a guard test

Violations to remove (all verified 2026-09-09): literal colours and font sizes in stylesheets, views building UI in `__init__`, and user-visible strings outside `self.tr()`. A new guard test makes the colour and structure rules permanent; the failing test names every offender, so fix until green.

**Files:**
- Create: `tests/test_example_hygiene.py`
- Modify: `examples/basic_example/features/calculator/view.py:88-106`
- Modify: `examples/basic_example/features/notification_tester/view.py:35`
- Modify: `examples/basic_example/features/tab_manager/view.py:117`
- Modify: `examples/closeable_tab_example/main.py:155-176`
- Modify: `examples/notification_example/main.py:69-70,104-105`
- Modify: every example view/widget module — wrap user-visible literals in `self.tr()`

- [ ] **Step 1: Write the guard test.** Create `tests/test_example_hygiene.py`:

```python
# This Python file uses the following encoding: utf-8
"""
The examples must obey the framework's own stated rules.

An example is what a user or an AI agent copies. An example that breaks a
rule teaches the violation, so the rules that can be checked mechanically
are checked here: no literal colour or font size inside setStyleSheet, no
cleanup() call inside on_view_close, no BaseView subclass that overrides
__init__ instead of setup_ui, and no tr() call without a literal argument.
"""

import ast
import re
from pathlib import Path
from typing import List, Tuple

import pytest

from tests.test_localisation import _non_literal_tr_calls

EXAMPLES_ROOT = Path(__file__).resolve().parents[1] / "examples"

# Hex colours, font sizes, and the named CSS colours the examples used.
_LITERAL_STYLE = re.compile(
    r"#[0-9a-fA-F]{3,8}\b"
    r"|font-size\s*:"
    r"|\bcolor\s*:\s*(gray|grey|white|black|red|green|blue)\b"
)


def _example_files() -> List[Path]:
    return sorted(EXAMPLES_ROOT.rglob("*.py"))


def _stylesheet_offenders(path: Path) -> List[Tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: List[Tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "setStyleSheet":
            continue
        for part in ast.walk(node):
            if (isinstance(part, ast.Constant)
                    and isinstance(part.value, str)
                    and _LITERAL_STYLE.search(part.value)):
                offenders.append((node.lineno, part.value.strip()))
    return offenders


@pytest.mark.parametrize(
    "path", _example_files(),
    ids=lambda p: str(p.relative_to(EXAMPLES_ROOT)))
def test_no_literal_colour_or_font_size_in_a_stylesheet(path):
    offenders = _stylesheet_offenders(path)
    assert not offenders, (
        f"{path}: literal colour or font size in setStyleSheet at "
        f"{offenders}. Use the tokens in opaque.view.theme instead."
    )


@pytest.mark.parametrize(
    "path", _example_files(),
    ids=lambda p: str(p.relative_to(EXAMPLES_ROOT)))
def test_on_view_close_never_calls_cleanup(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "on_view_close":
            continue
        for call in ast.walk(node):
            if (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "cleanup"):
                pytest.fail(
                    f"{path}:{call.lineno}: on_view_close() calls cleanup(). "
                    f"The framework calls cleanup() itself after the hook."
                )


@pytest.mark.parametrize(
    "path", _example_files(),
    ids=lambda p: str(p.relative_to(EXAMPLES_ROOT)))
def test_a_view_subclass_overrides_setup_ui_and_not_init(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        base_names = {
            base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
            for base in node.bases
        }
        if "BaseView" not in base_names:
            continue
        methods = {
            item.name for item in node.body
            if isinstance(item, ast.FunctionDef)
        }
        assert "__init__" not in methods, (
            f"{path}: view {node.name} overrides __init__. Build the "
            f"widgets in setup_ui(); the framework calls it."
        )
        assert "setup_ui" in methods, (
            f"{path}: view {node.name} does not override setup_ui()."
        )


@pytest.mark.parametrize(
    "path", _example_files(),
    ids=lambda p: str(p.relative_to(EXAMPLES_ROOT)))
def test_every_tr_call_carries_a_literal(path):
    offenders = _non_literal_tr_calls(path)
    assert not offenders, (
        f"{path}: tr() without a string literal at {offenders}. "
        f"lupdate cannot extract a variable."
    )
```

- [ ] **Step 2: Run it and collect the offender list**

Run: `uv run python -m pytest tests/test_example_hygiene.py -q`
Expected: FAIL, with one message per offender. The known list: `basic_example/features/calculator/view.py` (`#4CAF50`, `#45a049`, `color: white`, two `font-size`), `basic_example/features/notification_tester/view.py:35` (`font-size: 16px`), `basic_example/features/tab_manager/view.py:117` (`color: gray`), `closeable_tab_example/main.py` (`color: gray`, view `__init__`), `notification_example/main.py` (`font-size: 16px`, `background-color: #f0f0f0`).

- [ ] **Step 3: Fix the calculator.** In `examples/basic_example/features/calculator/view.py`, replace lines 88-106 with:

```python
            # Style operator buttons differently. Colours and sizes come
            # from the theme tokens; a widget never writes a literal.
            if text in ['+', '-', '*', '/', '=']:
                button.setStyleSheet(
                    f"QPushButton {{"
                    f" background-color: {interactive()};"
                    f" color: {on_interactive()};"
                    f" font-weight: bold;"
                    f" }}")
            button.setFont(TypeScale.body())
```

and add to the module's theme import (or create it):

```python
from opaque.view.theme import TypeScale, interactive, on_interactive
```

(`examples/basic_example/features/calculator/model.py:43` keeps its `default="#4CAF50"` — that is a colour-picker value, data, not a widget literal, and the guard only scans `setStyleSheet`.)

- [ ] **Step 4: Fix the three label styles.**

`examples/basic_example/features/notification_tester/view.py:35` — replace the `setStyleSheet("font-size: 16px; ...")` on the title label with:

```python
        title.setFont(TypeScale.h2())
```

`examples/basic_example/features/tab_manager/view.py:117` and `examples/closeable_tab_example/main.py:163` — replace `info.setStyleSheet("padding: 5px; color: gray;")` (wording varies; keep the padding) with:

```python
        info.setStyleSheet(f"padding: 5px; color: {muted_on_surface()};")
```

`examples/notification_example/main.py:70` — replace the title stylesheet with `title.setFont(TypeScale.h2())`; line 105 — replace the status-label stylesheet with:

```python
        self.status_label.setStyleSheet(
            f"margin-top: 20px; padding: 10px;"
            f" background-color: {surface_variant()};")
```

Add the needed imports to each file: `from opaque.view.theme import TypeScale, muted_on_surface, surface_variant` (only the names each file uses).

- [ ] **Step 5: Fix the closeable-tab view structure.** In `examples/closeable_tab_example/main.py`, replace the `TabExampleView.__init__` (lines 155-176) with a `setup_ui()` override (same body, no `super().__init__` call, no signature):

```python
class TabExampleView(BaseView):
    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        info = QLabel(self.tr(
            "Use the 'Add Tab' menu in the main window toolbar "
            "or the + button below."))
        info.setStyleSheet(f"padding: 5px; color: {muted_on_surface()};")
        layout.addWidget(info)

        self.tab_widget = CloseableTabWidget(
            widget_type=TextWidget,
            default_tab_name=self.tr("Text Editor"),
            minimum_tabs=0,
            show_plus_tab=True
        )
        layout.addWidget(self.tab_widget)

        self.setWidget(QWidget())
        self.widget().setLayout(layout)
```

Check every other `BaseView` subclass the structure test flags the same way (the test in Step 1 finds them all; `basic_example` is already correct).

- [ ] **Step 6: Wrap user-visible strings in `self.tr()`.** In each example view/widget file the guard cannot enforce this fully, so sweep by hand: every string handed to a `QLabel`, `QPushButton`, `setWindowTitle`, `setToolTip`, `setAccessibleName`, notification `title=`/`message=`, or tab name becomes `self.tr("...")` (inside a `QWidget` subclass) — see Step 5 for the pattern. Strings that are not user-visible (service names, `FEATURE_ID`, log messages, dictionary keys) stay bare. Files to sweep: `basic_example/features/*/view.py`, `basic_example/main.py`, `closeable_tab_example/main.py`, `console_example/main.py`, `notification_example/main.py`.

- [ ] **Step 7: Verify**

Run: `uv run python -m pytest tests/test_example_hygiene.py -q` → all pass.
Run: `uv run python -m pytest tests -q` → all pass (this proves every example still imports: `tests/test_example_app.py` and `tests/test_example_services.py` still hold).
Run: `uv run python examples/basic_example/main.py` briefly — the window must open with themed calculator buttons; close it.

- [ ] **Step 8: Commit**

```bash
git add tests/test_example_hygiene.py examples
git commit -m "refactor(examples): obey the theme, i18n and lifecycle rules, and guard them"
```

---

### Task 11: Ignore and delete the leftover local artifacts

**Files:**
- Modify: `.gitignore`
- Delete (untracked, local only): `examples/console_example/logs/`, `examples/notification_example/logs/`, `asdasd.wks`, `logs/`

- [ ] **Step 1: Add the ignore rule.** In `.gitignore`, extend the existing comment block about logs (near the end, after "# The logs and the single instance lock now live under...") with:

```
# Log folders written next to the examples by versions before the move.
examples/**/logs/
```

- [ ] **Step 2: Delete the leftovers** (all untracked; verify with `git status --short` before and after — it must stay empty):

```bash
rm -rf examples/console_example/logs examples/notification_example/logs logs asdasd.wks
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore the example log folders and drop local leftovers"
```

---

### Task 12: Documentation truth pass

Every item verified false or stale on 2026-09-09, fixed in one commit. No code changes here; run the suite once at the end.

**Files:**
- Modify: `docs/QUICK_REFERENCE.md`, `CLAUDE.md`, `README.md`, `docs/ENGINEERING_REVIEW.md`, `docs/ENGINEERING_REVIEW_2026-09-09.md`, `src/opaque/features/context.py`, `src/opaque/view/dialogs/keyboard_map.py`, `tests/test_documentation.py`

- [ ] **Step 1: `docs/QUICK_REFERENCE.md`**
  - Line 3: replace with "Every `opaque` import on this page is checked by `tests/test_documentation.py`; the prose is checked by review, not by a test."
  - Line 5: replace with "The worked examples are `examples/quickstart/main.py` (smallest), `examples/basic_example/main.py` (full), plus focused ones: `closeable_tab_example`, `console_example`, `notification_example`."
  - Line 20 (the `BasePresenter` row): "You must write" becomes `` `bind_events()`, `update()`, `on_view_show()`; `on_view_close()` is optional ``.
  - Line 24: replace the sentence after "not the application." with: "It offers the configuration (`context.configuration`), typed service lookups (`context.service(SomeService)`, `context.optional_service(...)`), the application icon (`context.application_icon()`), one way to put a window on screen (`context.show_window(view)`), and `context.shell` — a deliberate escape hatch to the main window for the rare feature that must reach shell-level UI; prefer the narrow members."
  - Line 105 (the `VersionManager` row): replace "not registered by the framework; construct directly with `VersionManager()`" with "`ServiceLocator.get(VersionManager)` — the shell registers it in `BaseApplication.__init__`".

- [ ] **Step 2: `CLAUDE.md`**
  - Line 7: update the reference-applications sentence to name the example set left after Task 9 (quickstart smallest, basic_example full, plus the three focused examples).
  - Line 15: "# full suite, headless, ~3 s" becomes "# full suite, headless, under a minute".
  - Line 46: "…`view/theme/palettes.py` is the only module in the framework that holds a hex colour" becomes "…hex colours live only inside `view/theme/` (`palettes.py`, the `StatusColors` tables in `tokens.py`, and the two anchors in `contrast.py`); no widget holds one".
  - Line 48: append to the i18n rule: "The scan covers `src/opaque`; `tests/test_example_hygiene.py` covers the examples."

- [ ] **Step 3: `README.md`**
  - Line 174: replace the Engineering Review bullet with: "[**Engineering Review**](docs/ENGINEERING_REVIEW.md): the 2026-09-08 audit (historical); [follow-up verification](docs/ENGINEERING_REVIEW_2026-09-09.md) with the remaining small items."
  - In the install section (near line 25), add one line: "Requires Python 3.11 or newer."
  - Examples section (lines 176-179): list the example set left after Task 9, one line each.

- [ ] **Step 4: Source docstrings**
  - `src/opaque/features/context.py:33-35`: replace the "and nothing else" claim with the true member list (same content as the QUICK_REFERENCE fix in Step 1, phrased for a docstring).
  - `src/opaque/view/dialogs/keyboard_map.py:13-14`: "The list is read off the live QAction objects" becomes "The list is read off the live QAction and QShortcut objects".

- [ ] **Step 5: `tests/test_documentation.py`**: in the comment above `SKIPPED_FILES` (lines 29-35), drop the counts ("The six files below" → "The files below", "None of the six" → "None of them") so the number cannot go stale again. Then delete this plan's own entry (`2026-09-09-review-followup-fixes.md`) from `SKIPPED_FILES` — Tasks 6 and 7 made its imports real — and confirm `uv run python -m pytest tests/test_documentation.py -q` passes without it.

- [ ] **Step 6: Correct the closure table in `docs/ENGINEERING_REVIEW.md` §9** (it is a historical record; correct it, do not rewrite it):
  - In the 3.11 row: change the claim that `self_check.py` wiring was closed by Task 4 to: "self_check wiring was NOT closed by `4dbbd3b` (only the hit-target token moved); it was closed later — see `ENGINEERING_REVIEW_2026-09-09.md` and the review-followup plan."
  - In the 4.1 row: append "(typed lookups only; the `create_services` replacement seam was not built — accepted, see the decision below)".
  - In the "Items accepted rather than fixed" table, add a row: "`create_services` seam (4.1 second half) | Accepted 2026-09-09: services are constructed inline in the shell and are not replaceable by subclasses. Revisit only if a real application needs to substitute a built-in service."

- [ ] **Step 7: Update `docs/ENGINEERING_REVIEW_2026-09-09.md`**: in section 6, mark the decisions taken (validator runs; four widgets built; self_check wired; my_example deleted; create_services accepted) and note this plan as the executor.

- [ ] **Step 8: Verify and commit**

Run: `uv run python -m pytest tests -q` → all pass (`test_documentation.py` re-checks every import in the changed Markdown).

```bash
git add docs CLAUDE.md README.md src/opaque/features/context.py src/opaque/view/dialogs/keyboard_map.py tests/test_documentation.py
git commit -m "docs: one truth pass over the reference, the readme and the closure table"
```

---

## Final verification (after Task 12)

- [ ] `uv run python -m pytest tests -q` → all pass, and `2>&1 | grep -c "Failed to disconnect"` prints `0`.
- [ ] `uv run python -m mypy src/opaque` → "no issues".
- [ ] `uv run python -m pylint src/opaque` → 10.00/10.
- [ ] `uv run python examples/quickstart/main.py` and `uv run python examples/basic_example/main.py` open and close cleanly.
- [ ] `OPAQUE_SELF_CHECK=1 uv run python examples/basic_example/main.py` logs the self-check output (or logs nothing when the tree is clean).
- [ ] `git status --short` is empty.

## Out of scope (stated so the executor does not drift)

- No `create_services` seam (decision recorded in Task 12).
- No change to `context.shell` behaviour — only its documentation.
- No new theme providers, no build_tools work, no CI changes.
- `SingleInstanceService` fixed TCP port: stays accepted-open, untouched.
