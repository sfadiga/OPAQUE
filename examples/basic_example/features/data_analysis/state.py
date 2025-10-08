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

from opaque.models.worskpace.workspace_model import WorkspaceStateModel
from opaque.models.base.field_descriptors import StringField, ListField, FloatField, DictField

if TYPE_CHECKING:
    from features.data_analysis.window import DataAnalysisWindow


class DataAnalysisState(WorkspaceStateModel):
    """Workspace state for data analysis feature"""

    current_file = StringField()
    selected_items = ListField(item_type=str)
    view_mode = StringField(default="grid")
    zoom_level = FloatField(default=1.0)
    window_geometry = DictField()  # x, y, width, height

    def capture_state(self, window: 'DataAnalysisWindow') -> None:
        self.current_file = window.analysis_widget.current_file
        self.selected_items = window.analysis_widget.get_selected_items()
        self.view_mode = window.analysis_widget.view_mode
        self.zoom_level = window.analysis_widget.zoom_level

    def restore_state(self, window: 'DataAnalysisWindow') -> None:
        if self.current_file:
            window.analysis_widget.load_file(self.current_file)
        window.analysis_widget.select_items(self.selected_items)
        window.analysis_widget.set_view_mode(self.view_mode)
        window.analysis_widget.set_zoom(self.zoom_level)
