# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

Pure geometry for the toast notification stack.

Every function here takes plain values and returns plain values. No function
reads widget state and no function moves a widget. The presenter does that.
This split lets the position rule be tested with no window on the screen.
"""

from typing import List

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtWidgets import QWidget

# More than four toasts at the same time cannot be read before they expire.
MAX_VISIBLE_TOASTS: int = 4

DEFAULT_MARGIN: int = 12
DEFAULT_SPACING: int = 8


def stacked_toast_positions(
    anchor: QRect,
    sizes: List[QSize],
    margin: int = DEFAULT_MARGIN,
    spacing: int = DEFAULT_SPACING,
) -> List[QPoint]:
    """
    Return the top left corner for each toast in a bottom right stack.

    Args:
        anchor: The area the stack must stay inside, in the same coordinate
            system that the caller will give to QWidget.move(). For a top level
            toast that is the global screen coordinate system.
        sizes: The size of each toast, newest first. The newest toast is the
            one closest to the bottom right corner.
        margin: The gap between the stack and the edge of the anchor.
        spacing: The gap between two toasts.

    Returns:
        One QPoint for each item in sizes, in the same order.
    """
    right_edge = anchor.x() + anchor.width() - margin
    bottom_edge = anchor.y() + anchor.height() - margin
    left_limit = anchor.x() + margin
    top_limit = anchor.y() + margin

    positions: List[QPoint] = []
    for size in sizes:
        x = max(right_edge - size.width(), left_limit)
        y = max(bottom_edge - size.height(), top_limit)
        positions.append(QPoint(x, y))
        bottom_edge = y - spacing
    return positions


def overflow_count(active: int, limit: int = MAX_VISIBLE_TOASTS) -> int:
    """
    Return how many of the oldest toasts must go before one more is added.

    Args:
        active: The number of toasts on the screen now.
        limit: The largest number of toasts allowed on the screen.

    Returns:
        Zero when there is room. A positive count when the oldest toasts must
        be removed first.
    """
    return max(0, active + 1 - limit)


def toast_anchor(window: QWidget) -> QRect:
    """
    Return the area the toast stack must stay inside, in global coordinates.

    A toast is a top level window, so QWidget.move() takes global screen
    coordinates. The width and the height of the main window are widget local
    lengths and must never be used as coordinates.

    Args:
        window: The main window the stack belongs to.

    Returns:
        The main window rectangle in global coordinates, clipped to the
        available area of the screen it is on.
    """
    area = QRect(window.mapToGlobal(QPoint(0, 0)), window.size())
    screen = window.screen()
    if screen is not None:
        clipped = area.intersected(screen.availableGeometry())
        if not clipped.isEmpty():
            return clipped
    return area
