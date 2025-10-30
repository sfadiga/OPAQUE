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
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from opaque.view.application import BaseApplication
from opaque.presenters.presenter import BasePresenter
from .model import LoggingModel
from .view import LoggingView


class LoggingPresenter(BasePresenter):
    """Presenter for the logging feature."""

    def __init__(self, model: LoggingModel, view: LoggingView, app: 'BaseApplication'):
        super().__init__(model, view, app)

    def bind_events(self):
        pass

    def update(self, field_name: str, new_value, old_value=None, model=None):
        if field_name == "log_updated":
            self.view.update_log(new_value)

    def on_view_show(self):
        """Called when the view is shown."""
        pass

    def on_view_close(self):
        """Called when the view is closed."""
        pass
