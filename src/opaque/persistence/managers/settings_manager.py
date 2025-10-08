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

import json
import os
from typing import Dict, Any, Optional, TYPE_CHECKING
from PySide6.QtCore import QStandardPaths, QCoreApplication

if TYPE_CHECKING:
    from models.settings.settings_model import SettingsModel


class SettingsManager:
    _instance: Optional['SettingsManager'] = None

    @classmethod
    def instance(cls) -> 'SettingsManager':
        if cls._instance is None:
            if not QCoreApplication.applicationName():
                # This is a fallback. The developer using the framework should set these
                # on their QApplication instance for QStandardPaths to work reliably.
                QCoreApplication.setApplicationName("UnnamedApp")
                QCoreApplication.setOrganizationName("UnnamedOrg")
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._settings_path: str = self._get_settings_path()
        self._settings: Dict[str, Any] = self._load_all_settings()

    def _get_settings_path(self) -> str:
        """Determines the path for the settings file."""
        config_dir: str = QStandardPaths.writableLocation(
            QStandardPaths.AppConfigLocation)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        return os.path.join(config_dir, "settings.json")

    def _load_all_settings(self) -> Dict[str, Any]:
        """Loads the entire settings file from disk."""
        if not os.path.exists(self._settings_path):
            return {}
        try:
            with open(self._settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_all_settings(self) -> None:
        """Saves the entire settings object to disk."""
        try:
            with open(self._settings_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4)
        except IOError as e:
            print(f"Error saving settings: {e}")

    def save_settings(self, settings_model: 'SettingsModel') -> None:
        """
        Saves the 'global' scoped fields from a settings model.
        """
        group_name: str = settings_model.get_settings_group()
        if group_name not in self._settings:
            self._settings[group_name] = {}

        model_data: Dict[str, Any] = settings_model.to_dict()
        fields: Dict[str, Any] = settings_model.get_fields()

        for name, field in fields.items():
            if field.scope == 'global':
                # Ensure value exists in model_data before assignment
                if name in model_data:
                    self._settings[group_name][name] = model_data[name]

        self._save_all_settings()

    def load_settings(self, settings_model: 'SettingsModel') -> None:
        """
        Loads 'global' scoped settings into a settings model.
        """
        group_name: str = settings_model.get_settings_group()
        group_settings: Dict[str, Any] = self._settings.get(group_name, {})

        fields: Dict[str, Any] = settings_model.get_fields()
        for name, field in fields.items():
            if field.scope == 'global' and name in group_settings:
                # Use the field's deserialize method to correctly process the value
                deserialized_value: Any = field.deserialize(
                    group_settings[name])
                setattr(settings_model, name, deserialized_value)
