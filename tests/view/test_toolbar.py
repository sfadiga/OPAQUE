# This Python file uses the following encoding: utf-8
"""
Tests for OpaqueMainToolbar.

The toolbar reads only five members from a presenter, so these tests use a
duck-typed double instead of a real BasePresenter. A real presenter needs a
model, a view, a main window and a populated ServiceLocator, none of which the
toolbar touches.
"""

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QToolButton

from opaque.view.widgets.toolbar import OpaqueMainToolbar


class FakeView(QObject):
    """Emits the same four signals as OpaqueMdiSubWindow."""

    window_opened = Signal()
    window_closed = Signal()
    window_focused = Signal()
    window_unfocused = Signal()

    def __init__(self):
        super().__init__()
        self.open_close_calls = 0

    def open_close(self) -> None:
        self.open_close_calls += 1


class FakeModel:
    def __init__(self, name: str):
        self._name = name

    def feature_name(self) -> str:
        return self._name

    def feature_description(self) -> str:
        return f"{self._name} description"

    def feature_icon(self) -> QIcon:
        return QIcon()


class FakePresenter:
    def __init__(self, name: str):
        self.model = FakeModel(name)
        self.view = FakeView()


def test_the_double_satisfies_add_feature(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    button = toolbar.add_feature(FakePresenter("Alpha"))
    assert isinstance(button, QToolButton)
    assert button.text() == "Alpha"


def test_a_new_feature_button_is_checkable_and_starts_unchecked(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    button = toolbar.add_feature(FakePresenter("Alpha"))
    assert button.isCheckable() is True
    assert button.isChecked() is False


def test_opening_a_window_checks_its_button(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    presenter = FakePresenter("Alpha")
    button = toolbar.add_feature(presenter)

    presenter.view.window_opened.emit()

    assert button.isChecked() is True


def test_closing_a_window_unchecks_its_button(qtbot):
    """This is defect C1. The old code called _set_active on the close signal."""
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    presenter = FakePresenter("Alpha")
    button = toolbar.add_feature(presenter)

    presenter.view.window_opened.emit()
    presenter.view.window_closed.emit()

    assert button.isChecked() is False


def test_focusing_a_second_window_unchecks_the_first(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    first = FakePresenter("Alpha")
    second = FakePresenter("Beta")
    first_button = toolbar.add_feature(first)
    second_button = toolbar.add_feature(second)

    first.view.window_opened.emit()
    second.view.window_focused.emit()

    assert second_button.isChecked() is True
    assert first_button.isChecked() is False


def test_closing_one_window_leaves_another_checked(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    first = FakePresenter("Alpha")
    second = FakePresenter("Beta")
    first_button = toolbar.add_feature(first)
    second_button = toolbar.add_feature(second)

    second.view.window_opened.emit()
    first.view.window_closed.emit()

    assert second_button.isChecked() is True
    assert first_button.isChecked() is False


def test_clicking_the_button_calls_open_close(qtbot):
    toolbar = OpaqueMainToolbar("Features")
    qtbot.addWidget(toolbar)
    presenter = FakePresenter("Alpha")
    button = toolbar.add_feature(presenter)

    button.click()

    assert presenter.view.open_close_calls == 1
