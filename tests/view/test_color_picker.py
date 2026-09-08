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
