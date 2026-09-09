# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

The one yes/cancel confirmation used before a destructive action.

CloseableTabWidget and NotificationListItem each built this same question
box before this module existed. Each keeps its own overridable method, named
for what it asks about, because a test replaces that method so the box
never opens in a test run; both now call this one function instead of each
building the box itself.
"""

from PySide6.QtWidgets import QMessageBox, QWidget


def confirm_destructive_action(parent: QWidget, title: str, message: str) -> bool:
    """
    Ask a yes/cancel question before an action that cannot be undone.

    Args:
        parent: The widget the question box is shown over.
        title: The window title of the question box.
        message: The question itself.

    Returns:
        True when the user chose Yes, False otherwise (Cancel or closed).
    """
    answer = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Cancel,
    )
    return answer == QMessageBox.StandardButton.Yes
