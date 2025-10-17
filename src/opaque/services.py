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

from pathlib import Path
from typing import Optional

from opaque.core.services import BaseService
from opaque.managers.settings_manager import SettingsManager
from opaque.managers.workspace_manager import WorkspaceManager


class SettingsService(BaseService):
    """Service for managing application settings."""

    def __init__(self, settings_file: Optional[Path] = None):
        super().__init__("settings")
        self.manager = SettingsManager(settings_file)

    def initialize(self, **kwargs) -> None:
        super().initialize()
        self.manager.load_settings_file()

    def cleanup(self) -> None:
        self.manager.save_settings_file()
        super().cleanup()


class WorkspaceService(BaseService):
    """Service for managing the application workspace."""

    def __init__(self, workspace_file: Optional[Path] = None):
        super().__init__("workspace")
        self.manager = WorkspaceManager(workspace_file)

    def initialize(self, **kwargs) -> None:
        super().initialize()
        self.manager.load_workspace()

    def cleanup(self) -> None:
        self.manager.save_workspace()
        super().cleanup()
