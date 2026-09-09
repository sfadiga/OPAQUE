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
    picker.set_color("#00ff00")
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
