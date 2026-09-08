# Settings Subsystem Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the settings subsystem keep what the user typed: the same type going out of the dialog as went in, a file that survives a crash and a bad parse, and every setting the framework declares actually connected to something.

**Architecture:** The settings path has three independent failures. The dialog builds a widget from `Field.ui_type` and reads back whatever that widget produces, so a float becomes an int and a typed choice becomes a string (review 3.6); the fix gives `Field` one `coerce()` step that the dialog calls before it queues a value, so the widget layer can no longer decide a type. The service writes the JSON file in place and replaces the whole settings dictionary with `{}` when a parse fails, so a truncated write and a bad file both lose everything silently (review 3.7); the fix is an atomic write and a kept copy of the bad file. Twenty-two declared settings reach nothing at all: the notification settings model is never registered, `settings_changed` has no listener, and the language field never reaches `install_translator` (review 3.8); decision D7 says implement them, so this plan connects all three.

**Tech Stack:** Python 3.11, PySide6 (`QSpinBox`, `QDoubleSpinBox`, `QComboBox`, `QLocale`, `QTranslator`), pytest, pytest-qt, `json`, `os.replace`.

**Closes:** review 3.6, review 3.7, review 3.8, decision D7.

**Depends on:** Plan 03 (the theme names the dialog offers) and Plan 04 (one notification per write, and `Field` is documented as shared metadata). The interpreter is `uv run python`.

---

## Rules that apply to every task here

1. Read `docs/superpowers/plans/2026-09-08-techdebt-00-index.md` first. The rules there are binding.
2. Run every command from `C:\Users\sfadiga\sandro\opaque`.
3. `tests/view/test_settings_dialog.py` holds 23 tests and `tests/models/test_settings_service.py` holds more. Every one of them must stay green. Add to those files; do not rewrite them.
4. The dialog already reads exactly three members from each entry it is given: `feature_id`, `model` and `apply_settings()`. `tests/view/test_settings_dialog.py` proves it with a duck-typed double. Task 6 depends on that contract; do not widen it.
5. Every user-visible string is a literal inside `self.tr()`. The status label of the dialog is user-visible.
6. Do not change the identity keys. A feature still has three of them; Plan 06 owns that.

---

## File structure

| File | Responsibility |
|---|---|
| Modify: `src/opaque/models/annotations.py` | `Field.coerce()` and `Field.display()`. `FloatField` gets the right widget type. |
| Create: `tests/models/test_field_coercion.py` | One test per field kind for the round trip. |
| Modify: `src/opaque/view/dialogs/settings.py:110-113, 296-392` | The dialog coerces every value it queues, shows pending values, and keeps the real choice object. |
| Modify: `src/opaque/services/settings_service.py:130-161, 202-252` | An atomic write, a kept copy of a bad file, and utf-8 everywhere. |
| Modify: `src/opaque/models/notification_settings_model.py` | The 22 fields become real settings, `log_file_path` becomes `log_directory`, and the model can name and draw itself. |
| Modify: `src/opaque/presenters/notification_presenter.py` | Register the settings model, expose one settings page, and honour every notification setting. |
| Modify: `src/opaque/view/widgets/notification_widget.py:301-370` | The notification list keeps at most a declared number of rows. |
| Modify: `src/opaque/services/logger_service.py` | A warning can raise a notification, and the setting is readable back. |
| Modify: `src/opaque/view/application.py:60-80, 126-131, 154-174, 395-405` | The stored language reaches the translator, the stored log directory reaches the logger, and `settings_changed` reaches the presenter that cares. |
| Modify: `src/opaque/presenters/app_presenter.py` | Report that a language change needs a restart. |
| Create: `tests/test_notification_settings.py` | The notification settings, from the file to the interface. |
| Create: `tests/test_localisation_setting.py` | The early read of the stored language. |

---

## Task 1: A field knows how to read its own widget

**Files:**
- Modify: `src/opaque/models/annotations.py`
- Test: `tests/models/test_field_coercion.py`

`IntField` and `FloatField` both declare `UIType.SPINBOX`, so a float setting is drawn with a `QSpinBox` and `settings.py:353` calls `int(current_value)`: 2.5 is shown as 2, and 2 is what gets saved. A combo box hands back the display text, so a `ChoiceField` with the choices `[1, 2, 3]` stores `"2"`, which the model setter then rejects. The widget layer must stop deciding types. The field decides.

- [ ] **Step 1: Write the failing test**

Create `tests/models/test_field_coercion.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the widget round trip of every field kind."""

import pytest

from opaque.models.annotations import (
    BoolField,
    ChoiceField,
    Field,
    FloatField,
    IntField,
    ListField,
    StringField,
    UIType,
)


def test_a_float_field_is_drawn_with_a_double_spin_box():
    assert FloatField().ui_type == UIType.DOUBLE_SPINBOX


def test_an_int_field_is_drawn_with_a_spin_box():
    assert IntField().ui_type == UIType.SPINBOX


def test_an_int_field_reads_back_an_int():
    assert IntField().coerce("7") == 7


def test_an_int_field_refuses_text_that_is_not_a_number():
    with pytest.raises(ValueError):
        IntField().coerce("seven")


def test_a_float_field_keeps_the_fraction():
    assert FloatField().coerce("2.5") == 2.5


def test_a_bool_field_reads_back_a_bool():
    field = BoolField()
    assert field.coerce("true") is True
    assert field.coerce("false") is False
    assert field.coerce(1) is True
    assert field.coerce(0) is False


def test_a_string_field_reads_back_a_string():
    assert StringField().coerce(12) == "12"


def test_a_choice_field_reads_back_the_declared_choice_object():
    field = ChoiceField(choices=[1, 2, 3])
    value = field.coerce("2")
    assert value == 2
    assert isinstance(value, int)


def test_a_choice_field_refuses_a_value_that_is_not_a_choice():
    field = ChoiceField(choices=["a", "b"])
    with pytest.raises(ValueError):
        field.coerce("c")


def test_a_plain_field_with_choices_also_maps_back():
    field = Field(choices=[10, 20])
    assert field.coerce("20") == 20


def test_a_plain_field_without_choices_passes_the_value_through():
    marker = object()
    assert Field().coerce(marker) is marker


def test_none_passes_through_every_field_kind():
    for field in (Field(), StringField(), IntField(), FloatField(),
                  BoolField(), ListField(), ChoiceField()):
        assert field.coerce(None) is None


def test_a_list_field_reads_back_a_list_from_comma_separated_text():
    assert ListField().coerce("a, b ,c") == ["a", "b", "c"]


def test_a_list_field_passes_a_real_list_through():
    assert ListField().coerce(["a", "b"]) == ["a", "b"]


def test_an_empty_string_gives_an_empty_list():
    assert ListField().coerce("") == []


def test_a_list_field_is_displayed_comma_separated():
    assert ListField().display(["a", "b"]) == "a, b"


def test_the_display_of_a_list_field_round_trips():
    field = ListField()
    original = ["one", "two", "three"]
    assert field.coerce(field.display(original)) == original


def test_display_of_none_is_an_empty_string():
    assert Field().display(None) == ""


def test_display_of_a_number_is_its_text():
    assert IntField().display(7) == "7"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/models/test_field_coercion.py -q
```

Expected: `test_a_float_field_is_drawn_with_a_double_spin_box` FAILS, and every test that calls `coerce` or `display` FAILS with `AttributeError`.

- [ ] **Step 3: Write the implementation**

In `src/opaque/models/annotations.py`, add these two methods to `Field`, directly after `validate`:

```python
    def coerce(self, value: Any) -> Any:
        """
        Convert a raw widget value into the type this field stores.

        The settings dialog builds a widget from ui_type and reads back
        whatever that widget produces, which is not always the type the field
        holds: a combo box gives display text, a line edit gives a string.
        The dialog calls this before it queues a value, so a round trip
        through the dialog can no longer change a type.

        The base implementation maps a value back onto the declared choice
        object, because a combo box only ever hands back text. A subclass
        calls super().coerce(value) first and then converts.

        None passes through unchanged: an unset value stays unset.

        Raises:
            ValueError: When the value is not one of the declared choices.
        """
        if value is None:
            return None

        if self.choices:
            for choice in self.choices:
                if choice == value or str(choice) == str(value):
                    return choice
            raise ValueError(
                f"{value!r} is not one of the allowed choices for "
                f"'{self.name}': {self.choices}")

        return value

    def display(self, value: Any) -> str:
        """
        Return the value as the text a line edit or a combo box shows.

        The inverse of coerce for the text widgets. Override it when str()
        gives something the user cannot edit back into the same value.
        """
        return "" if value is None else str(value)
```

Then give the subclasses their conversions. Replace the whole block from `class StringField` to the end of the file:

```python
class StringField(Field):
    """Field for string values."""

    def __init__(self, ui_type: UIType = UIType.TEXT, **kwargs: Any):
        super().__init__(ui_type=ui_type, **kwargs)

    def coerce(self, value: Any) -> Any:
        value = super().coerce(value)
        return None if value is None else str(value)


class IntField(Field):
    """Field for integer values."""

    def __init__(self, **kwargs: Any):
        super().__init__(ui_type=UIType.SPINBOX, **kwargs)

    def coerce(self, value: Any) -> Any:
        value = super().coerce(value)
        return None if value is None else int(value)


class FloatField(Field):
    """Field for float values."""

    def __init__(self, **kwargs: Any):
        # A float needs a widget with a fraction. It used to declare
        # UIType.SPINBOX, so the dialog drew a QSpinBox and truncated every
        # value it read back.
        super().__init__(ui_type=UIType.DOUBLE_SPINBOX, **kwargs)

    def coerce(self, value: Any) -> Any:
        value = super().coerce(value)
        return None if value is None else float(value)


class BoolField(Field):
    """Field for boolean values."""

    # The strings a check box or a settings file can hold for True.
    TRUE_WORDS = ("1", "true", "yes", "on")

    def __init__(self, **kwargs: Any):
        super().__init__(ui_type=UIType.CHECKBOX, **kwargs)

    def coerce(self, value: Any) -> Any:
        value = super().coerce(value)
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip().lower() in self.TRUE_WORDS
        return bool(value)


class ListField(Field):
    """Field for list values. Shown and edited as comma separated text."""

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def coerce(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            return list(value)
        text = str(value).strip()
        if not text:
            return []
        return [item.strip() for item in text.split(",")]

    def display(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return ", ".join(str(item) for item in value)
        return str(value)


class ChoiceField(Field):
    """Field for values from a list of choices."""

    def __init__(self, **kwargs: Any):
        super().__init__(ui_type=UIType.DROPDOWN, **kwargs)
```

