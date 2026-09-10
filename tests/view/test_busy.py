# This Python file uses the following encoding: utf-8
"""Tests for the shared busy state overlay."""

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from opaque.view.widgets.busy import BusyOverlay


def _host(qtbot):
    """Build a widget the overlay can cover."""
    host = QWidget()
    qtbot.addWidget(host)
    layout = QVBoxLayout(host)
    layout.addWidget(QLabel("content"))
    host.resize(320, 240)
    return host


def test_a_new_overlay_is_hidden(qtbot, light_palette_app):
    host = _host(qtbot)
    overlay = BusyOverlay(host)
    assert not overlay.isVisibleTo(overlay.parentWidget())


def test_starting_shows_the_overlay_and_the_message(qtbot, light_palette_app):
    host = _host(qtbot)
    overlay = BusyOverlay(host)
    overlay.start("Loading the workspace")
    assert overlay.isVisibleTo(overlay.parentWidget())
    assert overlay.message_label.text() == "Loading the workspace"


def test_stopping_hides_the_overlay(qtbot, light_palette_app):
    host = _host(qtbot)
    overlay = BusyOverlay(host)
    overlay.start("Working")
    overlay.stop()
    assert not overlay.isVisibleTo(overlay.parentWidget())


def test_the_overlay_reports_a_readable_state(qtbot, light_palette_app):
    host = _host(qtbot)
    overlay = BusyOverlay(host)
    overlay.start("Working")
    assert overlay.accessibleName() != ""
    assert "Working" in overlay.accessibleDescription()


def test_the_overlay_covers_the_whole_host(qtbot, light_palette_app):
    host = _host(qtbot)
    overlay = BusyOverlay(host)
    overlay.start("Working")
    assert overlay.size() == host.size()


def test_the_overlay_tracks_a_live_resize(qtbot, light_palette_app):
    # A hidden widget never receives a resize event - Qt only delivers one
    # once the widget has a real window handle. Show it and wait for
    # exposure so the resize below is a live one, exercising the event
    # filter installed on the parent.
    host = _host(qtbot)
    host.show()
    qtbot.waitExposed(host)
    overlay = BusyOverlay(host)
    overlay.start("Working")
    host.resize(640, 480)
    assert overlay.size() == host.size()


def test_the_overlay_repaints_after_a_theme_change(qtbot, light_palette_app):
    # light_palette_app restores the session palette on teardown; a raw
    # QApplication.setPalette left the dark palette behind for every
    # later test in the session.
    from PySide6.QtWidgets import QWidget
    from opaque.view.theme import build_dark_palette, surface_variant
    from opaque.view.widgets.busy import BusyOverlay

    parent = QWidget()
    qtbot.addWidget(parent)
    overlay = BusyOverlay(parent)
    before = overlay.styleSheet()

    light_palette_app.setPalette(build_dark_palette())
    overlay.apply_theme()

    assert overlay.styleSheet() != before
    assert surface_variant() in overlay.styleSheet()
