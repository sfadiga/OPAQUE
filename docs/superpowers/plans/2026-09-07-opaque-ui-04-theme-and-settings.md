# Plan 04 — Theme Default and Settings Dialog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the theme setting store a valid value, make the Settings dialog report the value that is really applied, and make Cancel undo the edits.

**Architecture:** The dialog stops writing into the model on every keystroke. It collects the edits in a pending dictionary and commits them only on OK or Apply. Cancel then needs no disk reload, because nothing was changed. The theme default becomes a name the theme service can actually apply, and `SettingsService` stops crashing the application when a settings file holds a value that is no longer allowed.

**Tech Stack:** PySide6 `QDialog`, `QFormLayout`, `QComboBox`.

Read **Rules for the executing agent** in `2026-09-07-opaque-ui-00-index.md` before you start.

**Closes:** C4, W13, W14, W15, W16.

**Depends on:** Plan 02 Task 6, which adds `ThemeService.DEFAULT_THEME` and `is_valid_theme`.

**File ownership:** This plan modifies `settings.py`, `app_model.py`, `app_presenter.py` and `settings_service.py`. It does not touch `application.py`. It is safe to run at the same time as Plans 03, 05, 06 and 07.

---

## Background: the theme default can crash the application

The audit reported that the default theme `"light"` is applied as nothing. The real behaviour is worse. Read these three facts together.

1. `ApplicationModel.theme` is declared with `default="light"` and no `choices` (`app_model.py:24-29`).
2. `ApplicationPresenter.__init__` fills that field's `choices` at run time with the real theme list (`app_presenter.py:36-38`).
3. `ModelMeta`'s generated setter **raises `ValueError`** when a value is not in `choices` (`abstract_model.py:41-43`).

`BaseApplication._init_application_settings` builds the presenter first, which fills `choices`, and only then calls `settings_service.register_model`, which calls `setattr(model, "theme", saved_value)` (`settings_service.py:74`). So any user whose `settings.json` holds `"theme": "light"` gets an unhandled `ValueError` and the application does not start.

Task 1 fixes the default. Task 2 makes `SettingsService` refuse to crash on a stale value.

---

## File Structure

| Path | Responsibility |
|---|---|
| Modify `src/opaque/models/app_model.py` | The theme default becomes a valid theme name. |
| Modify `src/opaque/presenters/app_presenter.py` | Coerces an unknown stored theme to the default before applying it. |
| Modify `src/opaque/services/settings_service.py` | A rejected persisted value is logged and skipped, never raised. |
| Modify `src/opaque/view/dialogs/settings.py` | Buffers edits, adds Restore Defaults, drops the modal success box, fixes the search highlight and adds a result count. |
| Create `tests/models/__init__.py` | Test package marker. |
| Create `tests/models/test_settings_service.py` | Proves a stale persisted value cannot crash registration. |
| Create `tests/view/test_settings_dialog.py` | Proves buffering, Cancel, Apply and the search count. |

---

### Task 1: The theme default must be a valid theme name

**Files:**
- Modify: `src/opaque/models/app_model.py:24-29`
- Modify: `src/opaque/presenters/app_presenter.py:33-40`
- Test: `tests/models/test_app_model.py`

- [ ] **Step 1: Write the failing test**

Create `tests/models/__init__.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the OPAQUE model layer."""
```

Create `tests/models/test_app_model.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the application-wide settings model."""

from opaque.models.app_model import ApplicationModel
from opaque.services.theme_service import ThemeService


def test_the_theme_default_is_the_theme_service_default():
    """
    Defect C4. The old default was "light", which no branch of
    ThemeService.apply_theme recognises, so the theme was applied as nothing.
    """
    field = ApplicationModel.get_fields()["theme"]
    assert field.default == ThemeService.DEFAULT_THEME


def test_the_theme_default_is_applicable(qapp):
    service = ThemeService(qapp)
    service.initialize()
    try:
        field = ApplicationModel.get_fields()["theme"]
        assert service.is_valid_theme(field.default)
    finally:
        service.cleanup()


def test_the_language_field_still_offers_its_choices():
    field = ApplicationModel.get_fields()["language"]
    assert field.choices == ["en", "es", "fr"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/models/test_app_model.py -q
```

