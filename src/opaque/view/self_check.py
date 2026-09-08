# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

A run time interface self check for a debug build.

The test suite checks the widgets the framework ships. An application built on
the framework can still put a target that is too small, or a control a screen
reader cannot name, on the screen. Call check_interface on a window in a debug
build and read the report.
"""

import logging
from typing import List

from PySide6.QtWidgets import QAbstractButton, QLineEdit, QTabBar, QWidget

logger = logging.getLogger(__name__)

# The smallest square a pointer can hit reliably.
MINIMUM_TARGET = 24

# Qt builds these buttons itself, inside QTableWidget and QToolBar, the same
# way it builds a tab close button. The application never constructs them and
# cannot reach them to give them a name, so they are excluded on the same
# ground as a tab close button.
_PLATFORM_INTERNAL_BUTTON_CLASSES = ("QTableCornerButton", "QToolBarExtension")


def _describe(widget: QWidget) -> str:
    """Return a name a developer can find in the source."""
    name = widget.objectName()
    if name:
        return f"{type(widget).__name__}('{name}')"
    return type(widget).__name__


def _has_a_readable_label(button: QAbstractButton) -> bool:
    """True when a screen reader can announce this button."""
    text = button.text().replace("&", "").strip()
    if len(text) >= 2 and any(character.isalnum() for character in text):
        return True
    return bool(button.accessibleName().strip())


def _is_a_platform_internal_button(button: QAbstractButton) -> bool:
    """A button Qt builds for its own bookkeeping, not one the framework owns."""
    return button.metaObject().className() in _PLATFORM_INTERNAL_BUTTON_CLASSES


def check_interface(root: QWidget) -> List[str]:
    """
    Walk a widget tree and report every accessibility problem found.

    Args:
        root: The window or panel to check. Every child is checked too.

    Returns:
        One plain sentence for each problem. An empty list means the tree is
        clean. Nothing is raised and nothing is changed.
    """
    problems: List[str] = []

    for button in root.findChildren(QAbstractButton):
        # A tab close button is sized by the platform style, not by
        # application code.
        if isinstance(button.parent(), QTabBar):
            continue
        if _is_a_platform_internal_button(button):
            continue

        cap = button.maximumSize()
        if cap.width() < MINIMUM_TARGET or cap.height() < MINIMUM_TARGET:
            problems.append(
                f"{_describe(button)} is capped at "
                f"{cap.width()}x{cap.height()}, below the {MINIMUM_TARGET} "
                f"pixel minimum target."
            )

        if not _has_a_readable_label(button):
            problems.append(
                f"{_describe(button)} has no readable label. "
                f"Call setAccessibleName()."
            )

    for box in root.findChildren(QLineEdit):
        if not box.accessibleName().strip():
            problems.append(
                f"{_describe(box)} has no accessible name. "
                f"Call setAccessibleName()."
            )

    return problems


def log_interface_problems(root: QWidget) -> int:
    """
    Run check_interface and write every problem to the log.

    Args:
        root: The window to check.

    Returns:
        How many problems were found.
    """
    problems = check_interface(root)
    for problem in problems:
        logger.warning("Interface self check: %s", problem)
    return len(problems)