`ChoiceField` needs no `coerce` of its own: the base implementation maps display text back onto the declared choice, which is the whole job.

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/models/test_field_coercion.py -q
```

Expected: `19 passed`.

- [ ] **Step 5: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. `FloatField` now reports `DOUBLE_SPINBOX`; the dialog already has a `DOUBLE_SPINBOX` branch, so nothing else has to change yet.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/models/annotations.py tests/models/test_field_coercion.py
git commit -m "feat(models): let a field convert and display its own value"
```

---

## Task 2: The dialog queues typed values

**Files:**
- Modify: `src/opaque/view/dialogs/settings.py:110-113` (`_record_pending`), `:360-392` (the combo box and the line edit branches)
- Test: `tests/view/test_settings_dialog.py` (add to it)

Every widget connection in `_on_group_selected` queues the raw signal argument. Task 1 gave the field a `coerce()`; this task calls it in the one place every edit passes through, and stops the combo box from throwing away the declared choice object.

- [ ] **Step 1: Write the failing test**

Add to `tests/view/test_settings_dialog.py`. Extend the import line first:

```python
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit, QSpinBox,
)
```

and the model import line:

```python
from opaque.models.annotations import (
    BoolField, ChoiceField, FloatField, IntField, ListField, StringField,
)
```

Then add this model, this double and these tests at the end of the file:

```python
class TypedModel(AbstractModel):
    """One field of every kind that the dialog can draw."""

    ratio = FloatField(default=2.5, description="Ratio", settings=True)
    level = ChoiceField(default=2, choices=[1, 2, 3],
                        description="Level", settings=True)
    tags = ListField(default=["a", "b"], description="Tags", settings=True)
    count = IntField(default=3, description="Count", settings=True)
    label = StringField(default="hello", description="Label", settings=True)
    enabled = BoolField(default=True, description="Enabled", settings=True)

    def feature_name(self) -> str:
        return "Typed"

    def feature_icon(self):
        from PySide6.QtGui import QIcon
        return QIcon()


@pytest.fixture
def typed_dialog(qtbot, service):
    presenter = DemoPresenter(TypedModel())
    presenter.feature_id = "typed"
    widget = SettingsDialog([presenter], parent=None)
    qtbot.addWidget(widget)
    widget._presenter = presenter
    return widget


def _widget_for(dialog, label):
    """Return the editor widget on the row whose label reads `label`."""
    container = dialog.scroll_area.widget()
    layout = container.layout()
    for row in range(layout.rowCount()):
        label_item = layout.itemAt(row, layout.ItemRole.LabelRole)
        field_item = layout.itemAt(row, layout.ItemRole.FieldRole)
        if label_item is None or field_item is None:
            continue
        if label_item.widget().text() == label:
            return field_item.widget()
    raise AssertionError(f"no row is labelled {label}")


def test_a_float_setting_is_drawn_with_a_double_spin_box(typed_dialog):
    assert isinstance(_widget_for(typed_dialog, "Ratio"), QDoubleSpinBox)


def test_a_float_setting_keeps_its_fraction(typed_dialog):
    widget = _widget_for(typed_dialog, "Ratio")
    widget.setValue(3.25)

    assert typed_dialog.pending_value("typed", "ratio") == 3.25


def test_a_choice_setting_queues_the_declared_choice_object(typed_dialog):
    widget = _widget_for(typed_dialog, "Level")
    assert isinstance(widget, QComboBox)
    widget.setCurrentIndex(2)

    queued = typed_dialog.pending_value("typed", "level")
    assert queued == 3
    assert isinstance(queued, int)


def test_a_choice_setting_starts_on_the_current_value(typed_dialog):
    widget = _widget_for(typed_dialog, "Level")
    assert widget.currentText() == "2"


def test_a_list_setting_is_shown_comma_separated(typed_dialog):
    widget = _widget_for(typed_dialog, "Tags")
    assert isinstance(widget, QLineEdit)
    assert widget.text() == "a, b"


def test_a_list_setting_queues_a_list(typed_dialog):
    widget = _widget_for(typed_dialog, "Tags")
    widget.setText("x, y, z")

    assert typed_dialog.pending_value("typed", "tags") == ["x", "y", "z"]


def test_an_int_setting_queues_an_int(typed_dialog):
    widget = _widget_for(typed_dialog, "Count")
    widget.setValue(9)

    queued = typed_dialog.pending_value("typed", "count")
    assert queued == 9
    assert isinstance(queued, int)


def test_apply_writes_every_typed_value_into_the_model(typed_dialog):
    _widget_for(typed_dialog, "Ratio").setValue(1.75)
    _widget_for(typed_dialog, "Level").setCurrentIndex(0)
    _widget_for(typed_dialog, "Tags").setText("q")

    typed_dialog._apply_settings()

    model = typed_dialog._presenter.model
    assert model.ratio == 1.75
    assert model.level == 1
    assert model.tags == ["q"]


def test_a_value_the_field_refuses_is_reported_and_not_queued(typed_dialog):
    typed_dialog._record_pending("typed", "count", "not a number")

    assert typed_dialog.pending_value("typed", "count") is None
    assert typed_dialog.status_label.text() != ""
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/view/test_settings_dialog.py -q -k "typed or choice_setting or list_setting or float_setting or int_setting or refuses"
```

Expected: `test_a_choice_setting_queues_the_declared_choice_object` FAILS, because the queued value is the string `"3"`. `test_a_list_setting_is_shown_comma_separated` FAILS, because the line edit reads `['a', 'b']`. `test_a_list_setting_queues_a_list` FAILS. `test_a_value_the_field_refuses_is_reported_and_not_queued` FAILS.

- [ ] **Step 3: Coerce in the one place every edit passes through**

In `src/opaque/view/dialogs/settings.py`, replace `_record_pending`, lines 110 to 113. Before:

```python
    def _record_pending(self, feature_id: str, field_name: str, value: Any) -> None:
        """Store one edited value. Nothing reaches the model until Apply."""
        self._pending_values.setdefault(feature_id, {})[field_name] = value
```

After:

```python
    def _record_pending(self, feature_id: str, field_name: str, value: Any) -> None:
        """
        Store one edited value. Nothing reaches the model until Apply.

        The value is converted by the field first. A widget hands back
        whatever type it likes, and a combo box always hands back text, so
        without this step a float arrived as an int and a typed choice
        arrived as a string that the model setter then rejected.
        """
        field = self._field_for(feature_id, field_name)
        if field is not None:
            try:
                value = field.coerce(value)
            except (TypeError, ValueError):
                self.status_label.setText(
                    self.tr("Value not accepted for: ") + field_name)
                return

        self._pending_values.setdefault(feature_id, {})[field_name] = value

    def _field_for(self, feature_id: str, field_name: str) -> Optional[Field]:
        """Return one Field declaration, or None when the name is unknown."""
        presenter = self.features.get(feature_id)
        if presenter is None:
            return None
        return type(presenter.model).get_fields().get(field_name)
```

Add `Field` to the annotations import at the top of the file:

```python
from opaque.models.annotations import Field, UIType
```

- [ ] **Step 4: Keep the real choice object in the combo box**

In `_on_group_selected`, replace the combo box branch. Before:

```python
            elif (hasattr(field, 'ui_type') and field.ui_type == UIType.COMBOBOX) or (hasattr(field, 'choices') and field.choices):
                widget = QComboBox()
                if hasattr(field, 'choices') and field.choices:
                    widget.addItems([str(c) for c in field.choices])
                widget.setCurrentText(str(current_value))
                widget.currentTextChanged.connect(
                    lambda text, fid=feature_id, name=name: self._record_pending(
                        fid, name, text)
                )
```

After:

```python
            elif (field.ui_type in (UIType.COMBOBOX, UIType.DROPDOWN)
                    or field.choices):
                widget = QComboBox()
                # Each item carries the declared choice object as its data,
                # so the queued value keeps the type the field declared. The
                # display text alone loses it: "2" is not 2.
                for choice in (field.choices or []):
                    widget.addItem(field.display(choice), choice)
                index = widget.findText(field.display(current_value))
                if index >= 0:
                    widget.setCurrentIndex(index)
                widget.currentIndexChanged.connect(
                    lambda position, fid=feature_id, name=name,
                    combo=widget: self._record_pending(
                        fid, name, combo.itemData(position))
                )
```

`ApplicationModel.theme` is a plain `Field` with `ui_type=UIType.COMBOBOX` whose `choices` the application presenter fills at run time, so it takes this branch through the first condition. `ChoiceField` declares `UIType.DROPDOWN` and takes it through the second.

- [ ] **Step 5: Show and read text values through the field**

In the same method, replace the final `else` branch. Before:

```python
            else:  # Default to QLineEdit for "text"
                widget = QLineEdit(str(current_value))
                widget.textChanged.connect(
                    lambda text, fid=feature_id, name=name: self._record_pending(
                        fid, name, text)
                )
```

After:

```python
            else:  # Default to QLineEdit for "text"
                # field.display() is the inverse of field.coerce(). A list
                # shown as str(["a", "b"]) cannot be edited back into a list.
                widget = QLineEdit(field.display(current_value))
                widget.textChanged.connect(
                    lambda text, fid=feature_id, name=name: self._record_pending(
                        fid, name, text)
                )
```

- [ ] **Step 6: Run the test to verify it passes**

```bash
uv run python -m pytest tests/view/test_settings_dialog.py -q
```

Expected: every test passes, the 23 that were there and the 9 you added.

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/dialogs/settings.py tests/view/test_settings_dialog.py
git commit -m "fix(settings): keep the declared type through the dialog"
```

---

## Task 3: The form shows what is queued, not what is stored

**Files:**
- Modify: `src/opaque/view/dialogs/settings.py:296-320` (`_on_group_selected`)
- Test: `tests/view/test_settings_dialog.py` (add to it)

`_restore_defaults` queues the declared defaults and then calls `_on_group_selected()` with the comment "Redraw the visible form so the widgets show the queued defaults". The redraw reads `getattr(target_model, name)`, and nothing was written to the model, so the form shows the old values. Pressing Restore Defaults looks like it did nothing. The same happens when the user edits a field, changes group and comes back.

- [ ] **Step 1: Write the failing test**

Add to `tests/view/test_settings_dialog.py`:

```python
def test_restore_defaults_shows_the_defaults_in_the_form(dialog):
    dialog._presenter.model.count = 7
    dialog._on_group_selected()
    assert _widget_for(dialog, "Count").value() == 7

    dialog._restore_defaults()

    assert _widget_for(dialog, "Count").value() == 2


