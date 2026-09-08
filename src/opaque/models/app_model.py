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
from opaque.services.theme_service import ThemeService


class ApplicationModel(BaseModel):
    """
    Base model for application-wide settings.
    Developers can subclass this to add their own global settings.
    """
    FEATURE_NAME = "Application"

    # The default must be a name that ThemeService.get_available_themes()
    # returns. "Default" is the one name that is always present. A name that is
    # not on the list is applied as nothing, and the settings dialog then
    # reports a theme the user is not looking at.
    theme = Field(
        default=ThemeService.DEFAULT_THEME,
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
