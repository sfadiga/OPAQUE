# This Python file uses the following encoding: utf-8
"""
Tests for SettingsDialog.

The dialog reads three members from a presenter, so these tests use a
duck-typed double. The model is a real AbstractModel because the dialog calls
type(model).get_fields().
"""

import pytest
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit, QPlainTextEdit,
    QSlider, QSpinBox,
)

from opaque.models.abstract_model import AbstractModel
from opaque.models.annotations import (
    BoolField, ChoiceField, FloatField, IntField, ListField, StringField,
    UIType,
)
from opaque.models.console_model import ConsoleModel
from opaque.services.service import ServiceLocator
from opaque.services.settings_service import SettingsService
from opaque.view.dialogs.settings import SettingsDialog
from opaque.view.widgets.file_selector import FileSelector
from opaque.view.widgets.list_editor import ListEditor


class DemoModel(AbstractModel):
    FEATURE_ID = "demo"

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


class _ConsolePresenterDouble:
    """
    A presenter double that only carries what SettingsPage needs.

    ConsolePresenter builds its view internally and captures stdout, which a
    settings-dialog test must not exercise, so this double stands in for it.
    """

    def __init__(self, model):
        self.feature_id = model.feature_id()
        self.model = model

    def apply_settings(self) -> None:
        pass


def test_a_model_with_no_declared_settings_fields_does_not_crash_the_dialog(
        qtbot, service):
    """
    ConsoleModel duck-types the model interface instead of extending
    AbstractModel (see its class docstring), but it never implemented
    get_fields(). SettingsDialog calls type(model).get_fields() on every
    registered feature while building its search cache, so registering the
    console feature made the whole Settings dialog fail to open, hiding
    every other feature's settings too (for example the application theme).
    """
    presenter = _ConsolePresenterDouble(ConsoleModel(context=None))
    widget = SettingsDialog([presenter], parent=None)
    qtbot.addWidget(widget)

    assert widget.groups_list.count() == 1


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

    FEATURE_ID = "typed"

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


def test_a_list_setting_is_shown_as_a_list_editor(typed_dialog):
    widget = _widget_for(typed_dialog, "Tags")
    assert isinstance(widget, ListEditor)
    assert widget.items() == ["a", "b"]


def test_a_list_setting_queues_a_list(typed_dialog):
    widget = _widget_for(typed_dialog, "Tags")
    widget.list_widget.setCurrentRow(0)
    widget.remove_button.click()

    assert typed_dialog.pending_value("typed", "tags") == ["b"]


def test_an_int_setting_queues_an_int(typed_dialog):
    widget = _widget_for(typed_dialog, "Count")
    widget.setValue(9)

    queued = typed_dialog.pending_value("typed", "count")
    assert queued == 9
    assert isinstance(queued, int)


def test_apply_writes_every_typed_value_into_the_model(typed_dialog):
    _widget_for(typed_dialog, "Ratio").setValue(1.75)
    _widget_for(typed_dialog, "Level").setCurrentIndex(0)
    tags_widget = _widget_for(typed_dialog, "Tags")
    tags_widget.list_widget.setCurrentRow(0)
    tags_widget.remove_button.click()

    typed_dialog._apply_settings()

    model = typed_dialog._presenter.model
    assert model.ratio == 1.75
    assert model.level == 1
    assert model.tags == ["b"]


def test_a_value_the_field_refuses_is_reported_and_not_queued(typed_dialog):
    typed_dialog._record_pending("typed", "count", "not a number")

    assert typed_dialog.pending_value("typed", "count") is None
    assert typed_dialog.status_label.text() != ""


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


class BlankModel(AbstractModel):
    """Numeric settings fields that declare no default value."""

    FEATURE_ID = "blank"

    level = IntField(description="Level", settings=True,
                     min_value=0, max_value=10, ui_type=UIType.SLIDER)
    count = IntField(description="Count", settings=True)
    ratio = FloatField(description="Ratio", settings=True)

    def feature_name(self) -> str:
        return "Blank"

    def feature_icon(self):
        from PySide6.QtGui import QIcon
        return QIcon()


def test_a_numeric_field_without_a_default_still_builds_the_form(qtbot, service):
    """An unset value is None, and int(None)/float(None) raised TypeError."""
    presenter = DemoPresenter(BlankModel())
    presenter.feature_id = "blank"
    widget = SettingsDialog([presenter], parent=None)
    qtbot.addWidget(widget)

    assert _widget_of_type(widget, QSlider) is not None
    assert _widget_of_type(widget, QSpinBox) is not None
    assert _widget_of_type(widget, QDoubleSpinBox) is not None


def test_a_list_field_holding_legacy_text_is_split_on_commas(qtbot, service):
    """ListField.coerce accepts comma text for old files; the editor must
    receive the coerced list, not the raw string exploded one character at
    a time."""
    presenter = DemoPresenter(TypedModel())
    presenter.feature_id = "typed"
    presenter.model.tags = "a, b"
    widget = SettingsDialog([presenter], parent=None)
    qtbot.addWidget(widget)

    editor = _widget_of_type(widget, ListEditor)
    assert editor.items() == ["a", "b"]


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