def test_an_edit_survives_a_redraw(dialog):
    _widget_for(dialog, "Count").setValue(6)

    dialog._on_group_selected()

    assert _widget_for(dialog, "Count").value() == 6
    assert dialog.pending_value("demo", "count") == 6


def test_a_text_edit_survives_a_redraw(dialog):
    _widget_for(dialog, "Label").setText("edited")

    dialog._on_group_selected()

    assert _widget_for(dialog, "Label").text() == "edited"


def test_a_check_box_edit_survives_a_redraw(dialog):
    _widget_for(dialog, "Enabled").setChecked(False)

    dialog._on_group_selected()

    assert _widget_for(dialog, "Enabled").isChecked() is False


def test_a_redraw_after_reject_shows_the_model_again(dialog):
    _widget_for(dialog, "Count").setValue(6)
    dialog.reject()

    dialog._on_group_selected()

    assert _widget_for(dialog, "Count").value() == 2
```

`_widget_for` is the helper Task 2 added to this file. `DemoModel.count` has the default 2, `DemoModel.label` the default `"hello"` and `DemoModel.enabled` the default `True`.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/view/test_settings_dialog.py -q -k "survives_a_redraw or restore_defaults_shows"
```

Expected: `test_restore_defaults_shows_the_defaults_in_the_form` FAILS with `assert 7 == 2`. The three `survives_a_redraw` tests FAIL, each showing the stored value instead of the edit.

- [ ] **Step 3: Write the implementation**

In `src/opaque/view/dialogs/settings.py`, add this method directly after `pending_value`:

```python
    def _effective_value(
            self, feature_id: str, field_name: str, model: Any) -> Any:
        """
        Return the value the form must show for one field.

        A queued edit wins over the stored value. Restore Defaults queues
        without writing, and switching group redraws the form, so a redraw
        that read only the model threw away everything the user had done and
        made Restore Defaults look like it had failed.
        """
        pending = self._pending_values.get(feature_id, {})
        if field_name in pending:
            return pending[field_name]
        return getattr(model, field_name)
```

Then, in `_on_group_selected`, replace the line that reads the value. Before:

```python
            current_value = getattr(target_model, name)
```

After:

```python
            current_value = self._effective_value(feature_id, name, target_model)
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/view/test_settings_dialog.py -q
```

Expected: every test passes.

Watch one interaction: building a widget with a queued value emits that widget's own change signal, which calls `_record_pending` again with the same value. That is harmless, because the queued value does not change. Do not add a signal block to work around it; if a test shows a real problem, report it.

- [ ] **Step 5: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 6: Look at the running application**

```bash
uv run python examples/basic_example/main.py
```

Open Settings, change a value, switch to another group in the left list and come back. Expected: your change is still shown. Press Restore Defaults. Expected: every field on the page changes to its default at once. Press Cancel and open Settings again. Expected: the original values are back. Record what you saw.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/dialogs/settings.py tests/view/test_settings_dialog.py
git commit -m "fix(settings): draw the queued edits in the settings form"
```

---

## Task 4: The settings file survives a bad write and a bad parse

**Files:**
- Modify: `src/opaque/services/settings_service.py:130-146`
- Test: `tests/models/test_settings_service.py` (add to it)

`save_settings_file` opens the real file for writing and then serializes into it, so any failure part way through leaves a truncated file, and the next start reads nothing. `load_settings_file` answers a parse failure by setting `self._settings = {}`, which the next save then writes over the user's file. Both paths lose data and both only log it.

- [ ] **Step 1: Write the failing test**

Add to `tests/models/test_settings_service.py`, and extend the import block at the top with:

```python
import os
```

Then add:

```python
def test_a_corrupt_settings_file_is_kept_beside_the_new_one(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ this is not json", encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    try:
        assert service.get_all_settings() == {}
        kept = path.with_suffix(".json.corrupt")
        assert kept.exists()
        assert kept.read_text(encoding="utf-8") == "{ this is not json"
    finally:
        service.cleanup()


def test_a_corrupt_file_is_not_left_in_place_to_fail_again(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ broken", encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    try:
        service.update_feature_settings("demo", {})
        # The service wrote a fresh file, so the next start parses.
        json.loads(path.read_text(encoding="utf-8"))
    finally:
        service.cleanup()


def test_a_failed_write_leaves_the_previous_file_untouched(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"demo": {"mode": "slow"}}), encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    try:
        def _explode(*args, **kwargs):
            raise OSError("the disk is full")

        monkeypatch.setattr(
            "opaque.services.settings_service.json.dump", _explode)

        service.save_settings_file()

        # The old content is still there, and no half written file replaced it.
        assert json.loads(path.read_text(encoding="utf-8")) == {
            "demo": {"mode": "slow"}}
    finally:
        service.cleanup()


def test_a_save_leaves_no_temporary_file_behind(tmp_path):
    path = tmp_path / "settings.json"
    service = SettingsService(path)
    service.initialize()
    try:
        service.update_feature_settings("demo", {})
        names = sorted(entry.name for entry in tmp_path.iterdir())
        assert names == ["settings.json"]
    finally:
        service.cleanup()


def test_a_read_failure_does_not_empty_the_settings_already_held(tmp_path,
                                                                monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"demo": {"mode": "slow"}}), encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    try:
        assert service.get_all_settings() == {"demo": {"mode": "slow"}}

        def _explode(*args, **kwargs):
            raise OSError("the file is locked")

        monkeypatch.setattr(
            "opaque.services.settings_service.open", _explode, raising=False)

        service.load_settings_file()

        assert service.get_all_settings() == {"demo": {"mode": "slow"}}
    finally:
        service.cleanup()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/models/test_settings_service.py -q
