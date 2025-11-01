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

from abc import abstractmethod
from typing import Optional
from pathlib import Path

from PySide6.QtGui import QIcon

from opaque.models.abstract_model import AbstractModel
from opaque.models.annotations import StringField, IntField


class DefaultApplicationConfiguration(AbstractModel):
    """
    A class to be used by BaseApplication (and it's user's application) to configure/customize application
    """

    # Define fields at class level
    application_name = StringField(default="MyApplication")
    application_title = StringField(default="My Application")
    application_description = StringField(default="My Application Description")
    application_icon_path = StringField(default="")
    application_version = StringField(
        default="0.0.1", description="Application Version")
    application_organization = StringField(
        default="My Company", description="Application Owner")
    application_min_width = IntField(
        default=800, description="Application min width")
    application_max_width = IntField(
        default=1980, description="Application max width")
    application_min_height = IntField(
        default=600, description="Application min height")
    application_max_height = IntField(
        default=720, description="Application max height")
    settings_file_path = StringField(default="")  # Will be set in __init__
    workspace_file_extension = StringField(default=".wks")

    def __init__(self) -> None:
        super().__init__()

        # Now set the dynamic default for settings_file_path
        app_name = self.get_application_name().lower().replace(' ', '_')
        file_path = str(Path.home() / f".{app_name}" / "settings.json")
        # This sets the value through the property setter
        self.settings_file_path = file_path

    @abstractmethod
    def get_application_name(self) -> str:
        """
        Return the application name for QApplication.setApplicationName().
        This is used for settings persistence paths.

        Example: return "MyApplication"
        """
        return self.application_name

    @abstractmethod
    def get_application_title(self) -> str:
        """
        Return the main window title.

        Example: return "My Application"
        """
        return self.application_title

    @abstractmethod
    def get_application_description(self) -> str:
        """
        Return the main window title.

        Example: return "My Application does this and that..."
        """
        return self.application_description

    @abstractmethod
    def get_application_icon(self) -> QIcon:
        """
        Return the main window Icon.
        """
        return QIcon(str(self.application_icon_path))

    def get_application_version(self) -> str:
        """
        Return the application version from multiple sources:
        1. Build-time injected version (highest priority)
        2. VERSION file in project root
        3. Environment variable APP_VERSION
        4. User-provided value in configuration
        5. Default value "0.0.1" (fallback)

        Example: 1.2.3 , 0.1.0-alpha, 1.0.0-rc1 , etc
        """
        # Try to get version from VersionManager service
        try:
            from opaque.services.version_service import VersionManager
            version_manager = VersionManager()
            runtime_version = version_manager.get_version()
            if runtime_version:
                return runtime_version
        except ImportError:
            # VersionManager not available, fall back to configured value
            pass
        except Exception:
            # Any other error, fall back gracefully
            pass

        # Fall back to configured value
        return self.application_version

    @abstractmethod
    def get_application_organization(self) -> str:
        """
        Return the organization name for QApplication.setOrganizationName().
        This is used for settings persistence paths.

        Example: return "MyCompany"
        """
        return self.application_organization

    def get_application_min_size(self) -> Optional[tuple[int, int]]:
        """
        Return a tuple of width, heigh that sets the minimum size of the application
        """
        return None  # self.application_min_width, self.application_min_height

    def get_application_max_size(self) -> Optional[tuple[int, int]]:
        """
        Return a tuple of width, heigh that sets the maximum size of the application
        """
        return None  # self.application_max_width, self.application_max_height

    def get_settings_file_path(self) -> Path:
        """
        Return the path for the settings file.
        Override this to customize the settings file location.

        Default implementation uses: ~/.{app_name}/settings.json

        Returns:
            Path to settings file or None to use default location

        Example:
            return Path.home() / ".myapp" / "config" / "settings.json"
        """
        return Path(str(self.settings_file_path))

    def get_workspace_file_extension(self) -> str:
        """
        Configurable workspace file extension
        return the extension and a description (to display purposes)
        """
        return self.workspace_file_extension
