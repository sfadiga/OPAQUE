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
import sys
import os
from typing import Optional, Type

sys.path.insert(0, os.path.join(os.path.dirname(
    __file__), '..', '..', '..', '..', 'src'))

from opaque import BaseFeatureWindow, BaseModel
from PySide6.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QSpinBox, QLineEdit, QLabel
from PySide6.QtGui import QIcon

from features.data_analysis.state import DataAnalysisState
from features.data_analysis.settings import DataAnalysisSettings


class DataAnalysisWidget(QWidget):
    """A simple widget for the Data Analysis feature."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # --- UI for Settings ---
        layout.addWidget(QLabel(self.tr("Settings")))
        self.auto_refresh_checkbox = QCheckBox(self.tr("Auto Refresh"))
        self.refresh_spinner = QSpinBox()
        self.refresh_spinner.setRange(1, 60)
        self.data_source_input = QLineEdit()
        self.data_source_input.setPlaceholderText(self.tr("Data Source Path"))

        layout.addWidget(self.auto_refresh_checkbox)
        layout.addWidget(self.refresh_spinner)
        layout.addWidget(self.data_source_input)

        # --- UI for State ---
        layout.addWidget(QLabel(self.tr("State")))
        self.current_file_label = QLabel()
        self.set_current_file_label("None")

        layout.addWidget(self.current_file_label)

        # --- Dummy properties and methods for state model ---
        self.current_file = ""
        self.view_mode = "grid"
        self.zoom_level = 1.0

    def get_selected_items(self):
        # Dummy method
        return ["item1", "item2"]

    def load_file(self, file_path):
        # Dummy method
        self.current_file = file_path
        self.set_current_file_label(file_path)

    def set_current_file_label(self, file_path):
        self.current_file_label.setText(
            self.tr("Current file: {0}").format(file_path))

    def select_items(self, items):
        # Dummy method
        print(f"Selected items: {items}")

    def set_view_mode(self, mode):
        # Dummy method
        self.view_mode = mode
        print(f"View mode set to: {mode}")

    def set_zoom(self, level):
        # Dummy method
        self.zoom_level = level
        print(f"Zoom level set to: {level}")


class DataAnalysisWindow(BaseFeatureWindow):
    """Feature window for Data Analysis."""

    # --- Feature Interface ---
    FEATURE_NAME = "Data Analysis"
    FEATURE_ICON = "document-properties"
    FEATURE_TOOLTIP = "A window to analyze data."
    DEFAULT_VISIBILITY = True
    # ----------------------------------

    def __init__(self, feature_id: str, **kwargs):
        super().__init__(feature_id, **kwargs)
        self.setWindowTitle(self.tr("Data Analysis"))

        # Create and set the central widget
        self.analysis_widget = DataAnalysisWidget()
        self.setWidget(self.analysis_widget)

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
        return DataAnalysisSettings

    def feature_state_model(self) -> Optional[Type[BaseModel]]:
        return DataAnalysisState
