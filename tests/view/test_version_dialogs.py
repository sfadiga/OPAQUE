# This Python file uses the following encoding: utf-8
"""Tests for the version and About dialogs."""

from pathlib import Path

from opaque.view.dialogs.version_info import AboutDialog, VersionInfoDialog
from opaque.view.theme import TypeScale, contrast_ratio, surface
from opaque.view.theme.contrast import TEXT_CONTRAST_MINIMUM

_SOURCE = Path(__file__).resolve().parents[2] / \
    "src" / "opaque" / "view" / "dialogs" / "version_info.py"


def test_the_about_dialog_is_not_a_fixed_size(qtbot, light_palette_app):
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    assert dialog.maximumWidth() > dialog.minimumWidth()
    assert dialog.maximumHeight() > dialog.minimumHeight()


def test_the_about_dialog_keeps_a_sensible_floor(qtbot, light_palette_app):
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    assert dialog.minimumWidth() >= 400


def test_the_framework_label_colour_passes_contrast(qtbot, light_palette_app):
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    ratio = contrast_ratio(dialog.framework_label_colour, surface())
    assert ratio >= TEXT_CONTRAST_MINIMUM


def test_the_system_tab_uses_the_system_fixed_font(qtbot, light_palette_app):
    dialog = VersionInfoDialog()
    qtbot.addWidget(dialog)
    assert dialog.system_text.font().family() == TypeScale.mono().family()


def test_no_dialog_hardcodes_a_grey_or_a_font_family():
    source = _SOURCE.read_text(encoding="utf-8")
    assert "#666666" not in source
    assert "rgba(0, 0, 0" not in source
    assert 'QFont("Courier"' not in source