class OpenSliderModel(AbstractModel):
    """A slider without bounds and a float slider; neither is drawable."""

    FEATURE_ID = "open_slider"

    level = IntField(default=500, description="Level", settings=True,
                     ui_type=UIType.SLIDER)
    ratio = FloatField(default=0.5, min_value=0.0, max_value=1.0,
                       description="Ratio", settings=True,
                       ui_type=UIType.SLIDER)

    def feature_name(self) -> str:
        return "OpenSlider"

    def feature_icon(self):
        from PySide6.QtGui import QIcon
        return QIcon()


@pytest.fixture
def open_slider_dialog(qtbot, service):
    presenter = DemoPresenter(OpenSliderModel())
    presenter.feature_id = "open_slider"
    widget = SettingsDialog([presenter], parent=None)
    qtbot.addWidget(widget)
    return widget


def test_a_slider_without_bounds_falls_back_to_a_spinbox(open_slider_dialog):
    """Qt's default slider range is 0-99. A stored 500 rendered at 99 and
    one drag wrote the clamped value back. The spinbox has an open range."""
    assert _widget_for(open_slider_dialog, "Level").value() == 500
    assert isinstance(_widget_for(open_slider_dialog, "Level"), QSpinBox)


def test_a_float_slider_falls_back_to_a_double_spinbox(open_slider_dialog):
    """QSlider moves in integer steps and truncates every fraction."""
    widget = _widget_for(open_slider_dialog, "Ratio")
    assert isinstance(widget, QDoubleSpinBox)
    assert widget.value() == 0.5
    assert (widget.minimum(), widget.maximum()) == (0.0, 1.0)


def test_a_bounded_int_slider_is_still_a_slider(rich_dialog):
    assert isinstance(_widget_for(rich_dialog, "Volume"), QSlider)


class PrecisionModel(AbstractModel):
    """Floats finer than the default six decimal places."""

    FEATURE_ID = "precision"

    tiny = FloatField(default=1e-7, description="Tiny", settings=True)
    declared = FloatField(default=0.5, decimals=9,
                          description="Declared", settings=True)
    half_significant = FloatField(default=1.5e-7,
                                  description="HalfSignificant",
                                  settings=True)
    floor_value = FloatField(default=1e-20, description="FloorValue",
                             settings=True)
    narrow = FloatField(default=1e-7, decimals=2, description="Narrow",
                        settings=True)
    not_a_number = FloatField(default=float("nan"),
                              description="NotANumber", settings=True)
    combined = FloatField(default=0.25, decimals=9, min_value=0.0,
                          max_value=1.0, description="Combined",
                          settings=True, ui_type=UIType.SLIDER)

    def feature_name(self) -> str:
        return "Precision"

    def feature_icon(self):
        from PySide6.QtGui import QIcon
        return QIcon()


@pytest.fixture
def precision_dialog(qtbot, service):
    presenter = DemoPresenter(PrecisionModel())
    presenter.feature_id = "precision"
    widget = SettingsDialog([presenter], parent=None)
    qtbot.addWidget(widget)
    return widget


def test_a_tiny_float_is_not_rounded_to_zero(precision_dialog):
    """setDecimals(6) displayed 1e-7 as 0.000000, and the first user
    interaction wrote the rounded 0.0 back into the model."""
    widget = _widget_for(precision_dialog, "Tiny")
    assert widget.value() == 1e-7


def test_a_declared_decimals_widens_the_widget(precision_dialog):
    widget = _widget_for(precision_dialog, "Declared")
    assert widget.decimals() == 9


def test_widening_preserves_every_significant_digit(precision_dialog):
    """1.5e-7 widened only to its leading digit displayed 0.0000002, and
    the first edit wrote the rounded 2e-7 back."""
    widget = _widget_for(precision_dialog, "HalfSignificant")
    assert widget.decimals() == 8
    assert widget.value() == 1.5e-7


def test_widening_is_capped_at_fifteen_places(precision_dialog):
    widget = _widget_for(precision_dialog, "FloorValue")
    assert widget.decimals() == 15


def test_widening_wins_over_a_smaller_declared_value(precision_dialog):
    widget = _widget_for(precision_dialog, "Narrow")
    assert widget.decimals() == 7


def test_a_non_finite_value_does_not_crash_the_dialog_and_keeps_six_places(
        precision_dialog):
    widget = _widget_for(precision_dialog, "NotANumber")
    assert widget.decimals() == 6


def test_a_float_slider_with_declared_decimals_composes(precision_dialog):
    """One field runs the ui_type override, the slider fallback and
    the declared precision together; this locks the pipeline."""
    widget = _widget_for(precision_dialog, "Combined")
    assert isinstance(widget, QDoubleSpinBox)
    assert widget.decimals() == 9
    assert widget.value() == 0.25


def test_the_default_stays_at_six_decimals(typed_dialog):
    widget = _widget_for(typed_dialog, "Ratio")
    assert widget.decimals() == 6
