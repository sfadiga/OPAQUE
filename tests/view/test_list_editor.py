# This Python file uses the following encoding: utf-8
"""Tests for the ListEditor settings widget."""

from opaque.view.widgets.list_editor import ListEditor


def test_the_initial_items_are_shown(qtbot):
    widget = ListEditor(initial_items=["a", "b"])
    qtbot.addWidget(widget)
    assert widget.items() == ["a", "b"]


def test_adding_an_item_emits_the_new_list(qtbot):
    widget = ListEditor(initial_items=["a"])
    qtbot.addWidget(widget)
    received = []
    widget.itemsChanged.connect(received.append)

    widget.add_button.click()

    assert len(widget.items()) == 2
    assert received and len(received[-1]) == 2


def test_removing_the_selected_item_emits_the_new_list(qtbot):
    widget = ListEditor(initial_items=["a", "b"])
    qtbot.addWidget(widget)
    received = []
    widget.itemsChanged.connect(received.append)

    widget.list_widget.setCurrentRow(0)
    widget.remove_button.click()

    assert widget.items() == ["b"]
    assert received[-1] == ["b"]


def test_editing_an_item_emits_the_new_list(qtbot):
    widget = ListEditor(initial_items=["a"])
    qtbot.addWidget(widget)
    received = []
    widget.itemsChanged.connect(received.append)

    widget.list_widget.item(0).setText("changed")

    assert widget.items() == ["changed"]
    assert received[-1] == ["changed"]
