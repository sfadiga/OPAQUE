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

from opaque.models.settings.settings_model import SettingsModel
from opaque.models.base.field_descriptors import BoolField, IntField, StringField, ListField


class DataAnalysisSettings(SettingsModel):
    """Settings for data analysis feature"""

    auto_refresh = BoolField(default=True, description="Enable auto refresh")
    refresh_interval = IntField(default=5, min_value=1, max_value=60)
    data_source = StringField(default="", description="Data source path")
    filters = ListField(item_type=str, default=[])

    def apply_to_ui(self, widget):
        widget.analysis_widget.auto_refresh_checkbox.setChecked(
            self.auto_refresh)
        widget.analysis_widget.refresh_spinner.setValue(self.refresh_interval)
        widget.analysis_widget.data_source_input.setText(self.data_source)

    def extract_from_ui(self, widget):
        self.auto_refresh = widget.analysis_widget.auto_refresh_checkbox.isChecked()
        self.refresh_interval = widget.analysis_widget.refresh_spinner.value()
        self.data_source = widget.analysis_widget.data_source_input.text()
