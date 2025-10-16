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
from opaque.models.model import AbstractModel
from opaque.models.annotations import Field


class ApplicationModel(AbstractModel):
    """
    Base model for application-wide settings.
    Developers can subclass this to add their own global settings.
    """
    FEATURE_NAME = "Application"

    theme = Field(
        default="light",
        description="Application theme",
        ui_type="combobox",
        settings=True
    )

    language = Field(
        default="en",
        description="UI Language",
        ui_type="combobox",
        choices=["en", "es", "fr"],
        settings=True
    )

    def feature_name(self) -> str:
        """
        Return the feature name for the settings dialog.
        """
        return self.FEATURE_NAME
