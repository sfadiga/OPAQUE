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
from PySide6.QtGui import QShortcut
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
    Return every shortcut label and key on a window, sorted by label.

    Two kinds of shortcut exist in a Qt application. A QAction carries its own
    label, and a QShortcut carries none, so the widget that owns a QShortcut
    says what it is called with setWhatsThis. A QShortcut with no whatsThis is
    left out, because a key with no label tells the user nothing.

    Args:
        window: The widget whose shortcuts are read. Every child widget is
            read too, so a menu bar action and a console search key are both
            found.

    Returns:
        A list of label and key pairs. A shortcut with no key or no label is
        left out, and the menu ampersand is removed from the label.
    """
    entries: List[Tuple[str, str]] = []
    seen: set = set()

    for action in window.actions():
        _add_action(action, entries, seen)

    for child in window.findChildren(QWidget):
        for action in child.actions():
            _add_action(action, entries, seen)

    for shortcut in window.findChildren(QShortcut):
        _add_shortcut(shortcut, entries, seen)

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


def _add_shortcut(shortcut, entries: List[Tuple[str, str]], seen: set) -> None:
    """Add one QShortcut to the list, if it has a key and a label."""
    key = shortcut.key().toString()
    if not key:
        return

    label = shortcut.whatsThis().replace("&", "").strip()
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
        # Do not keep a reference back to window here. window is this
        # dialog's Qt parent, so Qt already deletes this dialog's C++ object
        # when window's C++ object is deleted - that is the correct, one way
        # ownership direction. Storing self._window = window used to seem
        # like the safe move, to stop window from being garbage collected
        # out from under the dialog, but it reverses that direction: this
        # dialog's own Python teardown would then drop the last reference to
        # window, whose destruction deletes this same dialog's C++ object
        # through Qt's parent-child cascade while the dialog's own teardown
        # is still running, a reentrant double delete that crashed the
        # process instead of raising a catchable error. Every real call site
        # passes the running application window, which nothing garbage
        # collects mid-session, so window needs no help staying alive here.
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