```

Expected: `test_a_corrupt_settings_file_is_kept_beside_the_new_one` FAILS, because no `.corrupt` file is written. `test_a_failed_write_leaves_the_previous_file_untouched` FAILS, because the file is left empty. The other three may pass already.

- [ ] **Step 3: Write the implementation**

In `src/opaque/services/settings_service.py`, add `import os` to the import block, then replace `load_settings_file` and `save_settings_file`, lines 130 to 146. Before:

```python
    def load_settings_file(self) -> None:
        """Load settings from file."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self._settings = json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.exception("Failed to load settings")
                self._settings = {}

    def save_settings_file(self) -> None:
        """Save settings to file."""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2)
        except IOError:
            logger.exception("Failed to save settings")
```

After:

```python
    def load_settings_file(self) -> bool:
        """
        Load settings from the file.

        A file that cannot be parsed is moved aside with the suffix
        ".corrupt" and reported, instead of being silently replaced by an
        empty dictionary that the next save then writes over the user's own
        file. A file that cannot be read at all leaves the settings already
        held in memory alone, for the same reason.

        Returns:
            True when the file was read. False when there was nothing to
            read, or when reading failed.
        """
        if not self.settings_file.exists():
            return False

        try:
            with open(self.settings_file, 'r', encoding='utf-8') as handle:
                loaded = json.load(handle)
        except json.JSONDecodeError:
            kept = self.settings_file.with_suffix(
                self.settings_file.suffix + ".corrupt")
            try:
                os.replace(self.settings_file, kept)
                logger.error(
                    "The settings file %s could not be parsed. It was kept as "
                    "%s and the defaults are in use.",
                    self.settings_file, kept)
            except OSError:
                logger.exception(
                    "The settings file %s could not be parsed and could not "
                    "be moved aside", self.settings_file)
            return False
        except OSError:
            logger.exception(
                "The settings file %s could not be read. The settings already "
                "loaded are kept.", self.settings_file)
            return False

        if not isinstance(loaded, dict):
            logger.error(
                "The settings file %s holds %s, not an object. The defaults "
                "are in use.", self.settings_file, type(loaded).__name__)
            return False

        self._settings = loaded
        return True

    def save_settings_file(self) -> bool:
        """
        Save settings to the file, atomically.

        The data is written to a temporary file next to the target and then
        moved onto it, because os.replace is atomic on Windows and on POSIX.
        Writing into the target directly left a truncated file whenever the
        write failed part way, and the next start read nothing.

        Returns:
            True when the file was written.
        """
        temporary = self.settings_file.with_suffix(
            self.settings_file.suffix + ".tmp")
        try:
            with open(temporary, 'w', encoding='utf-8') as handle:
                json.dump(self._settings, handle, indent=2)
            os.replace(temporary, self.settings_file)
            return True
        except (OSError, TypeError, ValueError):
            logger.exception(
                "Failed to save the settings to %s. The previous file is "
                "unchanged.", self.settings_file)
            try:
                if temporary.exists():
                    temporary.unlink()
            except OSError:
                logger.exception(
                    "Failed to remove the temporary file %s", temporary)
            return False
```

`json.dump` raises `TypeError` for a value it cannot serialize, so that is caught with the I/O errors: a value the dialog queued must not be able to destroy the file either.

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/models/test_settings_service.py -q
```

Expected: every test passes, the three that were there and the five you added.

- [ ] **Step 5: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/services/settings_service.py tests/models/test_settings_service.py
git commit -m "fix(settings): write the settings file atomically and keep a bad one"
```

---

## Task 5: One path writes a stored value into a model

**Files:**
- Modify: `src/opaque/services/settings_service.py:56-88, 107-128, 163-174, 202-252`
- Test: `tests/models/test_settings_service.py` (add to it)

Four methods write stored values into models, and each one repeats the same property check with a different amount of care. `register_model` guards `ValueError`; `load_all_settings` does not; `update_feature_settings` writes any key the model happens to have, whether it is a settings field or not; `import_settings` writes with no guard at all. A JSON file also cannot hold a type: an int field comes back as an int only by luck, and comes back as a string from a hand-edited file. `export_settings` and `import_settings` open their files with no encoding, so a non-ASCII value depends on the machine's locale.

- [ ] **Step 1: Write the failing test**

Add to `tests/models/test_settings_service.py`:

```python
class TypedSettingsModel(AbstractModel):
    """A model whose settings fields have real types."""

    count = IntField(default=1, description="Count", settings=True)
    ratio = FloatField(default=0.5, description="Ratio", settings=True)
    label = StringField(default="plain", description="Label", settings=True)
    internal = IntField(default=0, description="Internal")


def test_a_stored_string_arrives_as_the_declared_type(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"demo": {"count": "12", "ratio": "1.25"}}),
        encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        assert model.count == 12
        assert isinstance(model.count, int)
        assert model.ratio == 1.25
    finally:
        service.cleanup()


def test_a_stored_key_that_is_not_a_field_is_ignored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"demo": {"count": 3, "nonsense": 9}}), encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        assert model.count == 3
        assert not hasattr(model, "nonsense")
    finally:
        service.cleanup()


def test_a_field_that_is_not_a_setting_is_not_restored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"demo": {"internal": 99}}), encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        assert model.internal == 0
    finally:
        service.cleanup()


def test_update_feature_settings_ignores_a_key_that_is_not_a_setting(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        service.update_feature_settings("demo", {"internal": 42, "count": 8})
        assert model.count == 8
        assert model.internal == 0
    finally:
        service.cleanup()


def test_update_feature_settings_converts_the_value(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        service.update_feature_settings("demo", {"count": "5"})
        assert model.count == 5
        assert isinstance(model.count, int)
    finally:
        service.cleanup()


def test_load_all_settings_survives_a_value_the_field_refuses(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"demo": {"count": "not a number"}}), encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        service.load_all_settings()
        assert model.count == 1
    finally:
        service.cleanup()


def test_a_non_ascii_value_survives_export_and_import(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        service.update_feature_settings("demo", {"label": "café"})

        exported = tmp_path / "exported.json"
        assert service.export_settings(exported) is True

        other = SettingsService(tmp_path / "other.json")
        other.initialize()
        other_model = TypedSettingsModel()
        other.register_model("demo", other_model)
        assert other.import_settings(exported) is True
        assert other_model.label == "café"
        other.cleanup()
    finally:
        service.cleanup()
```

Extend the import block of the file with:

```python
from opaque.models.annotations import Field, FloatField, IntField, StringField
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/models/test_settings_service.py -q -k "declared_type or not_a_field or not_a_setting or converts_the_value or refuses or non_ascii"
```

Expected: `test_a_stored_string_arrives_as_the_declared_type` FAILS with `assert '12' == 12`. `test_a_field_that_is_not_a_setting_is_not_restored` passes already, because `register_model` checks `is_setting`. `test_update_feature_settings_ignores_a_key_that_is_not_a_setting` FAILS with `assert 42 == 0`. `test_load_all_settings_survives_a_value_the_field_refuses` FAILS with a `ValueError`.

- [ ] **Step 3: Write the one path**

In `src/opaque/services/settings_service.py`, add this method directly after `register_model`:

```python
    def _apply_stored_value(
            self, model: Any, key: str, value: Any) -> bool:
        """
        Write one stored value into one model field, or refuse it.

        This is the only path from stored data into a model. Four methods
        used to do it, each with a different amount of care, so a value that
        one accepted another rejected and a key that was not a field at all
        could be written as a new attribute.

        The value is converted by the field first. JSON holds no types, so a
        file written by an older version, or edited by hand, hands back a
        string where an int was stored.

        Args:
            model: The model to write into.
            key: The field name from the settings file.
            value: The stored value.

        Returns:
            True when the value was written.
        """
        field = type(model).get_fields().get(key)
        if field is None:
            logger.warning(
                "Ignoring the stored setting %s: %s declares no such field",
                key, type(model).__name__)
            return False

        if not field.is_setting:
            logger.warning(
                "Ignoring the stored setting %s: the field is not declared "
                "with settings=True", key)
            return False

        declared = getattr(type(model), key, None)
        if isinstance(declared, property) and declared.fset is None:
            return False

        try:
            setattr(model, key, field.coerce(value))
        except (TypeError, ValueError):
            # A settings file written by an older version, or edited by hand,
            # can hold a value the field no longer allows. Keep the field
            # default and carry on. Raising here would stop the application
            # from starting.
            logger.warning(
                "Ignoring the stored setting %s: the value %r is not allowed",
                key, value)
            return False

        return True
```

Then replace the body of `register_model` after the model is stored. Before:

```python
        self._feature_models[feature_id] = model

        # Initialize model with saved settings
        self.load_settings_file()
        if feature_id in self._settings:
            # Explicitly call get_fields on the class
            fields = type(model).get_fields()
            for key, value in self._settings[feature_id].items():
                if key in fields and fields[key].is_setting:
                    # Check if the property is settable
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

After:

```python
        self._feature_models[feature_id] = model

        # Fill the model from what was already loaded. initialize() reads the
        # file once; re-reading it here made every registration touch the disk.
        self.load_settings_file()
        for key, value in self._settings.get(feature_id, {}).items():
            self._apply_stored_value(model, key, value)
```

Then replace the model update inside `update_feature_settings`. Before:

```python
        # Update model if registered
        if feature_id in self._feature_models:
            model = self._feature_models[feature_id]
            for key, value in settings.items():
                if hasattr(model, key):
                    setattr(model, key, value)
```

After:

```python
        # Update model if registered
        model = self._feature_models.get(feature_id)
        if model is not None:
            for key, value in settings.items():
                self._apply_stored_value(model, key, value)
```

Then replace the body of `load_all_settings`. Before:

```python
        self.load_settings_file()
        for feature_id, model in self._feature_models.items():
            if feature_id in self._settings:
                for key, value in self._settings[feature_id].items():
                    if hasattr(model, key):
                        # Check if the property is settable
                        if hasattr(model.__class__, key) and isinstance(getattr(model.__class__, key), property):
                            if getattr(model.__class__, key).fset is None:
                                continue  # Skip read-only properties
                        setattr(model, key, value)
```

After:

```python
        self.load_settings_file()
        for feature_id, model in self._feature_models.items():
            for key, value in self._settings.get(feature_id, {}).items():
                self._apply_stored_value(model, key, value)
```

Then, in `export_settings`, give the file an encoding:

```python
            with open(export_file, 'w', encoding='utf-8') as f:
```

And in `import_settings`, the same, and use the one path for the models:

```python
            with open(import_file, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)

            self._settings.update(imported_settings)
            self.save_settings_file()

            # Update registered models
            for feature_id, model in self._feature_models.items():
                for key, value in self._settings.get(feature_id, {}).items():
                    self._apply_stored_value(model, key, value)
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/models/test_settings_service.py -q
```

Expected: every test passes.

- [ ] **Step 5: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/services/settings_service.py tests/models/test_settings_service.py
git commit -m "refactor(settings): one guarded path from the file into a model"
```

---

## Task 6: The notification settings become real settings

**Files:**
- Modify: `src/opaque/models/notification_settings_model.py:20-137`
- Modify: `src/opaque/presenters/notification_presenter.py:69-89`
- Modify: `src/opaque/view/application.py:395-405`
- Test: `tests/test_notification_settings.py`

`NotificationSettingsModel` declares 22 fields and not one of them declares `settings=True`, so none is saved and none appears in the settings dialog. The model is built in `_setup_models` and the registration line beside it is commented out with the note "Assuming registration happens elsewhere". It does not. Decision D7 says implement, so this task makes the fields settings, registers the model, and gives the dialog a page for it. Task 7, Task 8 and Task 9 make the values do their work.

The dialog reads exactly three members from every entry it is given: `feature_id`, `model` and `apply_settings()`. `NotificationPresenter` is a `QObject` and not a `BasePresenter`, so a small adapter carries those three.

- [ ] **Step 1: Write the failing test**

Create `tests/test_notification_settings.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests that the notification settings are declared, saved and editable."""

import pytest

from opaque.models.notification_settings_model import NotificationSettingsModel
from opaque.presenters.notification_presenter import (
    NOTIFICATION_SETTINGS_ID,
    NotificationPresenter,
)
from opaque.services.notification_service import NotificationService
from opaque.services.service import ServiceLocator
from opaque.services.settings_service import SettingsService


@pytest.fixture
def services(tmp_path, qapp):
    ServiceLocator.cleanup_services()
    settings = SettingsService(tmp_path / "settings.json")
    settings.initialize()
    ServiceLocator.register_service(settings)
    notifications = NotificationService()
    notifications.initialize()
    ServiceLocator.register_service(notifications)
    yield settings
    ServiceLocator.cleanup_services()


@pytest.fixture
def presenter(services, qtbot):
    from PySide6.QtWidgets import QMainWindow

    window = QMainWindow()
    qtbot.addWidget(window)
    return NotificationPresenter(window)


def test_every_field_of_the_model_is_a_setting():
    fields = NotificationSettingsModel.get_fields()
    assert fields
    not_settings = [name for name, field in fields.items()
                    if not field.is_setting]
    assert not_settings == []


def test_the_model_can_name_and_draw_itself(qapp):
    model = NotificationSettingsModel()
    assert model.feature_name() == "Notification System"
    assert model.feature_description() != ""
    assert model.feature_icon() is not None


def test_the_presenter_registers_the_settings_model(presenter, services):
    stored = services.get_all_settings()
    assert NOTIFICATION_SETTINGS_ID in stored
    assert "enable_toasts" in stored[NOTIFICATION_SETTINGS_ID]


def test_the_presenter_offers_one_settings_page(presenter):
    page = presenter.settings_page()
    assert page is not None
    assert page.feature_id == NOTIFICATION_SETTINGS_ID
    assert isinstance(page.model, NotificationSettingsModel)
    assert callable(page.apply_settings)


def test_a_stored_value_reaches_the_model_at_start(tmp_path, qapp, qtbot):
    import json

    from PySide6.QtWidgets import QMainWindow

    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({NOTIFICATION_SETTINGS_ID: {"enable_toasts": False}}),
        encoding="utf-8")

    ServiceLocator.cleanup_services()
    settings = SettingsService(path)
    settings.initialize()
    ServiceLocator.register_service(settings)
    notifications = NotificationService()
    notifications.initialize()
    ServiceLocator.register_service(notifications)
    try:
        window = QMainWindow()
        qtbot.addWidget(window)
        presenter = NotificationPresenter(window)
        assert presenter.settings_page().model.enable_toasts is False
    finally:
        ServiceLocator.cleanup_services()


def test_the_settings_dialog_shows_the_notification_page(presenter):
    from opaque.view.dialogs.settings import SettingsDialog

    dialog = SettingsDialog([presenter.settings_page()], parent=None)
    try:
        titles = [dialog.groups_list.item(row).text()
                  for row in range(dialog.groups_list.count())]
        assert "Notification System" in titles
    finally:
        dialog.deleteLater()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_notification_settings.py -q
