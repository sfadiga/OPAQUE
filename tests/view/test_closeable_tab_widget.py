# This Python file uses the following encoding: utf-8
"""Tests for the closeable tab widget."""

from PySide6.QtWidgets import QInputDialog, QMessageBox, QWidget

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


def test_selecting_the_add_tab_creates_a_new_tab(qtbot, light_palette_app):
    widget = _tabs(qtbot)
    before = widget.get_tab_count()
    widget.tab_widget.setCurrentIndex(widget.add_tab_index())
    assert widget.get_tab_count() == before + 1


def test_selecting_the_add_tab_does_not_leave_it_current(
        qtbot, light_palette_app):
    widget = _tabs(qtbot)
    widget.tab_widget.setCurrentIndex(widget.add_tab_index())
    assert not widget.is_add_tab(widget.tab_widget.currentIndex())


def test_the_new_tab_names_are_unique(qtbot, light_palette_app):
    widget = _tabs(qtbot)
    widget.tab_widget.setCurrentIndex(widget.add_tab_index())
    widget.tab_widget.setCurrentIndex(widget.add_tab_index())
    names = [
        widget.get_tab_name(i) for i in range(widget.tab_widget.count())
    ]
    names = [name for name in names if name is not None]
    assert len(names) == 3
    assert len(names) == len(set(names))


def test_no_dialog_is_opened_from_a_selection_change(
        qtbot, light_palette_app, monkeypatch):
    widget = _tabs(qtbot)

    def _explode(*args, **kwargs):
        raise AssertionError("a modal dialog was opened from currentChanged")

    monkeypatch.setattr(QInputDialog, "getText", _explode)
    widget.tab_widget.setCurrentIndex(widget.add_tab_index())
    assert widget.get_tab_count() == 2


def test_the_last_tab_cannot_be_closed(qtbot, light_palette_app):
    widget = _tabs(qtbot, minimum_tabs=1)
    assert not widget.can_close_tab(0)


def test_a_tab_can_be_closed_when_more_than_the_minimum_exist(
        qtbot, light_palette_app):
    widget = _tabs(qtbot, minimum_tabs=1)
    widget.add_tab("Second")
    assert widget.can_close_tab(0)


def test_closing_asks_for_confirmation_first(qtbot, light_palette_app):
    widget = _tabs(qtbot, minimum_tabs=1)
    widget.add_tab("Second")
    asked = []
    widget._confirm_close_tab = lambda name: asked.append(name) or True

    assert widget.remove_tab(0)

    assert len(asked) == 1
    assert widget.get_tab_count() == 1


def test_declining_the_confirmation_keeps_the_tab(qtbot, light_palette_app):
    widget = _tabs(qtbot, minimum_tabs=1)
    widget.add_tab("Second")
    widget._confirm_close_tab = lambda name: False

    assert not widget.remove_tab(0)

    assert widget.get_tab_count() == 2


def test_the_minimum_rule_opens_no_message_box(
        qtbot, light_palette_app, monkeypatch):
    widget = _tabs(qtbot, minimum_tabs=1)

    def _explode(*args, **kwargs):
        raise AssertionError("a warning box was opened for the minimum rule")

    monkeypatch.setattr(QMessageBox, "warning", _explode)
    assert not widget.remove_tab(0)
    assert widget.get_tab_count() == 1
