# This Python file uses the following encoding: utf-8
"""Tests for the pure toast stack geometry."""

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtWidgets import QWidget

from opaque.view.layouts.toast_stack import (
    MAX_VISIBLE_TOASTS,
    overflow_count,
    stacked_toast_positions,
    toast_anchor,
)

ANCHOR = QRect(0, 0, 800, 600)
TOAST = QSize(300, 80)


def test_an_empty_stack_gives_no_positions():
    assert stacked_toast_positions(ANCHOR, []) == []


def test_the_first_toast_sits_in_the_bottom_right_corner():
    positions = stacked_toast_positions(ANCHOR, [TOAST], margin=12)
    assert positions[0] == QPoint(800 - 12 - 300, 600 - 12 - 80)


def test_the_second_toast_sits_above_the_first():
    positions = stacked_toast_positions(
        ANCHOR, [TOAST, TOAST], margin=12, spacing=8)
    assert positions[1].x() == positions[0].x()
    assert positions[1].y() == positions[0].y() - 80 - 8


def test_the_stack_never_leaves_the_anchor_on_the_left():
    tiny = QRect(0, 0, 200, 400)
    positions = stacked_toast_positions(tiny, [TOAST], margin=12)
    assert positions[0].x() == 12


def test_the_stack_never_leaves_the_anchor_on_the_top():
    tiny = QRect(0, 0, 800, 60)
    positions = stacked_toast_positions(tiny, [TOAST], margin=12)
    assert positions[0].y() == 12


def test_the_anchor_offset_is_added_to_every_position():
    moved = QRect(1000, 500, 800, 600)
    positions = stacked_toast_positions(moved, [TOAST], margin=12)
    assert positions[0] == QPoint(1000 + 800 - 12 - 300, 500 + 600 - 12 - 80)


def test_no_toast_overflows_below_the_limit():
    assert overflow_count(0) == 0
    assert overflow_count(MAX_VISIBLE_TOASTS - 2) == 0


def test_one_toast_overflows_when_the_stack_is_full():
    assert overflow_count(MAX_VISIBLE_TOASTS - 1) == 0
    assert overflow_count(MAX_VISIBLE_TOASTS) == 1


def test_a_larger_backlog_overflows_by_more():
    assert overflow_count(MAX_VISIBLE_TOASTS + 3) == 4


def test_the_anchor_uses_global_coordinates_not_widget_coordinates(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    window.resize(320, 240)
    window.move(40, 60)
    window.show()
    qtbot.waitExposed(window)

    anchor = toast_anchor(window)
    top_left = window.mapToGlobal(QPoint(0, 0))
    bottom_right = window.mapToGlobal(QPoint(window.width(), window.height()))

    assert anchor.left() >= top_left.x()
    assert anchor.top() >= top_left.y()
    assert anchor.left() + anchor.width() <= bottom_right.x()
    assert anchor.top() + anchor.height() <= bottom_right.y()


def test_the_anchor_is_never_empty(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    window.resize(320, 240)
    window.show()
    qtbot.waitExposed(window)

    assert not toast_anchor(window).isEmpty()