```

Expected: a collection error, `ImportError: cannot import name 'NOTIFICATION_SETTINGS_ID'`.

- [ ] **Step 3: Declare the fields as settings**

In `src/opaque/models/notification_settings_model.py`, add `settings=True` to every one of the 22 fields, and add the two description methods. Replace the whole class body from the class docstring to the end of `feature_name`:

```python
class NotificationSettingsModel(AbstractModel):
    """
    Model for notification system settings and preferences.

    Every field is a setting, so every field is saved to settings.json and
    drawn in the settings dialog. The presenter that honours each one is
    NotificationPresenter; see its apply_settings().
    """

    # General notification settings
    notifications_enabled = BoolField(
        default=True,
        description="Enable/disable all notifications",
        settings=True
    )

    enable_toasts = BoolField(
        default=True,
        description="Enable transient toast notifications",
        settings=True
    )

    show_notification_count = BoolField(
        default=True,
        description="Show notification count in the widget",
        settings=True
    )

    auto_hide_notifications = BoolField(
        default=False,
        description="Automatically hide non-persistent notifications after timeout",
        settings=True
    )

    auto_hide_timeout = IntField(
        default=5000,
        min_value=500,
        max_value=120000,
        description="Auto-hide timeout in milliseconds (5 seconds default)",
        settings=True
    )

    # Notification level filters
    show_debug_notifications = BoolField(
        default=False,
        description="Show DEBUG level notifications",
        settings=True
    )

    show_info_notifications = BoolField(
        default=True,
        description="Show INFO level notifications",
        settings=True
    )

    show_warning_notifications = BoolField(
        default=True,
        description="Show WARNING level notifications",
        settings=True
    )

    show_error_notifications = BoolField(
        default=True,
        description="Show ERROR level notifications",
        settings=True
    )

    show_critical_notifications = BoolField(
        default=True,
        description="Show CRITICAL level notifications",
        settings=True
    )

    # Logger integration settings
    log_level = ChoiceField(
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        description="Minimum logging level",
        settings=True
    )

    console_logging_enabled = BoolField(
        default=True,
        description="Enable console logging output",
        settings=True
    )

    file_logging_enabled = BoolField(
        default=True,
        description="Enable file logging output",
        settings=True
    )

    log_file_path = StringField(
        default="",
        description="Custom log file path (empty for default)",
        settings=True
    )

    notification_on_warning = BoolField(
        default=False,
        description="Create notifications for WARNING log messages",
        settings=True
    )

    notification_on_error = BoolField(
        default=True,
        description="Create notifications for ERROR log messages",
        settings=True
    )

    notification_on_critical = BoolField(
        default=True,
        description="Create notifications for CRITICAL log messages",
        settings=True
    )

    # Widget appearance settings
    notification_widget_position = ChoiceField(
        default="Right",
        choices=["Left", "Right", "Top", "Bottom"],
        description="Default docking position for notification widget",
        settings=True
    )

    max_notification_display = IntField(
        default=100,
        min_value=1,
        max_value=1000,
        description="Maximum number of notifications to display in widget",
        settings=True
    )

    notification_widget_width = IntField(
        default=300,
        min_value=120,
        max_value=2000,
        description="Default width of notification widget",
        settings=True
    )

    notification_widget_height = IntField(
        default=400,
        min_value=120,
        max_value=2000,
        description="Default height of notification widget",
        settings=True
    )

    def __init__(self):
        super().__init__()

    def feature_name(self) -> str:
        """Return the feature name for this settings model"""
        return "Notification System"

    def feature_description(self) -> str:
        """Return one sentence for the settings dialog."""
        return "Notifications, toasts and logging"

    def feature_icon(self) -> QIcon:
        """Return the icon the settings dialog draws beside the group name."""
        return QIcon.fromTheme("dialog-information")
```

Add the icon import at the top of the file:

```python
from PySide6.QtGui import QIcon
```

The four `IntField` declarations gained a minimum and a maximum. The dialog draws an `IntField` with a `QSpinBox`, and a `QSpinBox` with no declared range uses the Qt default of 0 to 99, which would silently clamp 5000 to 99.

- [ ] **Step 4: Register the model and expose the page**

In `src/opaque/presenters/notification_presenter.py`, add this constant and this class directly after the `logger = logging.getLogger(__name__)` line:

```python
# The settings.json key and the dialog page identity of the notification
# settings. It is a constant because two modules need the same string.
NOTIFICATION_SETTINGS_ID = "notification_settings"


class NotificationSettingsPage:
    """
    What SettingsDialog needs from a feature, for the notification settings.

    The dialog reads exactly three members from every entry it is given:
    feature_id, model and apply_settings(). NotificationPresenter is a QObject
    and not a BasePresenter, so it cannot be such an entry itself. This
    adapter is, and it forwards the apply to the presenter.
    """

    def __init__(
            self,
            presenter: "NotificationPresenter",
            model: NotificationSettingsModel,
    ) -> None:
        self.feature_id: str = NOTIFICATION_SETTINGS_ID
        self.model: NotificationSettingsModel = model
        self._presenter = presenter

    def apply_settings(self) -> None:
        """Called by the settings dialog after it wrote the model."""
        self._presenter.apply_settings()
```

Then replace the registration block in `_setup_models`, lines 82 to 86. Before:

```python
            # Register settings model
            settings_service = ServiceLocator.get_service("settings")
            if settings_service:
                 # settings_service.register_model("notification_settings", self._settings_model)
                 pass # Assuming registration happens elsewhere or manual loading
```

After:

```python
            # Register the settings model so its values are saved and drawn.
            settings_service = ServiceLocator.get_service("settings")
            if settings_service is not None:
                settings_service.register_model(
                    NOTIFICATION_SETTINGS_ID, self._settings_model)
                settings_service.save_feature_settings(
                    NOTIFICATION_SETTINGS_ID, self._settings_model)

            self._settings_page = NotificationSettingsPage(
                self, self._settings_model)
```

Declare the page attribute beside the other attributes in `__init__`, after `self._settings_model: Optional[NotificationSettingsModel] = None`:

```python
        self._settings_page: Optional[NotificationSettingsPage] = None
```

Then add these two methods directly after `get_logger_model`:

```python
    def settings_page(self) -> Optional[NotificationSettingsPage]:
        """
        Return the settings dialog page for the notification settings.

        None only when the models failed to build, which _setup_models logs.
        """
        return self._settings_page

    def apply_settings(self) -> None:
        """
        Apply every notification setting to the running interface.

        Called by the settings dialog through NotificationSettingsPage, and by
        BaseApplication when SettingsService reports a change from anywhere
        else. Task 7, Task 8 and Task 9 of this plan fill it in.
        """
```

- [ ] **Step 5: Give the dialog the page**

In `src/opaque/view/application.py`, replace the first statement of `show_settings_dialog`. Before:

```python
        dialog = SettingsDialog(
            list(self._registered_features.values()), parent=self)
```

After:

```python
        pages = list(self._registered_features.values())

        # The notification settings have a model but no BasePresenter, so the
        # presenter hands over a small adapter that carries the three members
        # the dialog reads.
        notification_page = self.notification_presenter.settings_page()
        if notification_page is not None:
            pages.append(notification_page)

        dialog = SettingsDialog(pages, parent=self)
```

- [ ] **Step 6: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_notification_settings.py -q
```

Expected: `6 passed`.

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 8: Look at the running application**

```bash
uv run python examples/basic_example/main.py
```

Open Settings. Expected: a group named "Notification System" in the left list, with 22 rows, and the timeout row showing 5000 and not 99. Change "Enable transient toast notifications" off, press OK, close the application, start it again and open Settings. Expected: the box is still off. Record what you saw.

- [ ] **Step 9: Commit**

```bash
git add src/opaque/models/notification_settings_model.py src/opaque/presenters/notification_presenter.py src/opaque/view/application.py tests/test_notification_settings.py
git commit -m "feat(notifications): save and draw the notification settings"
```

---

## Task 7: The notification behaviour settings do their work

**Files:**
- Modify: `src/opaque/presenters/notification_presenter.py:141-148, 180-190` (`_on_service_notification_added`, `_show_toast`)
- Test: `tests/test_notification_settings.py` (add to it)

Ten of the fields describe what to show: one master switch, five level filters, the toast switch and the two auto-hide values. Only `enable_toasts` is read anywhere. Everything reaches the interface through one method, `_on_service_notification_added`, so one guard there covers all of them.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_notification_settings.py`:

```python
def _add(presenter, level):
    from opaque.services.notification_service import NotificationLevel

    service = ServiceLocator.get_service("notification")
    return service.add_notification(
        level=level, title="Title", message="Message", source="Test")


def test_a_notification_reaches_the_list(presenter):
    from opaque.services.notification_service import NotificationLevel

    _add(presenter, NotificationLevel.ERROR)

    assert len(presenter._notification_list.items) == 1


def test_the_master_switch_stops_every_notification(presenter):
    from opaque.services.notification_service import NotificationLevel

    presenter.settings_page().model.notifications_enabled = False

    _add(presenter, NotificationLevel.ERROR)

    assert presenter._notification_list.items == {}


def test_a_level_that_is_switched_off_does_not_reach_the_list(presenter):
    from opaque.services.notification_service import NotificationLevel

    presenter.settings_page().model.show_error_notifications = False

    _add(presenter, NotificationLevel.ERROR)

    assert presenter._notification_list.items == {}


def test_a_level_that_is_switched_on_still_reaches_the_list(presenter):
    from opaque.services.notification_service import NotificationLevel

    presenter.settings_page().model.show_error_notifications = False

    _add(presenter, NotificationLevel.INFO)

    assert len(presenter._notification_list.items) == 1


def test_debug_notifications_are_off_by_default(presenter):
    from opaque.services.notification_service import NotificationLevel

    _add(presenter, NotificationLevel.DEBUG)

    assert presenter._notification_list.items == {}


def test_no_toast_appears_when_toasts_are_switched_off(presenter):
    from opaque.services.notification_service import NotificationLevel

    presenter.settings_page().model.enable_toasts = False

    _add(presenter, NotificationLevel.ERROR)

    assert presenter._active_toasts == []


def test_a_toast_appears_when_toasts_are_switched_on(presenter):
    from opaque.services.notification_service import NotificationLevel

    _add(presenter, NotificationLevel.ERROR)

    assert len(presenter._active_toasts) == 1


def test_the_auto_hide_timeout_replaces_the_level_duration(presenter):
    from opaque.services.notification_service import NotificationLevel

    model = presenter.settings_page().model
    model.auto_hide_notifications = True
    model.auto_hide_timeout = 1500

    _add(presenter, NotificationLevel.ERROR)

    toast = presenter._active_toasts[0]
    assert toast.close_timer.isActive()
    assert toast.close_timer.interval() == 1500


