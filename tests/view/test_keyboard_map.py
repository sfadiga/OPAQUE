# This Python file uses the following encoding: utf-8
"""Tests for the keyboard map dialog."""

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QWidget

from opaque.view.dialogs.keyboard_map import KeyboardMapDialog, collect_shortcuts


def _window_with_actions(qtbot, entries):
    """Build a widget carrying one QAction for each label and key pair."""
    window = QWidget()
    qtbot.addWidget(window)
    for label, key in entries:
        action = QAction(label, window)
        if key:
            action.setShortcut(QKeySequence(key))
        window.addAction(action)
    return window


def test_collect_shortcuts_finds_an_action_with_a_key(qtbot):
    window = _window_with_actions(qtbot, [("Save Workspace", "Ctrl+S")])
    entries = collect_shortcuts(window)
    assert entries == [("Save Workspace", "Ctrl+S")]


def test_collect_shortcuts_skips_an_action_with_no_key(qtbot):
    window = _window_with_actions(
        qtbot, [("Save Workspace", "Ctrl+S"), ("No Key", None)])
    labels = [label for label, _ in collect_shortcuts(window)]
    assert labels == ["Save Workspace"]


def test_collect_shortcuts_is_sorted_by_label(qtbot):
    window = _window_with_actions(qtbot, [
        ("Zoom In", "Ctrl++"),
        ("About", "F2"),
        ("Manual", "F1"),
    ])
    labels = [label for label, _ in collect_shortcuts(window)]
    assert labels == sorted(labels)


def test_collect_shortcuts_drops_the_menu_ampersand(qtbot):
    window = _window_with_actions(qtbot, [("&Save Workspace", "Ctrl+S")])
    assert collect_shortcuts(window)[0][0] == "Save Workspace"


def test_the_dialog_lists_every_shortcut(qtbot, light_palette_app):
    window = _window_with_actions(qtbot, [
        ("Save Workspace", "Ctrl+S"),
        ("Load Workspace", "Ctrl+O"),
    ])
    dialog = KeyboardMapDialog(window)
    qtbot.addWidget(dialog)
    assert dialog.table.rowCount() == 2
    assert dialog.table.item(0, 0).text() == "Load Workspace"
