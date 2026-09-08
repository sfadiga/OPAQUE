# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

Semantic colour tokens.

Each function gives a hex string for one role, not for one appearance. Ask for
"the text colour on a surface", never for "dark grey". The role is read from
the active QPalette, so a theme change from qdarkstyle, qt-material or
qt-themes is picked up with no extra work.
"""

from dataclasses import dataclass
from enum import Enum

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from opaque.view.theme.contrast import (
    TEXT_CONTRAST_MINIMUM,
    contrast_ratio,
    relative_luminance,
)

# A window luminance below this value counts as a dark theme.
_DARK_THEME_LUMINANCE_LIMIT: float = 0.18


def _palette() -> QPalette:
    """Return the active application palette, or a default one in a headless test."""
    app = QApplication.instance()
    if app is None:
        return QPalette()
    return app.palette()


def _role(role: QPalette.ColorRole) -> str:
    """Return one palette role as a hex string."""
    return _palette().color(role).name()


def is_dark_theme() -> bool:
    """Return True when the active theme uses a dark window colour."""
    window = _role(QPalette.ColorRole.Window)
    return relative_luminance(window) < _DARK_THEME_LUMINANCE_LIMIT


def surface() -> str:
    """The background of a content area, for example a text view or a list."""
    return _role(QPalette.ColorRole.Base)


def on_surface() -> str:
    """The primary text colour on top of surface()."""
    return _role(QPalette.ColorRole.Text)


def surface_variant() -> str:
    """The background of a window or a panel, one step away from surface()."""
    return _role(QPalette.ColorRole.Window)


def on_surface_variant() -> str:
    """The primary text colour on top of surface_variant()."""
    return _role(QPalette.ColorRole.WindowText)


def outline() -> str:
    """A border or a separator line."""
    return _role(QPalette.ColorRole.Mid)


def interactive() -> str:
    """The background that tells the user an element responds to input."""
    return _role(QPalette.ColorRole.Highlight)


def on_interactive() -> str:
    """The text colour on top of interactive()."""
    return _role(QPalette.ColorRole.HighlightedText)


def muted_on_surface() -> str:
    """
    A dimmer text colour for secondary information, for example a timestamp.

    The colour is the primary text colour blended toward the surface. The blend
    stops at the last step that still meets the WCAG text contrast minimum, so
    the result is always readable, in a light theme and in a dark theme.
    """
    background = surface()
    text = QColor(on_surface())
    back = QColor(background)

    best = text.name()
    for step in range(1, 10):
        factor = step / 10.0
        blended = QColor(
            round(text.red() + (back.red() - text.red()) * factor),
            round(text.green() + (back.green() - text.green()) * factor),
            round(text.blue() + (back.blue() - text.blue()) * factor),
        )
        if contrast_ratio(blended.name(), background) < TEXT_CONTRAST_MINIMUM:
            break
        best = blended.name()
    return best


class StatusRole(Enum):
    """
    A semantic status, not an appearance.

    Ask for ERROR, never for red. The table below gives a different colour for
    a light theme and for a dark theme, and both pass the WCAG text contrast
    minimum.
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class StatusColors:
    """A background, a foreground and a border for one status role."""

    background: str
    foreground: str
    border: str


# Saturated fills with light text. Verified at or above 4.5:1.
_STATUS_LIGHT = {
    StatusRole.ERROR: StatusColors("#b3261e", "#ffffff", "#8c1d18"),
    StatusRole.WARNING: StatusColors("#ffd54f", "#000000", "#c8a415"),
    StatusRole.INFO: StatusColors("#0b6ba8", "#ffffff", "#084f7d"),
    StatusRole.SUCCESS: StatusColors("#1b5e20", "#ffffff", "#124016"),
    StatusRole.NEUTRAL: StatusColors("#5f6368", "#ffffff", "#45484b"),
}

# Pale fills with dark text. A saturated fill on a dark surface glares.
_STATUS_DARK = {
    StatusRole.ERROR: StatusColors("#f2b8b5", "#601410", "#8c1d18"),
    StatusRole.WARNING: StatusColors("#ffd54f", "#000000", "#c8a415"),
    StatusRole.INFO: StatusColors("#a8c7e0", "#08324f", "#084f7d"),
    StatusRole.SUCCESS: StatusColors("#a5d6a7", "#0b2e0d", "#124016"),
    StatusRole.NEUTRAL: StatusColors("#c4c7c5", "#2b2f31", "#45484b"),
}


def status_colors(role: StatusRole) -> StatusColors:
    """Return the colour triple for one status role, correct for the active theme."""
    table = _STATUS_DARK if is_dark_theme() else _STATUS_LIGHT
    return table[role]