def test_a_toast_that_never_expires_is_left_alone(presenter):
    from opaque.services.notification_service import NotificationLevel

    model = presenter.settings_page().model
    model.auto_hide_notifications = True
    model.auto_hide_timeout = 1500

    _add(presenter, NotificationLevel.CRITICAL)

    toast = presenter._active_toasts[0]
    # A critical toast has no duration, so it must not gain one.
    if not toast.close_timer.isActive():
        assert toast.close_timer.interval() != 1500
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_notification_settings.py -q -k "master_switch or level_that_is_switched_off or debug_notifications or auto_hide_timeout"
```

Expected: `test_the_master_switch_stops_every_notification` FAILS with one item in the list. `test_a_level_that_is_switched_off_does_not_reach_the_list` FAILS. `test_debug_notifications_are_off_by_default` FAILS. `test_the_auto_hide_timeout_replaces_the_level_duration` FAILS on the interval.

- [ ] **Step 3: Write the implementation**

In `src/opaque/presenters/notification_presenter.py`, replace `_on_service_notification_added`. Before:

```python
    def _on_service_notification_added(self, notification: Notification):
        # Add to list
        if self._notification_list:
            self._notification_list.add_notification(notification)
            
        # Show Toast if enabled
        if self._settings_model and self._settings_model.enable_toasts:
            self._show_toast(notification)
```

After:

```python
    def _on_service_notification_added(self, notification: Notification):
        # Every notification reaches the interface through this method, so
        # this is the one place the display settings have to be honoured.
        if not self._shows(notification):
            return

        if self._notification_list:
            self._notification_list.add_notification(notification)

        # Show Toast if enabled
        if self._settings_model and self._settings_model.enable_toasts:
            self._show_toast(notification)

    def _shows(self, notification: Notification) -> bool:
        """
        Return True when the settings allow this notification to be shown.

        notifications_enabled switches every notification off. The five
        show_*_notifications fields switch off one level each. Both were
        declared and read by nothing.
        """
        settings = self._settings_model
        if settings is None:
            return True

        if not settings.notifications_enabled:
            return False

        allowed = settings.get_enabled_notification_levels()
        return notification.level.name in allowed
```

Then, in `_show_toast`, apply the lifetime. Before:

```python
        toast = ToastWidget(notification, self._main_window)
        toast.closed.connect(self._on_toast_closed)
```

After:

```python
        toast = ToastWidget(notification, self._main_window)
        self._apply_toast_lifetime(toast)
        toast.closed.connect(self._on_toast_closed)
```

And add this method directly after `_show_toast`:

```python
    def _apply_toast_lifetime(self, toast: ToastWidget) -> None:
        """
        Replace the per level toast lifetime when the user asked for one.

        ToastWidget picks its duration from the notification level. The two
        auto_hide settings were declared and read by nothing.

        A toast whose timer is not running has no duration at all, which is
        how a critical notification stays on screen until the user dismisses
        it. That toast is left alone: an auto-hide timeout must not take away
        the one notification the user must see.
        """
        settings = self._settings_model
        if settings is None or not settings.auto_hide_notifications:
            return

        if not toast.close_timer.isActive():
            return

        timeout = int(settings.auto_hide_timeout)
        if timeout > 0:
            toast.close_timer.start(timeout)
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_notification_settings.py -q
```

Expected: `15 passed`.

- [ ] **Step 5: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. `tests/view/test_notification_widget.py` and `tests/view/test_toast_stack.py` both exercise these paths; both must stay green.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/presenters/notification_presenter.py tests/test_notification_settings.py
git commit -m "feat(notifications): honour the display and toast settings"
```

---

## Task 8: The notification panel settings do their work

**Files:**
- Modify: `src/opaque/view/widgets/notification_widget.py:301-356` (`SimplifiedNotificationList`)
- Modify: `src/opaque/presenters/notification_presenter.py` (`_setup_views`, `apply_settings`, two new methods)
- Modify: `src/opaque/view/application.py:170-174` (the count lambda)
- Test: `tests/test_notification_settings.py` (add to it)

Five fields describe the panel: where it docks, how wide and how tall it starts, how many rows it keeps, and whether the toolbar button shows a number. None of them reaches anything.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_notification_settings.py`:

```python
def test_the_row_limit_drops_the_oldest_row(presenter):
    from opaque.services.notification_service import NotificationLevel

    presenter.settings_page().model.max_notification_display = 2
    presenter.apply_settings()

    first = _add(presenter, NotificationLevel.INFO)
    _add(presenter, NotificationLevel.INFO)
    _add(presenter, NotificationLevel.INFO)

    assert len(presenter._notification_list.items) == 2
    assert first not in presenter._notification_list.items


def test_the_row_limit_can_be_raised_again(presenter):
    from opaque.services.notification_service import NotificationLevel

    model = presenter.settings_page().model
    model.max_notification_display = 1
    presenter.apply_settings()
    _add(presenter, NotificationLevel.INFO)
    _add(presenter, NotificationLevel.INFO)
    assert len(presenter._notification_list.items) == 1

    model.max_notification_display = 5
    presenter.apply_settings()
    _add(presenter, NotificationLevel.INFO)

    assert len(presenter._notification_list.items) == 2


def test_the_dock_moves_to_the_position_the_settings_name(presenter):
    from PySide6.QtCore import Qt

    presenter.settings_page().model.notification_widget_position = "Left"
    presenter.apply_settings()

    area = presenter._main_window.dockWidgetArea(presenter._dock_widget)
    assert area == Qt.DockWidgetArea.LeftDockWidgetArea


def test_applying_the_dock_settings_does_not_open_a_closed_panel(presenter):
    presenter.settings_page().model.notification_widget_position = "Top"
    presenter.apply_settings()

    assert presenter._dock_widget.isVisible() is False


def test_the_toolbar_count_is_hidden_when_the_setting_is_off(presenter):
    presenter.settings_page().model.show_notification_count = False

    assert presenter.displayed_count(7) == 0


def test_the_toolbar_count_is_passed_through_when_the_setting_is_on(presenter):
    assert presenter.displayed_count(7) == 7
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_notification_settings.py -q -k "row_limit or dock or toolbar_count"
```

Expected: every one of the six FAILS. The first two fail on the row count, the dock tests fail because the dock stays at the bottom, and the count tests fail with `AttributeError: 'NotificationPresenter' object has no attribute 'displayed_count'`.

- [ ] **Step 3: Give the list a row limit**

In `src/opaque/view/widgets/notification_widget.py`, in `SimplifiedNotificationList.__init__`, add one attribute:

```python
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.items: Dict[str, NotificationListItem] = {}
        # 0 means no limit. The notification presenter sets a real limit from
        # the max_notification_display setting.
        self._maximum_rows: int = 0
        self._setup_ui()
```

Then add these two methods directly after `clear`:

```python
    def set_maximum_rows(self, maximum: int) -> None:
        """
        Keep at most `maximum` rows, dropping the oldest first.

        0 means no limit. A list that grows without a limit slows the panel
        down, and nobody reads the thousandth row.
        """
        self._maximum_rows = max(0, int(maximum))
        self._trim_to_maximum()

    def _trim_to_maximum(self) -> None:
        """Remove the oldest rows until the list fits the limit."""
        if self._maximum_rows <= 0:
            return
        # items is insertion ordered, so the first key is the oldest row.
        while len(self.items) > self._maximum_rows:
            self.remove_notification(next(iter(self.items)))
```

And in `add_notification`, add the trim. Before:

```python
        self.container_layout.insertWidget(0, item)
        self.items[notification.id] = item
        self._update_clear_button()
        self._apply_level_filter()
```

After:

```python
        self.container_layout.insertWidget(0, item)
        self.items[notification.id] = item
        self._trim_to_maximum()
        self._update_clear_button()
        self._apply_level_filter()
```

- [ ] **Step 4: Apply the panel settings**

In `src/opaque/presenters/notification_presenter.py`, add this mapping as a class attribute of `NotificationPresenter`, directly after the class docstring:

```python
    # The four positions the notification_widget_position setting offers.
    DOCK_AREAS = {
        "Left": Qt.DockWidgetArea.LeftDockWidgetArea,
        "Right": Qt.DockWidgetArea.RightDockWidgetArea,
        "Top": Qt.DockWidgetArea.TopDockWidgetArea,
        "Bottom": Qt.DockWidgetArea.BottomDockWidgetArea,
    }
```

Then add these two methods directly after `settings_page`:

```python
    def displayed_count(self, count: int) -> int:
        """
        Return the unread count the toolbar button must show.

        0 when show_notification_count is off; the toolbar then shows the
        plain label with no number. The setting was declared and read by
        nothing.
        """
        settings = self._settings_model
        if settings is not None and not settings.show_notification_count:
            return 0
        return count

    def _apply_panel_settings(self) -> None:
        """
        Apply the row limit, the dock position and the dock size.

        Called at start and again whenever the settings change. The dock is
        re-added to move it, which is how Qt moves a dock, and the visibility
        is put back afterwards: applying a setting must not open a panel the
        user closed.
        """
        settings = self._settings_model
        if settings is None:
            return

        if self._notification_list is not None:
            self._notification_list.set_maximum_rows(
                int(settings.max_notification_display))

        if self._dock_widget is None or self._main_window is None:
            return

        area = self.DOCK_AREAS.get(str(settings.notification_widget_position))
        if area is None:
            return

        was_visible = self._dock_widget.isVisible()
        self._main_window.addDockWidget(area, self._dock_widget)
        self._dock_widget.setVisible(was_visible)

        width = int(settings.notification_widget_width)
        height = int(settings.notification_widget_height)
        if area in (Qt.DockWidgetArea.LeftDockWidgetArea,
                    Qt.DockWidgetArea.RightDockWidgetArea):
            self._main_window.resizeDocks(
                [self._dock_widget], [width], Qt.Orientation.Horizontal)
        else:
            self._main_window.resizeDocks(
                [self._dock_widget], [height], Qt.Orientation.Vertical)
```

Then fill in `apply_settings`, which Task 6 left with only a docstring:

```python
    def apply_settings(self) -> None:
        """
        Apply every notification setting to the running interface.

        Called by the settings dialog through NotificationSettingsPage, and by
        BaseApplication when SettingsService reports a change from anywhere
        else.
        """
        self._apply_panel_settings()