Expected: FAIL. The first test reports `assert 'light' == 'Default'`.

- [ ] **Step 3: Fix the default**

In `src/opaque/models/app_model.py`, replace this block:

```python
    theme = Field(
        default="light",
        description="Application theme",
        ui_type=UIType.COMBOBOX,
        settings=True
    )
```

with this block:

```python
    # The default must be a name that ThemeService.get_available_themes()
    # returns. "Default" is the one name that is always present. A name that is
    # not on the list is applied as nothing, and the settings dialog then
    # reports a theme the user is not looking at.
    theme = Field(
        default=ThemeService.DEFAULT_THEME,
        description="Application theme",
        ui_type=UIType.COMBOBOX,
        settings=True
    )
```

Then add this import to `src/opaque/models/app_model.py`, below the existing `from opaque.models.annotations import Field, UIType` line:

```python
from opaque.services.theme_service import ThemeService
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/models/test_app_model.py -q
```

Expected: PASS. `3 passed`.

If instead you see `ImportError: cannot import name` or a circular import error, stop and report it. Do not work around it by copying the string `"Default"` into `app_model.py`.

- [ ] **Step 5: Coerce an unknown stored theme in the presenter**

In `src/opaque/presenters/app_presenter.py`, replace this block:

```python
        # --- Theme Management ---
        self.theme_service: ThemeService = ServiceLocator.get_service("themes")
        # Dynamically populate the theme choices
        theme_field = self.model.get_fields().get('theme')
        if theme_field:
            theme_field.choices = self.theme_service.get_available_themes()
        # Apply theme on startup
        self.theme_service.apply_theme(str(self.model.theme))
```

with this block:

```python
        # --- Theme Management ---
        self.theme_service: ThemeService = ServiceLocator.get_service("themes")

        # Fill the choices from the themes that are really installed. The list
        # depends on which optional packages are present, so it cannot be
        # declared on the field.
        theme_field = self.model.get_fields().get('theme')
        if theme_field:
            theme_field.choices = self.theme_service.get_available_themes()

        self._apply_current_theme()

    def _apply_current_theme(self) -> None:
        """
        Apply the theme the model holds, falling back to the default.

        A settings file written by an older version, or by a machine with a
        different set of theme packages, can hold a name this machine cannot
        apply. Replace it instead of leaving the user with no theme and no
        message.
        """
        wanted = str(self.model.theme)
        if not self.theme_service.is_valid_theme(wanted):
            wanted = ThemeService.DEFAULT_THEME
            self.model.theme = wanted
        self.theme_service.apply_theme(wanted)
```

Then replace the whole `apply_settings` method with:

```python
    def apply_settings(self) -> None:
        """Apply the theme when settings are changed."""
        self._apply_current_theme()
```

