# This Python file uses the following encoding: utf-8
"""Tests for the MDI area wrapper."""

from PySide6.QtWidgets import QMdiArea, QWidget

from opaque.view.widgets.mdi_window import OpaqueMdiArea


def test_the_area_declares_no_signal_of_its_own(qtbot):
    # A subclass that redeclares a Qt signal replaces it, and the version Qt
    # emits is then lost.
    assert "subWindowActivated" not in vars(OpaqueMdiArea)


def test_the_qt_signal_still_fires_when_a_window_is_activated(qtbot):
    area = OpaqueMdiArea()
    qtbot.addWidget(area)
    area.show()

    with qtbot.waitSignal(area.subWindowActivated, timeout=1000):
        window = area.addSubWindow(QWidget())
        window.show()
        area.setActiveSubWindow(window)


def test_the_tabbed_view_can_be_switched_on_and_off(qtbot):
    area = OpaqueMdiArea()
    qtbot.addWidget(area)

    area.set_tabbed(True)
    assert area.is_tabbed() is True
    assert area.viewMode() == QMdiArea.ViewMode.TabbedView

    area.set_tabbed(False)
    assert area.is_tabbed() is False