```

And call it at the end of `_setup_views`, inside the `try`, after the dock is hidden:

```python
                # The dock starts closed. The toolbar button opens it. An empty
                # panel must not take height from the MDI area at start up.
                self._dock_widget.hide()

            # Put the stored panel settings in place before the first
            # notification arrives.
            self._apply_panel_settings()
```

- [ ] **Step 5: Let the toolbar count follow the setting**

In `src/opaque/view/application.py`, in `_wire_shell_signals`, replace the count connection. Before:

```python
        model = self.notification_presenter.get_notification_model()
        if model is not None:
            model.notification_count_changed.connect(
                lambda count: self.toolbar.set_notification_count(count))
```

After:

```python
        model = self.notification_presenter.get_notification_model()
        if model is not None:
            # The presenter decides what the number is, because the
            # show_notification_count setting belongs to it.
            model.notification_count_changed.connect(
                lambda count: self.toolbar.set_notification_count(
                    self.notification_presenter.displayed_count(count)))
```

- [ ] **Step 6: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_notification_settings.py tests/view/test_notification_widget.py tests/test_application_shell.py -q
```

Expected: every test passes. `21 passed` in `tests/test_notification_settings.py`.

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/widgets/notification_widget.py src/opaque/presenters/notification_presenter.py src/opaque/view/application.py tests/test_notification_settings.py
git commit -m "feat(notifications): honour the panel position, size and row limit"
```

---

## Task 9: The logging settings reach the logger service

**Files:**
- Modify: `src/opaque/services/logger_service.py:60-66, 180-190, 300-310, 332-347`
- Modify: `src/opaque/models/notification_settings_model.py` (`log_file_path` becomes `log_directory`)
- Modify: `src/opaque/presenters/notification_presenter.py` (`apply_settings`)
- Modify: `src/opaque/view/application.py:126-131` (the logger service construction)
- Test: `tests/test_notification_settings.py` (add to it)

Six fields describe logging, and `LoggerService` already has a setter for four of them. `notification_on_warning` has no setter and `log()` has no WARNING branch, so that field could not work even if something called it. `log_file_path` names a file the service never reads; the service takes a log **directory** at construction, so the field is renamed to what the service can honour, and it is applied at the next start, which is stated in its own description.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_notification_settings.py`:

```python
def test_the_log_level_setting_reaches_the_logger_service(presenter, qapp):
    import logging

    from opaque.services.logger_service import LoggerService

    service = LoggerService(application_name="test")
    service.initialize()
    ServiceLocator.register_service(service)
    try:
        presenter.settings_page().model.log_level = "ERROR"
        presenter.apply_settings()

        assert service.get_configuration()["log_level"] == "ERROR"
    finally:
        service.cleanup()


def test_the_warning_notification_setting_reaches_the_logger_service(
        presenter, qapp):
    from opaque.services.logger_service import LoggerService

    service = LoggerService(application_name="test")
    service.initialize()
    ServiceLocator.register_service(service)
    try:
        presenter.settings_page().model.notification_on_warning = True
        presenter.apply_settings()

        assert service.get_configuration()["notify_on_warning"] is True
    finally:
        service.cleanup()


def test_a_warning_creates_a_notification_when_the_setting_is_on(qapp):
    from opaque.services.logger_service import LoggerService

    service = LoggerService(application_name="test")
    service.initialize()
    ServiceLocator.register_service(service)
    notifications = ServiceLocator.get_service("notification")
    try:
        service.set_notification_on_warning(True)
        before = len(notifications.get_notifications())

        service.log("WARNING", "the tank is low", source="Test")

        assert len(notifications.get_notifications()) == before + 1
    finally:
        service.cleanup()


def test_a_warning_creates_no_notification_when_the_setting_is_off(qapp):
    from opaque.services.logger_service import LoggerService

    service = LoggerService(application_name="test")
    service.initialize()
    ServiceLocator.register_service(service)
    notifications = ServiceLocator.get_service("notification")
    try:
        service.set_notification_on_warning(False)
        before = len(notifications.get_notifications())

        service.log("WARNING", "the tank is low", source="Test")

        assert len(notifications.get_notifications()) == before
    finally:
        service.cleanup()


def test_the_model_names_a_log_directory_and_not_a_file():
    fields = NotificationSettingsModel.get_fields()
    assert "log_directory" in fields
    assert "log_file_path" not in fields
    assert "next start" in fields["log_directory"].description
```

These four tests need the notification service, which the `services` fixture registers. Add `services` to the last three signatures if the fixture is not already pulled in through `presenter`.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_notification_settings.py -q -k "log_level_setting or warning_notification_setting or warning_creates or log_directory"
```

Expected: `test_the_log_level_setting_reaches_the_logger_service` FAILS, because `apply_settings` does not touch the logger. The two `warning_creates` tests FAIL with `AttributeError: 'LoggerService' object has no attribute 'set_notification_on_warning'`. `test_the_model_names_a_log_directory_and_not_a_file` FAILS.

- [ ] **Step 3: Teach the logger service about warnings**

In `src/opaque/services/logger_service.py`, add one attribute in `__init__`, beside the other two. Before:

```python
        self._notify_on_error = True
        self._notify_on_critical = True
```

After:

```python
        self._notify_on_warning = False
        self._notify_on_error = True
        self._notify_on_critical = True
```

Then add the WARNING branch in `log`. Before:

```python
            should_notify = (
                (level_upper == 'ERROR' and self._notify_on_error) or
                (level_upper == 'CRITICAL' and self._notify_on_critical)
            )
```

After:

```python
            should_notify = (
                (level_upper == 'WARNING' and self._notify_on_warning) or
                (level_upper == 'ERROR' and self._notify_on_error) or
                (level_upper == 'CRITICAL' and self._notify_on_critical)
            )
```

Then add the setter, directly before `set_notification_on_error`:

```python
    def set_notification_on_warning(self, enabled: bool) -> None:
        """Enable or disable notifications for warning messages"""
        self._notify_on_warning = enabled
```

And add the key to `get_configuration`, beside the other two:

```python
            'notify_on_warning': self._notify_on_warning,
```

- [ ] **Step 4: Rename the field to what the service can honour**

In `src/opaque/models/notification_settings_model.py`, replace the `log_file_path` field:

```python
    log_directory = StringField(
        default="",
        description="Folder for the log files, empty for the default. "
                    "Applies at the next start",
        settings=True
    )
```

Then fix the one reader, `get_logger_configuration`. Before:

```python
            "file_path": str(self.log_file_path) if self.log_file_path else None,
```

After:

```python
            "directory": str(self.log_directory) if self.log_directory else None,
```

- [ ] **Step 5: Apply the six live settings**

In `src/opaque/presenters/notification_presenter.py`, add this method directly after `_apply_panel_settings`:

```python
    def _apply_logger_settings(self) -> None:
        """
        Apply the logging settings to the logger service.

        Six of the notification settings describe logging, and all six were
        declared and read by nothing. log_directory is not here: the service
        takes it at construction, so BaseApplication passes it at start, and
        the field says so in its own description.
        """
        settings = self._settings_model
        service = ServiceLocator.get_service("logger")
        if settings is None or service is None:
            return

        service.set_log_level(str(settings.log_level))
        service.set_console_logging(bool(settings.console_logging_enabled))
        service.set_file_logging(bool(settings.file_logging_enabled))
        service.set_notification_on_warning(
            bool(settings.notification_on_warning))
        service.set_notification_on_error(
            bool(settings.notification_on_error))
        service.set_notification_on_critical(
            bool(settings.notification_on_critical))
```

Then call it from `apply_settings`:

```python
    def apply_settings(self) -> None:
        """
        Apply every notification setting to the running interface.

        Called by the settings dialog through NotificationSettingsPage, and by
        BaseApplication when SettingsService reports a change from anywhere
        else.
        """
        self._apply_panel_settings()
        self._apply_logger_settings()
```

- [ ] **Step 6: Pass the stored log directory at start**

In `src/opaque/view/application.py`, replace the logger service construction. Before:

```python
        # Initialize logger service
        self.logger_service = LoggerService(
            application_name=configuration.get_application_name())
```

After:

```python
        # Initialize logger service. The log directory is a stored setting,
        # and the service takes it at construction, so it is read here from
        # the settings service that was created just above.
        stored_notification_settings = self.settings_service.get_all_settings(
        ).get(NOTIFICATION_SETTINGS_ID, {})
        self.logger_service = LoggerService(
            application_name=configuration.get_application_name(),
            log_directory=stored_notification_settings.get(
                "log_directory") or None)
```

Add the constant to the imports at the top of `application.py`:

```python
from opaque.presenters.notification_presenter import (
    NOTIFICATION_SETTINGS_ID,
    NotificationPresenter,
)
```

- [ ] **Step 7: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_notification_settings.py -q
```

Expected: `26 passed`.

- [ ] **Step 8: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 9: Commit**

```bash
git add src/opaque/services/logger_service.py src/opaque/models/notification_settings_model.py src/opaque/presenters/notification_presenter.py src/opaque/view/application.py tests/test_notification_settings.py
git commit -m "feat(logging): apply the stored logging settings"
```

---

## Task 10: A settings change from anywhere reaches the presenter

**Files:**
- Modify: `src/opaque/view/application.py:154-174` (`_wire_shell_signals`)
- Test: `tests/test_application_shell.py` (add to it)

`SettingsService.settings_changed` is emitted by `update_feature_settings`, `reset_feature_settings` and `import_settings`, and nothing has ever connected to it. Those three write the file and the model and leave the interface showing the old values. The settings dialog does not need the signal, because it calls `apply_settings()` itself; every other writer does.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_application_shell.py`:

```python
def test_a_settings_change_from_the_service_reaches_the_presenter(
        app_window, monkeypatch):
    presenter = next(iter(app_window._registered_features.values()))
    calls = []
    monkeypatch.setattr(
        presenter, "apply_settings", lambda: calls.append(True))

    app_window.settings_service.settings_changed.emit(
        presenter.feature_id, {})

    assert calls == [True]


def test_a_settings_change_for_an_unknown_feature_is_ignored(app_window):
    # Nothing to assert but the absence of a failure: an unknown identity
    # must not raise inside a signal handler.
    app_window.settings_service.settings_changed.emit("no-such-feature", {})


