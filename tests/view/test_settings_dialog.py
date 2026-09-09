# This Python file uses the following encoding: utf-8
"""
Tests for SettingsDialog.

The dialog reads three members from a presenter, so these tests use a
duck-typed double. The model is a real AbstractModel because the dialog calls
type(model).get_fields().
"""

import pytest
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit, QSpinBox,
)

from opaque.models.abstract_model import AbstractModel
from opaque.models.annotations import (
    BoolField, ChoiceField, FloatField, IntField, ListField, StringField,
)
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