- [ ] **Step 6: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `68 passed`.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/models/app_model.py src/opaque/presenters/app_presenter.py tests/models
git commit -m "fix(theme): make the default theme a name the theme service can apply"
```

---

### Task 2: A stale persisted value must not crash registration

**Files:**
- Modify: `src/opaque/services/settings_service.py:61-74`
- Test: `tests/models/test_settings_service.py`

- [ ] **Step 1: Write the failing test**

Create `tests/models/test_settings_service.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""Tests for SettingsService robustness against a stale settings file."""

import json

import pytest

from opaque.models.abstract_model import AbstractModel
from opaque.models.annotations import Field
from opaque.services.settings_service import SettingsService


class ChoiceModel(AbstractModel):
    """A model whose field only accepts two values."""

    mode = Field(
        default="fast",
        description="Mode",
        choices=["fast", "slow"],
        settings=True,
    )


@pytest.fixture
def settings_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"demo": {"mode": "gone"}}), encoding="utf-8")
    return path


def test_a_value_outside_choices_does_not_raise(settings_file):
    """
    Defect C4, second half. ModelMeta's setter raises ValueError for a value
    outside choices, and register_model called setattr with no guard. A
    settings file holding an old value stopped the application from starting.
    """
    service = SettingsService(settings_file)
    service.initialize()
    model = ChoiceModel()
    try:
        service.register_model("demo", model)
    finally:
        service.cleanup()


def test_the_field_keeps_its_default_when_the_stored_value_is_rejected(settings_file):
    service = SettingsService(settings_file)
    service.initialize()
    model = ChoiceModel()
    try:
        service.register_model("demo", model)
        assert model.mode == "fast"
    finally:
        service.cleanup()


def test_a_valid_stored_value_is_still_applied(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"demo": {"mode": "slow"}}), encoding="utf-8")
    service = SettingsService(path)
    service.initialize()
    model = ChoiceModel()
    try:
        service.register_model("demo", model)
        assert model.mode == "slow"
    finally:
        service.cleanup()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/models/test_settings_service.py -q
```

Expected: FAIL, with `ValueError: Value 'gone' for 'mode' is not in the allowed choices`.

- [ ] **Step 3: Guard the assignment**

In `src/opaque/services/settings_service.py`, inside `register_model`, replace this block:

```python
                    if hasattr(model.__class__, key) and isinstance(getattr(model.__class__, key), property):
                        if getattr(model.__class__, key).fset is None:
                            continue  # Skip read-only properties
                    setattr(model, key, value)
```

with this block:

```python
                    if hasattr(model.__class__, key) and isinstance(getattr(model.__class__, key), property):
                        if getattr(model.__class__, key).fset is None:
                            continue  # Skip read-only properties
                    try:
                        setattr(model, key, value)
                    except ValueError:
                        # A settings file written by an older version can hold
                        # a value the field no longer allows. Keep the field
                        # default and carry on. Raising here would stop the
                        # application from starting.
                        logging.getLogger(__name__).warning(
                            "Ignoring stored setting %s.%s: value %r is no longer allowed",
                            feature_id, key, value,
                        )
```

Then add this import at the top of `src/opaque/services/settings_service.py`, above the existing imports:

```python
import logging
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/models/test_settings_service.py -q
```

Expected: PASS. `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/opaque/services/settings_service.py tests/models/test_settings_service.py
git commit -m "fix(settings): ignore a stored value the field no longer allows"
```

---

### Task 3: The Settings dialog must buffer its edits

**Files:**
- Modify: `src/opaque/view/dialogs/settings.py`
- Test: `tests/view/test_settings_dialog.py`

- [ ] **Step 1: Write the failing test**

Create `tests/view/test_settings_dialog.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""
Tests for SettingsDialog.

The dialog reads three members from a presenter, so these tests use a
duck-typed double. The model is a real AbstractModel because the dialog calls
type(model).get_fields().
"""

import pytest
from PySide6.QtWidgets import QCheckBox, QLineEdit, QSpinBox

from opaque.models.abstract_model import AbstractModel
from opaque.models.annotations import BoolField, IntField, StringField
from opaque.services.service import ServiceLocator
from opaque.services.settings_service import SettingsService
from opaque.view.dialogs.settings import SettingsDialog


class DemoModel(AbstractModel):
    enabled = BoolField(default=True, description="Enabled", settings=True)
    count = IntField(default=2, min_value=0, max_value=10,
                     description="Count", settings=True)
    label = StringField(default="hello", description="Label", settings=True)
    hidden = StringField(default="secret", description="Hidden")

    def feature_name(self) -> str:
        return "Demo"

    def feature_icon(self):
        from PySide6.QtGui import QIcon
        return QIcon()


class DemoPresenter:
    def __init__(self, model):
        self.feature_id = "demo"
        self.model = model
        self.apply_settings_calls = 0

    def apply_settings(self) -> None:
        self.apply_settings_calls += 1


@pytest.fixture
def service(tmp_path):
    ServiceLocator.cleanup_services()
    settings = SettingsService(tmp_path / "settings.json")
    settings.initialize()
    ServiceLocator.register_service(settings)
    yield settings
    ServiceLocator.cleanup_services()


@pytest.fixture
def dialog(qtbot, service):
    presenter = DemoPresenter(DemoModel())
    widget = SettingsDialog([presenter], parent=None)
    qtbot.addWidget(widget)
    widget._presenter = presenter
    return widget


def _widget_of_type(dialog, widget_type):
    return dialog.scroll_area.widget().findChild(widget_type)


def test_only_fields_marked_as_settings_appear(dialog):
    labels = [label.lower() for label in dialog._current_form_widgets]
    assert "enabled" in labels
    assert "count" in labels
    assert "label" in labels
    assert "hidden" not in labels


