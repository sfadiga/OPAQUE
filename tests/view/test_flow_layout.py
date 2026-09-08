# This Python file uses the following encoding: utf-8
"""Tests for the flow layout."""

from PySide6.QtWidgets import QLabel, QWidget

from opaque.view.layouts.flow import FlowLayout


def _flow(qtbot, left, top, right, bottom):
    """Build a flow layout holding one label, with the given margins."""
    container = QWidget()
    qtbot.addWidget(container)
    layout = FlowLayout(container)
    layout.setContentsMargins(left, top, right, bottom)
    layout.addWidget(QLabel("item"))
    return container, layout


def test_the_width_uses_the_horizontal_margins(qtbot, light_palette_app):
    wide_container, wide = _flow(qtbot, 40, 4, 40, 4)
    narrow_container, narrow = _flow(qtbot, 4, 4, 4, 4)
    assert wide.minimumSize().width() > narrow.minimumSize().width()


def test_the_height_uses_the_vertical_margins(qtbot, light_palette_app):
    tall_container, tall = _flow(qtbot, 4, 40, 4, 40)
    short_container, short = _flow(qtbot, 4, 4, 4, 4)
    assert tall.minimumSize().height() > short.minimumSize().height()


def test_a_wide_margin_does_not_change_the_height(qtbot, light_palette_app):
    wide_container, wide = _flow(qtbot, 40, 4, 40, 4)
    narrow_container, narrow = _flow(qtbot, 4, 4, 4, 4)
    assert wide.minimumSize().height() == narrow.minimumSize().height()
