# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.
"""
from typing import List

from PySide6.QtCore import Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem 
from PySide6.QtWidgets import QLineEdit, QWidget, QPushButton, QTableView, QVBoxLayout, QFrame

from opaque.view.application import BaseApplication
from opaque.view.view import BaseView


class TodoListView(BaseView):
    """A simple feature window that displays text logs."""

    item_added = Signal(str)

    def __init__(self, app: BaseApplication, parent: QWidget | None = None) -> None:
        super().__init__(app, parent)

        # Create and set the central widget
        self.item_edit = QLineEdit()
        self.add_button = QPushButton("Add")
        self.todo_view = QTableView()
        self.todo_model = QStandardItemModel(self)
        self.todo_view.setModel(self.todo_model)

        self.add_button.clicked.connect(self._on_button_click)

        frame = QFrame(self)
        vertical_layout = QVBoxLayout(frame)
        vertical_layout.addWidget(self.item_edit)
        vertical_layout.addWidget(self.add_button)
        vertical_layout.addWidget(self.todo_view)
        frame.setLayout(vertical_layout)
        self.setWidget(frame)

    def _on_button_click(self):
        self.item_added.emit(self.item_edit.text())


    def update_todo_list(self, todo_list_model):
        self.todo_model.clear()
        for item in todo_list_model:
            self.todo_model.appendRow(QStandardItem(str(item)))
