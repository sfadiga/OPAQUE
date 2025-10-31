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
#from typing import TYPE_CHECKING
from typing import Any

from opaque.models.model import BaseModel
from opaque.presenters.presenter import BasePresenter

#if TYPE_CHECKING:
from opaque.view.application import BaseApplication
from opaque.view.view import BaseView

from .model import TodoListModel
from .view import TodoListView


class TodoListPresenter(BasePresenter):
    """Presenter for the logging feature."""
    def __init__(self, model: TodoListModel, view: TodoListView, app: BaseApplication) -> None:
        super().__init__(model, view, app)

    def bind_events(self) -> None:
        self.view.item_added.connect(self._add_to_list)

    def update(self, field_name: str, new_value: Any, old_value: Any = None, model: Any = None) -> None:
        """Handle model field change notifications"""
        if field_name == "todo_list":
            self._view.update_todo_list(new_value)

    def _add_to_list(self, value: str):
        self.model.add_todo_list(value)

    def on_view_show(self) -> None:
        pass

    def on_view_close(self) -> None:
        self.cleanup()
