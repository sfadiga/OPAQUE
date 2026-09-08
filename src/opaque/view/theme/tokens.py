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

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from opaque.view.theme.contrast import relative_luminance

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