def test_editing_a_field_does_not_change_the_model(dialog):
    """Defect W13. The old code wrote to the model on every keystroke."""
    line_edit = _widget_of_type(dialog, QLineEdit)
    line_edit.setText("changed")
    assert dialog._presenter.model.label == "hello"


def test_editing_a_field_records_a_pending_value(dialog):
    line_edit = _widget_of_type(dialog, QLineEdit)
    line_edit.setText("changed")
    assert dialog.pending_value("demo", "label") == "changed"


def test_apply_commits_the_pending_value_to_the_model(dialog):
    line_edit = _widget_of_type(dialog, QLineEdit)
    line_edit.setText("changed")

    dialog._apply_settings()

    assert dialog._presenter.model.label == "changed"


def test_apply_calls_apply_settings_on_the_presenter(dialog):
    dialog._apply_settings()
    assert dialog._presenter.apply_settings_calls == 1


def test_apply_clears_the_pending_edits(dialog):
    line_edit = _widget_of_type(dialog, QLineEdit)
    line_edit.setText("changed")
    dialog._apply_settings()
    assert dialog.has_pending_changes() is False


def test_reject_leaves_the_model_untouched(dialog):
    spin_box = _widget_of_type(dialog, QSpinBox)
    spin_box.setValue(7)
    check_box = _widget_of_type(dialog, QCheckBox)
    check_box.setChecked(False)

    dialog.reject()

    assert dialog._presenter.model.count == 2
    assert dialog._presenter.model.enabled is True


def test_accept_commits_before_closing(dialog):
    spin_box = _widget_of_type(dialog, QSpinBox)
    spin_box.setValue(7)

    dialog.accept()

    assert dialog._presenter.model.count == 7
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_settings_dialog.py -q
```

Expected: FAIL. `test_editing_a_field_does_not_change_the_model` and `test_editing_a_field_records_a_pending_value` both fail, because the old code writes straight through.

- [ ] **Step 3: Add the pending store**

In `src/opaque/view/dialogs/settings.py`, inside `__init__`, directly after this line:

```python
        self._current_form_widgets: Dict[str, QWidget] = {}
```

add these lines:

```python
        # Edits live here until the user presses OK or Apply. Writing straight
        # into the model made Cancel unreliable, because a value that came
        # from a field default was never on disk to reload.
        # Shape: {feature_id: {field_name: new_value}}
        self._pending_values: Dict[str, Dict[str, Any]] = {}
```

Then change the typing import at the top of the file from:

```python
from typing import List, Dict, Optional
```

to:

```python
from typing import Any, Dict, List, Optional
```

- [ ] **Step 4: Add the three pending helpers**

Add these three methods to `SettingsDialog`, directly after `__init__`:

```python
    def _record_pending(self, feature_id: str, field_name: str, value: Any) -> None:
        """Store one edited value. Nothing reaches the model until Apply."""
        self._pending_values.setdefault(feature_id, {})[field_name] = value

    def pending_value(self, feature_id: str, field_name: str) -> Any:
        """Return one pending value, or None when the field was not edited."""
        return self._pending_values.get(feature_id, {}).get(field_name)

    def has_pending_changes(self) -> bool:
        """Return True while at least one edit is waiting to be committed."""
        return any(self._pending_values.values())
```

- [ ] **Step 5: Route every widget signal into the pending store**

In `_on_group_selected`, every `setattr(model, name, ...)` lambda must become a `_record_pending` call. Replace all six connection blocks. The replacements are below, in the same order as the file.

Checkbox:

```python
                widget.stateChanged.connect(
                    lambda state, fid=feature_id, name=name: self._record_pending(
                        fid, name, state == Qt.CheckState.Checked.value)
                )
```

Spin box:

```python
                widget.valueChanged.connect(
                    lambda value, fid=feature_id, name=name: self._record_pending(
                        fid, name, value)
                )
```

Double spin box:

```python
                widget.valueChanged.connect(
                    lambda value, fid=feature_id, name=name: self._record_pending(
                        fid, name, value)
                )
```

Combo box:

```python
                widget.currentTextChanged.connect(
                    lambda text, fid=feature_id, name=name: self._record_pending(
                        fid, name, text)
                )
