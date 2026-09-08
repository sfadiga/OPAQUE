# This Python file uses the following encoding: utf-8
"""Tests for the closeable tab widget."""

from PySide6.QtWidgets import QWidget

from opaque.view.widgets.closeable_tab_widget import CloseableTabWidget


def _tabs(qtbot, minimum_tabs=1, show_plus_tab=True):
    """Build a tab widget holding plain QWidget content."""
    widget = CloseableTabWidget(
        widget_type=QWidget,
        minimum_tabs=minimum_tabs,
        show_plus_tab=show_plus_tab,
    )
    qtbot.addWidget(widget)
    return widget


def test_the_add_tab_is_found_by_its_role(qtbot, light_palette_app):
    widget = _tabs(qtbot)
    assert widget.add_tab_index() == widget.tab_widget.count() - 1
    assert widget.is_add_tab(widget.add_tab_index())


def test_a_content_tab_is_not_the_add_tab(qtbot, light_palette_app):
    widget = _tabs(qtbot)
    assert not widget.is_add_tab(0)


def test_a_tab_renamed_to_a_plus_is_still_a_content_tab(
        qtbot, light_palette_app):
    widget = _tabs(qtbot)
    # Set the label directly. This is what a stubborn user or a translation
    # would produce. The tab must keep its identity as content.
    widget.tab_widget.setTabText(0, "+")
    assert not widget.is_add_tab(0)
    assert widget.get_tab_name(0) == "+"
    assert widget.get_widget_at_index(0) is not None


def test_the_real_tab_count_ignores_the_add_tab(qtbot, light_palette_app):
    widget = _tabs(qtbot, minimum_tabs=2)
    assert widget.tab_widget.count() == 3
    assert widget.get_tab_count() == 2


def test_new_tabs_are_inserted_before_the_add_tab(qtbot, light_palette_app):
    widget = _tabs(qtbot)
    widget.add_tab("Second")
    assert widget.is_add_tab(widget.tab_widget.count() - 1)
    assert widget.get_tab_name(widget.tab_widget.count() - 2) == "Second"


def test_without_the_add_tab_nothing_is_an_add_tab(qtbot, light_palette_app):
    widget = _tabs(qtbot, show_plus_tab=False)
    assert widget.add_tab_index() == -1
    assert not widget.is_add_tab(0)
