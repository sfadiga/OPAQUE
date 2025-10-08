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

from typing import Optional, Type

from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QIcon

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from opaque import BaseFeatureWindow, BaseModel
from features.logging.settings import LoggingSettings


class LoggingWindow(BaseFeatureWindow):
    """A simple feature window that displays text logs."""

    # --- Feature Interface ---
    FEATURE_NAME = "Logging"
    FEATURE_ICON = "utilities-terminal"
    FEATURE_TOOLTIP = "Shows application logs and messages."
    DEFAULT_VISIBILITY = False
    # ----------------------------------


    def __init__(self, feature_id: str, **kwargs):
        super().__init__(feature_id, **kwargs)
        self.setWindowTitle(self.tr("Application Logging"))

        # Create and set the central widget
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.setWidget(self.log_view)

        self.log_view.append(self.tr("Logging window initialized."))

        # Load settings after the widget is initialized
        if self.settings:
            self._load_settings()

    def feature_name(self) -> str:
        return self.FEATURE_NAME

    def feature_icon(self) -> QIcon:
        return QIcon.fromTheme(self.FEATURE_ICON)

    def feature_tooltip(self) -> str:
        return self.FEATURE_TOOLTIP

    def feature_visibility(self) -> bool:
        return self.DEFAULT_VISIBILITY

    def feature_settings_model(self) -> Optional[Type[BaseModel]]:
        return LoggingSettings

    def feature_state_model(self) -> Optional[Type[BaseModel]]:
        return None  # No state model for logging window
