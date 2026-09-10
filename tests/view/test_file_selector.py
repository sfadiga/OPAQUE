# This Python file uses the following encoding: utf-8
"""Tests for the FileSelector settings widget."""

from opaque.view.widgets.file_selector import FileSelector


def test_typing_a_path_emits_the_signal(qtbot):
    widget = FileSelector(initial_path="")
    qtbot.addWidget(widget)
    received = []
    widget.pathChanged.connect(received.append)

    widget.path_edit.setText("C:/data/input.csv")

    assert received == ["C:/data/input.csv"]
    assert widget.path() == "C:/data/input.csv"


def test_the_initial_path_is_shown(qtbot):
    widget = FileSelector(initial_path="C:/start.txt")
    qtbot.addWidget(widget)
    assert widget.path() == "C:/start.txt"


def test_the_controls_have_accessible_names(qtbot):
    widget = FileSelector(initial_path="")
    qtbot.addWidget(widget)
    assert widget.path_edit.accessibleName().strip()
    assert widget.browse_button.text().strip()
