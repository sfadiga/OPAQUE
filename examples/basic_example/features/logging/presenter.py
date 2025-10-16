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
from opaque.core.presenter import BasePresenter
from .model import LoggingModel
from .view import LoggingView


class LoggingPresenter(BasePresenter):
    """Presenter for the logging feature."""

    def __init__(self, feature_id: str, model: LoggingModel, view: LoggingView):
        super().__init__(feature_id=feature_id, model=model, view=view)

    def bind_events(self):
        pass

    def update(self, property_name: str, value):
        if property_name == "log_updated":
            self.view.update_log(value)
