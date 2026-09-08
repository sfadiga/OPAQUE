# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

The framework type scale.

Every size comes from the application font multiplied by a fixed ratio. That
keeps the sizes in proportion to each other, and it keeps them correct when the
user raises the operating system font size.

Never write a font family or a point size in a widget. Ask for a role.

Use no more than three roles on one screen. More than three sizes makes a
screen look noisy.
"""

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


class TypeScale:
    """A modular type scale built on a minor third ratio."""

    # A minor third. Moderate contrast between steps, which suits a dense
    # engineering interface.
    RATIO: float = 1.2

    # No role may produce a font smaller than this, whatever the base is.
    MINIMUM_POINT_SIZE: float = 9.0

    # Used only when there is no QApplication, which happens in a unit test
    # that does not need a widget.
    FALLBACK_POINT_SIZE: float = 9.0

    @classmethod
    def base_point_size(cls) -> float:
        """Return the application font size, which follows the OS font scale."""
        app = QApplication.instance()
        if app is None:
            return cls.FALLBACK_POINT_SIZE
        size = app.font().pointSizeF()
        if size <= 0:
            return cls.FALLBACK_POINT_SIZE
        return size

    @classmethod
    def _size_for_step(cls, step: int) -> float:
        """Return the point size for one step of the scale."""
        size = cls.base_point_size() * (cls.RATIO ** step)
        return max(size, cls.MINIMUM_POINT_SIZE)

    @classmethod
    def _font_for_step(cls, step: int) -> QFont:
        """Return a copy of the application font resized to one step."""
        app = QApplication.instance()
        font = QFont(app.font()) if app is not None else QFont()
        font.setPointSizeF(cls._size_for_step(step))
        return font

    @classmethod
    def caption(cls) -> QFont:
        """Secondary information, for example a timestamp or a unit label."""
        return cls._font_for_step(-1)

    @classmethod
    def body(cls) -> QFont:
        """Primary reading text. This is the base of the scale."""
        return cls._font_for_step(0)

    @classmethod
    def h2(cls) -> QFont:
        """A section heading inside a panel."""
        return cls._font_for_step(1)

    @classmethod
    def h1(cls) -> QFont:
        """A dialog title or a page title."""
        return cls._font_for_step(2)

    @classmethod
    def display(cls) -> QFont:
        """A single large value, for example a version number on an About page."""
        return cls._font_for_step(3)

    @classmethod
    def mono(cls, step: int = 0) -> QFont:
        """
        A fixed-width font for console output and for hexadecimal values.

        The family comes from the platform, not from a literal name, so it is
        correct on Windows, on macOS and on Linux.
        """
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSizeF(cls._size_for_step(step))
        return font

    @staticmethod
    def emphasis(font: QFont) -> QFont:
        """
        Return a copy of a font at medium weight.

        Use this for a heading or for a list item title. Never use bold inside
        body text.
        """
        emphasised = QFont(font)
        emphasised.setWeight(QFont.Weight.Medium)
        return emphasised
