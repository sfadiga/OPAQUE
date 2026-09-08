# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

The keyboard map.

The list is read off the live QAction objects every time the dialog opens, so
it can never disagree with the application. A hand written list goes stale.
"""

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from opaque.view.theme import TypeScale


def collect_shortcuts(window: QWidget) -> List[Tuple[str, str]]:
    """
    Return every action label and key on a window, sorted by label.

    Args:
        window: The widget whose actions are read. The actions of every child
            widget are read too, so a menu bar action is found as well.

    Returns:
        A list of label and key pairs. An action with no key is left out, and
        the menu ampersand is removed from the label.
    """
    entries: List[Tuple[str, str]] = []
    seen = set()

    for action in window.actions():
        _add_action(action, entries, seen)

    for child in window.findChildren(QWidget):
        for action in child.actions():
            _add_action(action, entries, seen)

    entries.sort(key=lambda pair: pair[0])
    return entries


def _add_action(action, entries: List[Tuple[str, str]], seen: set) -> None:
    """Add one action to the list, if it has a key and is not there already."""
    key = action.shortcut().toString()
    if not key:
        return

    label = action.text().replace("&", "").strip()
    if not label:
        return

    if (label, key) in seen:
        return

    seen.add((label, key))
    entries.append((label, key))


class KeyboardMapDialog(QDialog):
    """A read only list of every keyboard shortcut the application has."""

    def __init__(self, window: QWidget, parent: Optional[QWidget] = None):
        super().__init__(parent or window)
        self.setWindowTitle(self.tr("Keyboard Shortcuts"))
        self.setMinimumSize(420, 320)

        layout = QVBoxLayout(self)

        entries = collect_shortcuts(window)

        self.table = QTableWidget(len(entries), 2, self)
        self.table.setHorizontalHeaderLabels(
            [self.tr("Action"), self.tr("Key")])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAccessibleName(self.tr("Keyboard shortcuts"))
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)

        for row, (label, key) in enumerate(entries):
            self.table.setItem(row, 0, QTableWidgetItem(label))
            key_item = QTableWidgetItem(key)
            key_item.setFont(TypeScale.mono())
            self.table.setItem(row, 1, key_item)

        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.table.setFocus(Qt.FocusReason.OtherFocusReason)