```

Colour picker:

```python
                widget.colorChanged.connect(
                    lambda color, fid=feature_id, name=name: self._record_pending(
                        fid, name, color)
                )
```

Line edit:

```python
                widget.textChanged.connect(
                    lambda text, fid=feature_id, name=name: self._record_pending(
                        fid, name, text)
                )
```

Note the lambda default argument changed from `model=target_model` to `fid=feature_id`. Keep the default-argument form. Without it, every lambda would capture the last loop value.

- [ ] **Step 6: Commit the pending values in `_apply_settings`**

Replace the whole `_apply_settings` method with exactly this:

```python
    def _apply_settings(self, show_success_message: bool = False) -> None:
        """
        Write the pending edits into the models, then persist them.

        A value that the field rejects is skipped and reported, so one bad
        entry cannot stop the rest of the dialog from saving.
        """
        rejected: List[str] = []

        for feature_id, changes in self._pending_values.items():
            presenter = self.features.get(feature_id)
            if presenter is None:
                continue
            for field_name, value in changes.items():
                try:
                    setattr(presenter.model, field_name, value)
                except ValueError:
                    rejected.append(field_name)

        self._pending_values.clear()

        for feature_id, presenter in self.features.items():
            self.settings_service.save_feature_settings(
                feature_id, presenter.model)
            presenter.apply_settings()

        if rejected:
            QMessageBox.warning(
                self,
                self.tr("Some settings were not saved"),
                self.tr("These settings hold a value that is not allowed: ")
                + ", ".join(rejected),
            )
```

The `show_success_message` argument is kept so the existing `accept` call site stays valid. Task 5 removes it.

- [ ] **Step 7: Make `reject` discard the pending edits**

Add this method directly after `accept`:

```python
    def reject(self) -> None:
        """Discard every pending edit and close.

        No disk reload is needed. Nothing was written to a model, so there is
        nothing to undo.
        """
        self._pending_values.clear()
        super().reject()
```

- [ ] **Step 8: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_settings_dialog.py -q
```

Expected: PASS. `8 passed`.

- [ ] **Step 9: Commit**

```bash
git add src/opaque/view/dialogs/settings.py tests/view/test_settings_dialog.py
git commit -m "fix(settings): buffer dialog edits so Cancel really cancels"
```

---

### Task 4: Restore Defaults

**Files:**
- Modify: `src/opaque/view/dialogs/settings.py`
- Test: `tests/view/test_settings_dialog.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_settings_dialog.py`:

```python
from PySide6.QtWidgets import QDialogButtonBox


def test_the_dialog_offers_restore_defaults(dialog):
    button = dialog.button_box.button(
        QDialogButtonBox.StandardButton.RestoreDefaults)
    assert button is not None


def test_restore_defaults_queues_the_field_defaults(dialog):
    spin_box = _widget_of_type(dialog, QSpinBox)
    spin_box.setValue(7)

    dialog._restore_defaults()

    assert dialog.pending_value("demo", "count") == 2
    assert dialog.pending_value("demo", "label") == "hello"


def test_restore_defaults_does_not_touch_the_model_until_apply(dialog):
    spin_box = _widget_of_type(dialog, QSpinBox)
    spin_box.setValue(7)

    dialog._restore_defaults()

    assert dialog._presenter.model.count == 2

    dialog._apply_settings()

    assert dialog._presenter.model.count == 2


def test_restore_defaults_only_touches_settings_fields(dialog):
    dialog._restore_defaults()
    assert dialog.pending_value("demo", "hidden") is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_settings_dialog.py -q
```

Expected: FAIL, with `AttributeError: 'SettingsDialog' object has no attribute '_restore_defaults'`.

- [ ] **Step 3: Add the button**

In `__init__`, replace the `QDialogButtonBox` construction block:

```python
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
```

with:

```python
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
```

Then, directly after the existing Apply connection, add:

```python
        self.button_box.button(
            QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(
                self._restore_defaults)
```

- [ ] **Step 4: Add the method**

Add this method directly after `_apply_settings`:

