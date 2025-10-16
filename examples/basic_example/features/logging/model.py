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
from PySide6.QtGui import QIcon
from opaque.core.model import BaseModel
from opaque.models.annotations import BoolField, IntField, StringField


class LoggingModel(BaseModel):
    """Settings for the Logging feature"""

    FEATURE_NAME = "Logging"
    FEATURE_ICON = "utilities-terminal"
    FEATURE_TOOLTIP = "Shows application logs and messages."
    DEFAULT_VISIBILITY = False

    show_timestamps = BoolField(
        default=True,
        description="Prepend a timestamp to each log message.",
        settings=True,
        binding=True
    )

    log_level = StringField(
        default="INFO",   settings=True,
        binding=True, description="The minimum level of message to display.")

    max_lines = IntField(default=1000,   settings=True,
                         binding=True, min_value=100, max_value=10000,
                         description="Maximum number of lines to keep in the log.")

    def __init__(self, feature_id: str):
        super().__init__(feature_id)
        self.log_messages = []

    def add_log(self, message: str):
        self.log_messages.append(message)
        if len(self.log_messages) > self.max_lines:
            self.log_messages.pop(0)
        self.notify("log_updated", self.log_messages)

    # --- Model Interface --------------------------------

    def feature_name(self) -> str:
        """Get the feature name associated with this model."""
        return self.FEATURE_NAME

    def feature_icon(self) -> QIcon:
        """Override in subclasses to provide icon (can return str or QIcon)"""
        return QIcon.fromTheme(self.FEATURE_ICON)

    def feature_description(self) -> str:
        """Override in subclasses"""
        return self.FEATURE_TOOLTIP

    def feature_modal(self) -> bool:
        """Override in subclasses"""
        return not self.DEFAULT_VISIBILITY
