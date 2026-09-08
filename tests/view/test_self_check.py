# This Python file uses the following encoding: utf-8
"""Tests for the debug build interface self check."""

from PySide6.QtWidgets import (
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from opaque.view.self_check import MINIMUM_TARGET, check_interface


def _host(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    QVBoxLayout(host)
    return host


def test_a_clean_widget_reports_nothing(qtbot, light_palette_app):
    host = _host(qtbot)
    button = QPushButton("Save", host)
    host.layout().addWidget(button)
    assert check_interface(host) == []


def test_a_small_button_is_reported(qtbot, light_palette_app):
    host = _host(qtbot)
    button = QPushButton("x", host)
    button.setFixedSize(16, 16)
    button.setAccessibleName("Close")
    host.layout().addWidget(button)

    problems = check_interface(host)

    assert len(problems) == 1
    assert str(MINIMUM_TARGET) in problems[0]


def test_a_button_with_no_readable_label_is_reported(
        qtbot, light_palette_app):
    host = _host(qtbot)
    button = QPushButton("...", host)
    host.layout().addWidget(button)

    problems = check_interface(host)

    assert len(problems) == 1
    assert "name" in problems[0].lower()


def test_a_text_box_with_no_name_is_reported(qtbot, light_palette_app):
    host = _host(qtbot)
    host.layout().addWidget(QLineEdit(host))
    assert len(check_interface(host)) == 1


def test_every_problem_names_the_widget_class(qtbot, light_palette_app):
    host = _host(qtbot)
    host.layout().addWidget(QLineEdit(host))
    assert "QLineEdit" in check_interface(host)[0]


def test_a_platform_internal_button_is_not_reported(qtbot, light_palette_app):
    host = _host(qtbot)
    host.layout().addWidget(QTableWidget(2, 2, host))
    assert check_interface(host) == []