```python
    def _restore_defaults(self) -> None:
        """
        Queue the declared default of every settings field.

        The values are queued, not written, so the user can still press Cancel
        after pressing Restore Defaults.
        """
        for feature_id, presenter in self.features.items():
            fields = type(presenter.model).get_fields()
            for name, field in fields.items():
                if not getattr(field, 'is_setting', False):
                    continue
                self._record_pending(feature_id, name, field.default)

        # Redraw the visible form so the widgets show the queued defaults.
        self._on_group_selected()
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_settings_dialog.py -q
```

Expected: PASS. `12 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/dialogs/settings.py tests/view/test_settings_dialog.py
git commit -m "feat(settings): add Restore Defaults that respects Cancel"
```

---

### Task 5: Remove the modal success box

A modal box that confirms the action the user just asked for adds a click and gives no information. The framework already owns a notification system, and the dialog has a status line available.

**Files:**
- Modify: `src/opaque/view/dialogs/settings.py`
- Test: `tests/view/test_settings_dialog.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_settings_dialog.py`:

```python
import inspect

from opaque.view.dialogs import settings as settings_module


def test_apply_settings_takes_no_success_message_argument():
    """Defect W14. The success box is gone, so the flag is gone too."""
    signature = inspect.signature(SettingsDialog._apply_settings)
    assert "show_success_message" not in signature.parameters


def test_apply_reports_success_in_the_status_label(dialog):
    dialog._apply_settings()
    assert dialog.status_label.text() != ""


def test_the_status_label_starts_empty(dialog):
    assert dialog.status_label.text() == ""
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_settings_dialog.py -q
```

Expected: FAIL, on `test_apply_settings_takes_no_success_message_argument`.

- [ ] **Step 3: Add the status label**

In `__init__`, directly before the `layout.addWidget(self.button_box)` line, add:

```python
        # A quiet status line. Applying settings is a routine action, so it
        # gets a line of text and not a modal box.
        self.status_label: QLabel = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
```

- [ ] **Step 4: Change the two signatures and the message**

Change the `accept` method from:

```python
    def accept(self) -> None:
        """Apply settings and accept the dialog."""
        self._apply_settings(show_success_message=False)
        super().accept()
```

to:

```python
    def accept(self) -> None:
        """Apply settings and accept the dialog."""
        self._apply_settings()
        super().accept()
```

Change the `_apply_settings` signature from:

```python
    def _apply_settings(self, show_success_message: bool = False) -> None:
```

to:

```python
    def _apply_settings(self) -> None:
```

Then, at the end of `_apply_settings`, replace the `if rejected:` block with this:

```python
        if rejected:
            self.status_label.setText(
                self.tr("Not saved, value not allowed: ")
                + ", ".join(rejected))
        else:
            self.status_label.setText(self.tr("Settings applied."))
```

- [ ] **Step 5: Remove the unused import**

`QMessageBox` is no longer used in this file. Remove it from the import list at the top. Change:

```python
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QMessageBox, QLabel
```

to:

```python
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QLabel
```

- [ ] **Step 6: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_settings_dialog.py -q
```

Expected: PASS. `15 passed`.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/dialogs/settings.py tests/view/test_settings_dialog.py
git commit -m "fix(settings): replace the modal Apply confirmation with a status line"
```

---

### Task 6: The search highlight and the result count

Two defects here. `color: palette(highlight)` uses a background role as a text colour, so contrast is not guaranteed. And the search gives no count, so the user cannot tell why the group list shrank.

**Files:**
- Modify: `src/opaque/view/dialogs/settings.py`
- Test: `tests/view/test_settings_dialog.py`

- [ ] **Step 1: Write the failing test**

Append these tests to `tests/view/test_settings_dialog.py`:

```python
def test_the_search_highlight_uses_no_style_sheet(dialog):
    """
    Defect W15. palette(highlight) is a background role. Used as a text colour
    it can land anywhere on the contrast scale. The bold weight already
    carries the state.
    """
    dialog.search_bar.setText("count")
    for label in dialog._current_form_widgets.values():
        assert label.styleSheet() == ""


def test_a_matching_field_label_is_emphasised(dialog):
    dialog.search_bar.setText("count")
    label = dialog._current_form_widgets["count"]
    assert label.font().bold() is True


def test_a_non_matching_field_label_is_not_emphasised(dialog):
    dialog.search_bar.setText("count")
    label = dialog._current_form_widgets["label"]
    assert label.font().bold() is False


def test_clearing_the_search_removes_every_emphasis(dialog):
    dialog.search_bar.setText("count")
    dialog.search_bar.setText("")
    for label in dialog._current_form_widgets.values():
        assert label.font().bold() is False


def test_the_search_reports_a_group_count(dialog):
    """Defect W16."""
    dialog.search_bar.setText("count")
    assert "1" in dialog.status_label.text()


def test_a_search_with_no_match_says_so(dialog):
    dialog.search_bar.setText("zzzznomatch")
    assert dialog.status_label.text() != ""
    assert "0" in dialog.status_label.text()


def test_clearing_the_search_clears_the_status(dialog):
    dialog.search_bar.setText("count")
    dialog.search_bar.setText("")
    assert dialog.status_label.text() == ""
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_settings_dialog.py -q
```

