# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

Pure WCAG 2.2 contrast maths.

This module holds no state and reads no palette. Every function takes a colour
string and gives a number, so a test can call it directly.

Reference: https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio
"""

from PySide6.QtGui import QColor

# WCAG 2.2 minimum contrast for normal body text.
TEXT_CONTRAST_MINIMUM: float = 4.5

# WCAG 2.2 minimum contrast for large text and for user interface components.
LARGE_TEXT_CONTRAST_MINIMUM: float = 3.0

_BLACK = "#000000"
_WHITE = "#ffffff"


def _channel_luminance(value: int) -> float:
    """Convert one 0-255 sRGB channel to its linear luminance part."""
    channel = value / 255.0
    if channel <= 0.03928:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(color: str) -> float:
    """
    Return the WCAG relative luminance of a colour, from 0.0 to 1.0.

    Args:
        color: Any string that QColor accepts, for example "#1a1a1a".
    """
    value = QColor(color)
    return (
        0.2126 * _channel_luminance(value.red())
        + 0.7152 * _channel_luminance(value.green())
        + 0.0722 * _channel_luminance(value.blue())
    )


def contrast_ratio(first: str, second: str) -> float:
    """
    Return the WCAG contrast ratio between two colours.

    The result is from 1.0 (the two colours are equal) to 21.0 (black on
    white). The order of the arguments does not change the result.
    """
    first_luminance = relative_luminance(first)
    second_luminance = relative_luminance(second)
    if first_luminance >= second_luminance:
        lighter, darker = first_luminance, second_luminance
    else:
        lighter, darker = second_luminance, first_luminance
    return (lighter + 0.05) / (darker + 0.05)


def readable_foreground(background: str) -> str:
    """
    Return black or white, whichever gives more contrast on the background.

    Use this when a background colour comes from user data or from a theme and
    the foreground must stay readable.
    """
    if contrast_ratio(background, _BLACK) >= contrast_ratio(background, _WHITE):
        return _BLACK
    return _WHITE
