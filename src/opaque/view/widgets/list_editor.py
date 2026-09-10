# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

A list-of-strings editor for the settings dialog. The settings dialog builds
one for every field declared with UIType.LIST_VIEW; a ListField declares it
by default.
"""

from typing import List, Optional, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from opaque.view.theme import MINIMUM_HIT_TARGET


class ListEditor(QWidget):
    """An editable list of strings with add and remove buttons."""

    itemsChanged = Signal(list)

    def __init__(
            self,
            initial_items: Optional[Sequence[str]] = None,
            parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.list_widget = QListWidget()
        self.list_widget.setAccessibleName(self.tr("List items"))
        for text in (initial_items or []):
            self._append_item(str(text))
        layout.addWidget(self.list_widget)

        buttons = QHBoxLayout()
        self.add_button = QPushButton(self.tr("Add"))
        self.add_button.setMinimumHeight(MINIMUM_HIT_TARGET)
        self.add_button.clicked.connect(self._add_item)
        buttons.addWidget(self.add_button)

        self.remove_button = QPushButton(self.tr("Remove"))
        self.remove_button.setMinimumHeight(MINIMUM_HIT_TARGET)
        self.remove_button.clicked.connect(self._remove_selected)
        buttons.addWidget(self.remove_button)
        layout.addLayout(buttons)

        # Connected after the initial fill, so building the widget does not
        # announce a change nobody made.
        self.list_widget.itemChanged.connect(lambda _item: self._emit())

    def items(self) -> List[str]:
        """The current items, top to bottom."""
        return [
            self.list_widget.item(row).text()
            for row in range(self.list_widget.count())
        ]

    def _append_item(self, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.list_widget.addItem(item)

    def _add_item(self) -> None:
        self._append_item(self.tr("new item"))
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)
        self._emit()

    def _remove_selected(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0:
            return
        self.list_widget.takeItem(row)
        self._emit()

    def _emit(self) -> None:
        self.itemsChanged.emit(self.items())
