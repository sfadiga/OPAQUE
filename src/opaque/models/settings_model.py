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

from typing import Any
from opaque.models.model import AbstractModel


class SettingsModel(AbstractModel):
    """Base class for feature settings models"""

    class Meta:
        abstract: bool = True

    def __init__(self, feature_id: str = "") -> None:
        super().__init__()
        self.feature_id: str = feature_id

    def get_settings_group(self) -> str:
        """Get settings group name"""
        return f"feature.{self.feature_id}"

    def apply_to_ui(self, widget: Any) -> None:
        """Apply settings to UI widget"""
        pass

    def extract_from_ui(self, widget: Any) -> None:
        """Extract settings from UI widget"""
        pass