def test_a_settings_change_reaches_the_notification_presenter(
        app_window, monkeypatch):
    from opaque.presenters.notification_presenter import (
        NOTIFICATION_SETTINGS_ID,
    )

    calls = []
    monkeypatch.setattr(
        app_window.notification_presenter, "apply_settings",
        lambda: calls.append(True))

    app_window.settings_service.settings_changed.emit(
        NOTIFICATION_SETTINGS_ID, {})

    assert calls == [True]
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_application_shell.py -q -k "settings_change"
```

Expected: the first and the third FAIL with `assert [] == [True]`. The second passes already.

- [ ] **Step 3: Write the implementation**

In `src/opaque/view/application.py`, add this connection at the end of `_wire_shell_signals`:

```python
        self.settings_service.settings_changed.connect(
            lambda feature_id, _values: self._on_settings_changed(feature_id))
```

And add this method directly after `_wire_shell_signals`:

```python
    def _on_settings_changed(self, feature_id: str) -> None:
        """
        Tell one presenter that its settings changed outside the dialog.

        The settings dialog calls apply_settings() itself. This path covers
        every other writer: update_feature_settings(), reset_feature_settings()
        and import_settings(). Until now they wrote the file and the model and
        left the interface showing the old values.

        The registry is searched instead of indexed, because a feature has
        three identity keys today and the registry key is not the settings
        key. Plan 06 makes this one lookup.
        """
        if feature_id == NOTIFICATION_SETTINGS_ID:
            self.notification_presenter.apply_settings()
            return

        for presenter in self._registered_features.values():
            if presenter.feature_id == feature_id:
                presenter.apply_settings()
                return
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_application_shell.py -q
```

Expected: every test passes.

- [ ] **Step 5: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/application.py tests/test_application_shell.py
git commit -m "fix(settings): deliver settings_changed to the presenter that owns it"
```

---

## Task 11: The language setting really changes the language

**Files:**
- Modify: `src/opaque/services/settings_service.py` (one module function)
- Modify: `src/opaque/view/application.py:66-74`
- Modify: `src/opaque/presenters/app_presenter.py`
- Test: `tests/test_localisation_setting.py`

`ApplicationModel.language` offers `en`, `es` and `fr`, and `install_translator(app)` is called with no locale, so it always uses `QLocale.system()`. The stored value has never changed anything. Decision D7 says implement it: the value is honoured at the next start, and changing it says so.

The translator must be installed before the first widget is built, which is before `SettingsService` exists, so the one value that is needed that early is read straight from the file.

- [ ] **Step 1: Write the failing test**

Create `tests/test_localisation_setting.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests that the stored language setting reaches the translator."""

import json

from opaque.services.settings_service import stored_language


def test_no_file_gives_no_language(tmp_path):
    assert stored_language(tmp_path / "missing.json") == ""


def test_a_broken_file_gives_no_language(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ broken", encoding="utf-8")
    assert stored_language(path) == ""


def test_a_stored_language_is_found_whatever_the_block_is_called(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"ApplicationPresenter": {"language": "fr"}}),
        encoding="utf-8")
    assert stored_language(path) == "fr"


def test_a_file_with_no_language_gives_no_language(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"demo": {"theme": "Dark"}}), encoding="utf-8")
    assert stored_language(path) == ""


def test_a_language_that_is_not_text_is_refused(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"demo": {"language": 7}}), encoding="utf-8")
    assert stored_language(path) == ""


def test_a_list_at_the_top_level_gives_no_language(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(["nonsense"]), encoding="utf-8")
    assert stored_language(path) == ""
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_localisation_setting.py -q
```

Expected: a collection error, `ImportError: cannot import name 'stored_language'`.

- [ ] **Step 3: Write the reader**

In `src/opaque/services/settings_service.py`, add this module function directly after the `logger = logging.getLogger(__name__)` line:

```python
def stored_language(settings_file: Path) -> str:
    """
    Read the stored interface language straight from the settings file.

    The translator has to be installed before the first widget is built,
    because a widget reads its strings once, when it is created. That is
    before SettingsService exists, so this reads the one value that is needed
    that early.

    Every feature block is searched, because the block key is the feature
    identity and this must not depend on which feature holds the application
    settings.

    Args:
        settings_file: The settings file to read.

    Returns:
        The language code, or an empty string when the file, the block or the
        key is absent, unreadable or not text.
    """
    try:
        with open(settings_file, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return ""

    if not isinstance(data, dict):
        return ""

    for block in data.values():
        if isinstance(block, dict):
            value = block.get("language")
            if isinstance(value, str) and value:
                return value

    return ""
```

- [ ] **Step 4: Install the translator for the stored language**

In `src/opaque/view/application.py`, replace the translator block. Before:

```python
        app = QApplication.instance()
        if app:
            app.main_window = self  # type: ignore
            # The translator must be installed before any widget is built.
            # A widget reads its strings once, when it is created.
            install_translator(app)
            apply_layout_direction(app)
```

After:

```python
        # The stored language decides the locale, and it is read from the file
        # because the settings service does not exist yet.
        self._language_at_start: str = stored_language(
            configuration.get_settings_file_path())
        locale = (QLocale(self._language_at_start)
                  if self._language_at_start else QLocale.system())

        app = QApplication.instance()
        if app:
            app.main_window = self  # type: ignore
            # The translator must be installed before any widget is built.
            # A widget reads its strings once, when it is created.
            install_translator(app, locale=locale)
            apply_layout_direction(app, locale=locale)
```

Both import lines already exist and are replaced, not added. Replace `from PySide6.QtCore import Qt` with:

```python
from PySide6.QtCore import QLocale, Qt
```

Replace `from opaque.services.settings_service import SettingsService` with:

```python
from opaque.services.settings_service import SettingsService, stored_language
```

- [ ] **Step 5: Say that the change needs a restart**

In `src/opaque/presenters/app_presenter.py`, record the language at start. Add this line at the end of `__init__`, after `self._apply_current_theme()`:

```python
        # The language cannot change while the process runs: every widget
        # already read its strings. Remember what was loaded, so a change can
        # be reported instead of looking as if it did nothing.
        self._language_at_start: str = str(self.model.language)
```

Then replace `apply_settings`:

```python
    def apply_settings(self) -> None:
        """Apply the theme, and report a language change."""
        self._apply_current_theme()
        self._report_language_change()

    def _report_language_change(self) -> None:
        """
        Tell the user that the new language arrives at the next start.

        Qt reads every string when a widget is built, so a running window
        cannot change language. Saying nothing made the setting look broken.
        """
        wanted = str(self.model.language)
        if wanted == self._language_at_start:
            return

        title = self.tr("Language changed")
        message = self.tr(
            "The new language is used the next time the application starts.")

        service = ServiceLocator.get_service("notification")
        if service is not None and hasattr(service, "add_notification"):
            service.add_notification(
                level=NotificationLevel.INFO,
                title=title,
                message=message,
                source="Settings",
                persistent=True,
            )
        else:
            logger.info("%s: %s", title, message)
```

Add the imports `app_presenter.py` needs:

```python
import logging

from opaque.services.notification_service import NotificationLevel

logger = logging.getLogger(__name__)
```

Put the `logger` line after the imports, at module level, if the module does not have one already.

- [ ] **Step 6: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_localisation_setting.py -q
```

Expected: `6 passed`.

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 8: Look at the running application**

```bash
uv run python examples/basic_example/main.py
```

Open Settings, change the language to `fr`, press OK. Expected: a notification appears saying the new language is used at the next start. Close the application and start it again. Expected: the interface still reads English, because the framework ships no French `.qm` file, and the log holds one DEBUG line reading "No translation found for fr". That is the correct behaviour for a missing translation; the setting is now honoured. Record what you saw.

- [ ] **Step 9: Commit**

```bash
git add src/opaque/services/settings_service.py src/opaque/view/application.py src/opaque/presenters/app_presenter.py tests/test_localisation_setting.py
git commit -m "feat(localisation): honour the stored language at start"
```

---

## Verification of the whole plan

- [ ] **Check 1: the settings tests all pass**

```bash
uv run python -m pytest tests/models/test_field_coercion.py tests/models/test_settings_service.py tests/view/test_settings_dialog.py tests/test_notification_settings.py tests/test_localisation_setting.py -q
```

Expected: zero failures.

- [ ] **Check 2: nothing declares a setting that nothing reads**

```bash
uv run python -c "
from opaque.models.notification_settings_model import NotificationSettingsModel
fields = NotificationSettingsModel.get_fields()
print(len(fields), 'fields')
print('not settings:', [n for n, f in fields.items() if not f.is_setting])
"
```

Expected: `22 fields` and `not settings: []`.

- [ ] **Check 3: a full round trip on disk**

```bash
uv run python -c "
import json, tempfile, pathlib
from opaque.models.abstract_model import AbstractModel
from opaque.models.annotations import FloatField, IntField
from opaque.services.settings_service import SettingsService

class M(AbstractModel):
    ratio = FloatField(default=1.0, description='Ratio', settings=True)
    count = IntField(default=1, description='Count', settings=True)

folder = pathlib.Path(tempfile.mkdtemp())
service = SettingsService(folder / 'settings.json')
service.initialize()
model = M()
service.register_model('demo', model)
model.ratio = 2.5
model.count = 7
service.save_feature_settings('demo', model)

again = SettingsService(folder / 'settings.json')
again.initialize()
restored = M()
again.register_model('demo', restored)
print('ratio', restored.ratio, type(restored.ratio).__name__)
print('count', restored.count, type(restored.count).__name__)
"
```

Expected:

```
ratio 2.5 float
count 7 int
```

- [ ] **Check 4: the whole suite, the type check and the lint**

```bash
uv run python -m pytest tests -q
uv run python -m mypy src/opaque/services/settings_service.py src/opaque/models/annotations.py
uv run python -m pylint src/opaque/services/settings_service.py src/opaque/models/annotations.py src/opaque/view/dialogs/settings.py
```

Expected: the suite reports zero failures. Report any mypy or pylint message that names a line this plan wrote.

---

## What this plan does not do

| Left open | Owner |
|---|---|
| The settings key is `presenter.feature_id` while the feature registry key is `model.feature_name()`, so `_on_settings_changed` searches the registry instead of indexing it. | Plan 06 Task 4, Task 5 |
| `register_model` still calls `load_settings_file()` once per registration, so start up touches the disk once per feature. | Plan 10 Task 7 |
| `SettingsService.__init__` creates a directory as a side effect of construction. | Plan 10 Task 7 |
| The five remaining `print()` calls in `logger_service.py` and `console_service.py`. | Plan 10 Task 6 |
| `_on_notifications_changed`, `_on_notification_count_changed`, `_on_log_entry_added` and `_on_logger_configuration_changed` are still four connected handlers whose bodies are `pass`. | Plan 10 Task 6 |
| The theme name list still comes from a class-level `Field.choices` write. | Plan 08 Task 5 |
