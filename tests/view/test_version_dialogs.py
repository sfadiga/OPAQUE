# This Python file uses the following encoding: utf-8
"""Tests for the version and About dialogs."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractButton

from opaque.view.dialogs.version_info import (
    AboutDialog,
    VersionInfoDialog,
    VersionStatusWidget,
)
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


def test_the_version_status_widget_is_a_button(qtbot, light_palette_app):
    widget = VersionStatusWidget({"version": "1.0"})
    qtbot.addWidget(widget)
    assert isinstance(widget, QAbstractButton)


def test_the_version_status_widget_can_take_the_keyboard_focus(
        qtbot, light_palette_app):
    widget = VersionStatusWidget({"version": "1.0"})
    qtbot.addWidget(widget)
    assert widget.focusPolicy() != Qt.FocusPolicy.NoFocus


def test_the_version_status_widget_is_tall_enough(qtbot, light_palette_app):
    widget = VersionStatusWidget({"version": "1.0"})
    qtbot.addWidget(widget)
    assert widget.minimumHeight() >= 24


def test_the_version_status_widget_has_an_accessible_name(
        qtbot, light_palette_app):
    widget = VersionStatusWidget({"version": "1.0"})
    qtbot.addWidget(widget)
    assert widget.accessibleName() != ""
    assert "1.0" in widget.text()


def test_the_version_schema_holds_every_key_the_dialog_shows():
    import dataclasses

    from opaque.view.version_info_schema import VersionInfo

    names = {entry.name for entry in dataclasses.fields(VersionInfo)}
    for expected in ("version", "build_date", "commit_hash"):
        assert expected in names


def test_the_schema_can_be_built_from_a_dictionary():
    from opaque.view.version_info_schema import VersionInfo

    info = VersionInfo.from_dict({"version": "1.2.3"})

    assert info.version == "1.2.3"


def test_a_missing_key_gives_the_documented_placeholder():
    from opaque.view.version_info_schema import VersionInfo

    info = VersionInfo.from_dict({})

    assert info.version == "Unknown"
    assert info.company == ""


def test_an_unknown_key_is_ignored_and_not_written():
    from opaque.view.version_info_schema import VersionInfo

    info = VersionInfo.from_dict({"versoin": "1.2.3"})

    assert info.version == "Unknown"
    assert not hasattr(info, "versoin")


def test_a_none_value_is_treated_as_a_missing_key():
    from opaque.view.version_info_schema import VersionInfo

    info = VersionInfo.from_dict({"version": None})

    assert info.version == "Unknown"


def test_the_dialog_reads_the_schema_and_not_a_dictionary():
    import inspect

    from opaque.view.dialogs import version_info

    source = inspect.getsource(version_info)
    assert "VersionInfo.from_dict(" in source
