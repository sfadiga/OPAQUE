# This Python file uses the following encoding: utf-8
"""
Shared pytest fixtures for the OPAQUE framework tests.

The Qt platform is forced to "offscreen" so the suite runs the same way on a
developer machine and on a build agent with no display.

Widget tests must never read the developer's own desktop palette. The two
palette fixtures below give a fixed light palette and a fixed dark palette, so
a contrast assertion gives the same answer on every machine.
"""

import os

# This must run before any PySide6 module creates a QGuiApplication.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QColor, QPalette


def _build_palette(values: dict) -> QPalette:
    """Build a QPalette from a mapping of colour role to hex string."""
    palette = QPalette()
    for role, hex_value in values.items():
        palette.setColor(role, QColor(hex_value))
    return palette


_LIGHT_ROLES = {
    QPalette.ColorRole.Window: "#f5f5f5",
    QPalette.ColorRole.WindowText: "#1a1a1a",
    QPalette.ColorRole.Base: "#ffffff",
    QPalette.ColorRole.Text: "#1a1a1a",
    QPalette.ColorRole.Mid: "#b0b0b0",
    QPalette.ColorRole.Button: "#efefef",
    QPalette.ColorRole.ButtonText: "#1a1a1a",
    QPalette.ColorRole.Highlight: "#0b6ba8",
    QPalette.ColorRole.HighlightedText: "#ffffff",
}

_DARK_ROLES = {
    QPalette.ColorRole.Window: "#2b2b2b",
    QPalette.ColorRole.WindowText: "#e0e0e0",
    QPalette.ColorRole.Base: "#1e1e1e",
    QPalette.ColorRole.Text: "#e0e0e0",
    QPalette.ColorRole.Mid: "#5a5a5a",
    QPalette.ColorRole.Button: "#3a3a3a",
    QPalette.ColorRole.ButtonText: "#e0e0e0",
    QPalette.ColorRole.Highlight: "#a8c7e0",
    QPalette.ColorRole.HighlightedText: "#08324f",
}


@pytest.fixture
def light_palette_app(qapp):
    """Apply a fixed light palette for the duration of one test."""
    original = qapp.palette()
    qapp.setPalette(_build_palette(_LIGHT_ROLES))
    yield qapp
    qapp.setPalette(original)


@pytest.fixture
def dark_palette_app(qapp):
    """Apply a fixed dark palette for the duration of one test."""
    original = qapp.palette()
    qapp.setPalette(_build_palette(_DARK_ROLES))
    yield qapp
    qapp.setPalette(original)
