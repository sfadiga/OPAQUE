# This Python file uses the following encoding: utf-8
"""Smoke tests that prove the pytest-qt harness and the palette fixtures work."""

from PySide6.QtGui import QPalette


def test_light_fixture_gives_a_light_window_colour(light_palette_app):
    window = light_palette_app.palette().color(QPalette.ColorRole.Window)
    assert window.name() == "#f5f5f5"


def test_dark_fixture_gives_a_dark_window_colour(dark_palette_app):
    window = dark_palette_app.palette().color(QPalette.ColorRole.Window)
    assert window.name() == "#2b2b2b"


def test_fixture_restores_the_original_palette(qapp):
    original = qapp.palette().color(QPalette.ColorRole.Window).name()
    assert original not in ("#f5f5f5", "#2b2b2b")
