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
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon


from typing import List
from opaque.models.model import BaseModel
from opaque.models.annotations import ListField, BoolField
from opaque.view.application import BaseApplication


class TodoListModel(BaseModel):

    todo_list = ListField(default=[],
                            description="To do List",
                            required=True,
                            settings=False,
                            workspace=True)

    add_time_stamp = BoolField(default=True, description="Add timestamp to each item", required=True, settings=True)

    def __init__(self, app: BaseApplication) -> None:
        super().__init__(app)


    def add_todo_list(self, value: str):
        # Create a new list with the added item
        current_list = list(self.todo_list) if self.todo_list else []
        current_list.append(value)
        # Assign to trigger automatic field notification
        self.todo_list = current_list

    def remove_todo_list(self, value: str):
        current_list = list(self.todo_list) if self.todo_list else []
        if value in current_list:
            current_list.remove(value)
            # Assign to trigger automatic field notification
            self.todo_list = current_list

    def feature_name(self) -> str:
        """Must be overridden in subclasses"""
        return "To do List"

    def feature_icon(self) -> QIcon:
        """Override in subclasses to provide icon (can return str or QIcon)"""
        return QIcon.fromTheme(QIcon.ThemeIcon.DocumentNew)

    def feature_description(self) -> str:
        """Override in subclasses"""
        return "A to do list"
