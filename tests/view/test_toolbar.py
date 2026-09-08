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
