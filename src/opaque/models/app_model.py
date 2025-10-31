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

from opaque.models.model import BaseModel
from opaque.models.annotations import Field, UIType


class ApplicationModel(BaseModel):
    """
    Base model for application-wide settings.
    Developers can subclass this to add their own global settings.
    """
    FEATURE_NAME = "Application"

    theme = Field(
        default="light",
        description="Application theme",
        ui_type=UIType.COMBOBOX,
        settings=True
    )

    language = Field(
        default="en",
        description="UI Language",
        ui_type=UIType.COMBOBOX,
        choices=["en", "es", "fr"],
        settings=True
    )

    def feature_name(self) -> str:
        """
        Return the feature name for the settings dialog.
        """
        return self.FEATURE_NAME

    def feature_icon(self) -> QIcon:
        """
        Return the feature icon for the settings dialog.
        """
        if self.app:
            return self.app._configuration.get_application_icon()
        return QIcon.fromTheme("tool")