Expected: FAIL, on `test_the_search_highlight_uses_no_style_sheet` and on `test_the_search_reports_a_group_count`.

- [ ] **Step 3: Drop the style sheet from both highlight methods**

Replace `_clear_search_highlighting` with exactly this:

```python
    def _clear_search_highlighting(self) -> None:
        """Remove the search emphasis from every field label."""
        for label_widget in self._current_form_widgets.values():
            if isinstance(label_widget, QLabel):
                font = label_widget.font()
                font.setBold(False)
                label_widget.setFont(font)
```

Replace `_highlight_matching_fields` with exactly this:

```python
    def _highlight_matching_fields(self, search_text: str) -> None:
        """
        Emphasise the field labels that match the search text.

        The emphasis is weight only. A colour would need a contrast check
        against whatever background the active theme paints, and the weight
        change already tells the user which row matched.
        """
        for field_name, label_widget in self._current_form_widgets.items():
            if isinstance(label_widget, QLabel):
                font = label_widget.font()
                font.setBold(search_text in field_name.lower())
                label_widget.setFont(font)
```

- [ ] **Step 4: Report the count**

In `_filter_groups`, replace this block near the start:

```python
        if not search_text:
            # Show all items if search is empty
            for i in range(self.groups_list.count()):
                self.groups_list.item(i).setHidden(False)
            # Also clear any highlighting in the current form
            self._clear_search_highlighting()
            return
```

with this block:

```python
        if not search_text:
            # Show all items if search is empty
            for i in range(self.groups_list.count()):
                self.groups_list.item(i).setHidden(False)
            # Also clear any highlighting in the current form
            self._clear_search_highlighting()
            self.status_label.setText("")
            return
```

Then, at the very end of `_filter_groups`, replace this line:

```python
        # Highlight matching fields in the current form
        self._highlight_matching_fields(search_text)
```

with this block:

```python
        # Highlight matching fields in the current form
        self._highlight_matching_fields(search_text)

        # Say how many groups matched. Without a count the user sees a shorter
        # list and cannot tell whether the search worked.
        matched = sum(
            0 if self.groups_list.item(i).isHidden() else 1
            for i in range(self.groups_list.count())
        )
        self.status_label.setText(
            self.tr("Matching groups: ") + str(matched))
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/view/test_settings_dialog.py -q
```

Expected: PASS. `22 passed`.

- [ ] **Step 6: Confirm no colour literal is left in the file**

Run:

```
venv\Scripts\python.exe -c "import pathlib,re; text=pathlib.Path('src/opaque/view/dialogs/settings.py').read_text(encoding='utf-8'); hits=re.findall(r'#[0-9a-fA-F]{6}|rgb\(|color:', text); print(hits or 'CLEAN')"
```

Expected: `CLEAN`.

- [ ] **Step 7: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest -q
```

Expected: `93 passed`.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/dialogs/settings.py tests/view/test_settings_dialog.py
git commit -m "fix(settings): weight-only search emphasis and a match count"
```

---

## Definition of done

- [ ] `venv\Scripts\python.exe -m pytest tests/view/test_settings_dialog.py tests/models -q` passes.
- [ ] `ApplicationModel.get_fields()["theme"].default` equals `ThemeService.DEFAULT_THEME`.
- [ ] A settings file holding `"theme": "light"` no longer stops the application from starting.
- [ ] Editing a field and pressing Cancel leaves the model unchanged.
- [ ] The regex check in Task 6 Step 6 prints `CLEAN`.
