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


def test_a_qshortcut_appears_in_the_list(qtbot):
    from PySide6.QtGui import QKeySequence, QShortcut
    from PySide6.QtWidgets import QWidget

    window = QWidget()
    qtbot.addWidget(window)
    shortcut = QShortcut(QKeySequence("Ctrl+Shift+K"), window)
    shortcut.setWhatsThis("Kick the tyres")

    entries = collect_shortcuts(window)

    assert ("Kick the tyres", "Ctrl+Shift+K") in entries


def test_a_qshortcut_without_a_label_is_left_out(qtbot):
    from PySide6.QtGui import QKeySequence, QShortcut
    from PySide6.QtWidgets import QWidget

    window = QWidget()
    qtbot.addWidget(window)
    QShortcut(QKeySequence("Ctrl+Shift+L"), window)

    keys = [key for _label, key in collect_shortcuts(window)]

    assert "Ctrl+Shift+L" not in keys


def test_the_same_key_is_not_listed_twice(qtbot):
    from PySide6.QtGui import QKeySequence, QShortcut
    from PySide6.QtWidgets import QWidget

    window = QWidget()
    qtbot.addWidget(window)
    for _ in range(2):
        shortcut = QShortcut(QKeySequence("Ctrl+Shift+M"), window)
        shortcut.setWhatsThis("Twice")

    entries = collect_shortcuts(window)

    assert entries.count(("Twice", "Ctrl+Shift+M")) == 1


def test_the_console_search_shortcuts_are_labelled(qtbot):
    from opaque.view.widgets.console_widget import ConsoleWidget

    widget = ConsoleWidget()
    qtbot.addWidget(widget)

    labels = [widget.next_shortcut.whatsThis(),
              widget.prev_shortcut.whatsThis()]

    assert all(labels)


def test_the_console_search_shortcuts_appear_in_the_list(qtbot):
    from opaque.view.widgets.console_widget import ConsoleWidget

    widget = ConsoleWidget()
    qtbot.addWidget(widget)

    labels = [label for label, _key in collect_shortcuts(widget)]

    assert widget.next_shortcut.whatsThis() in labels
