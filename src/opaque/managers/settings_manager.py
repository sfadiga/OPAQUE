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
from pathlib import Path
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal


class SettingsManager(QObject):
    """Manages application settings persistence."""

    settings_changed = Signal(str, object)  # feature_id, settings

    def __init__(self, settings_file: Optional[Path] = None):
        """
        Initialize the settings manager.

        Args:
            settings_file: Path to settings file. If None, uses default location.
        """
        super().__init__()

        if settings_file is None:
            settings_file = Path.home() / ".opaque" / "settings.json"

        self.settings_file = settings_file
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)

        self._settings: Dict[str, Dict[str, Any]] = {}
        # Store feature models for annotation support
        self._feature_models: Dict[str, Any] = {}
        self.load_settings()

    def register_model(self, feature_id: str, model: Any) -> None:
        """
        Register a model for settings management.

        Args:
            feature_id: Unique identifier for the feature
            model: Model instance with annotated fields
        """
        self._feature_models[feature_id] = model

        # Initialize model with saved settings
        if feature_id in self._settings:
            fields = model.get_fields()
            for key, value in self._settings[feature_id].items():
                if key in fields and fields[key].is_setting:
                    # Check if the property is settable
                    if hasattr(model.__class__, key) and isinstance(getattr(model.__class__, key), property):
                        if getattr(model.__class__, key).fset is None:
                            continue  # Skip read-only properties
                    setattr(model, key, value)

    def _collect_annotated_settings(self, model: Any) -> Dict[str, Any]:
        """
        Collect settings fields from a model using annotations.

        Args:
            model: Model instance to inspect

        Returns:
            Dictionary of field names and their current values
        """
        settings_data = {}
        fields = model.get_fields()
        for name, field in fields.items():
            if field.is_setting:
                settings_data[name] = getattr(model, name)
        return settings_data

    def register_feature_settings(self, feature_id: str, settings_model: Any) -> None:
        """
        Register feature settings.

        Args:
            feature_id: Unique identifier for the feature
            settings_model: Settings model instance
        """
        self.register_model(feature_id, settings_model)

    def get_feature_settings(self, feature_id: str) -> Dict[str, Any]:
        """
        Get settings for a specific feature.

        Args:
            feature_id: Unique identifier for the feature

        Returns:
            Dictionary of settings for the feature
        """
        # If we have a registered model, collect current values
        if feature_id in self._feature_models:
            model = self._feature_models[feature_id]
            settings_data = self._collect_annotated_settings(model)
            self._settings[feature_id] = settings_data

        return self._settings.get(feature_id, {})

    def update_feature_settings(self, feature_id: str, settings: Dict[str, Any]) -> None:
        """
        Update settings for a specific feature.

        Args:
            feature_id: Unique identifier for the feature
            settings: Dictionary of settings to update
        """
        if feature_id not in self._settings:
            self._settings[feature_id] = {}

        self._settings[feature_id].update(settings)

        # Update model if registered
        if feature_id in self._feature_models:
            model = self._feature_models[feature_id]
            for key, value in settings.items():
                if hasattr(model, key):
                    setattr(model, key, value)

        self.settings_changed.emit(feature_id, self._settings[feature_id])
        self.save_settings()

    def load_settings(self) -> None:
        """Load settings from file."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    self._settings = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading settings: {e}")
                self._settings = {}

    def save_feature_settings(self, feature_id: str, model: Any) -> None:
        """
        Save settings for a specific feature model.

        Args:
            feature_id: Unique identifier for the feature
            model: Model instance with annotated fields
        """
        settings_data = self._collect_annotated_settings(model)

        if feature_id not in self._settings:
            self._settings[feature_id] = {}
        self._settings[feature_id].update(settings_data)
        self.save_settings()

    def load_all_settings(self) -> None:
        """Load all settings from file and update models."""
        self.load_settings()
        for feature_id, model in self._feature_models.items():
            if feature_id in self._settings:
                for key, value in self._settings[feature_id].items():
                    if hasattr(model, key):
                        # Check if the property is settable
                        if hasattr(model.__class__, key) and isinstance(getattr(model.__class__, key), property):
                            if getattr(model.__class__, key).fset is None:
                                continue  # Skip read-only properties
                        setattr(model, key, value)

    def save_settings(self) -> None:
        """Save settings to file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except IOError as e:
            print(f"Error saving settings: {e}")

    def get_all_settings(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all settings.

        Returns:
            Dictionary of all feature settings
        """
        # Update from models before returning
        for feature_id, model in self._feature_models.items():
            settings_data = self._collect_annotated_settings(model)
            self._settings[feature_id] = settings_data

        return self._settings.copy()

    def reset_feature_settings(self, feature_id: str) -> None:
        """
        Reset settings for a specific feature to defaults.

        Args:
            feature_id: Unique identifier for the feature
        """
        if feature_id in self._settings:
            del self._settings[feature_id]
            self.save_settings()
            self.settings_changed.emit(feature_id, {})

    def export_settings(self, export_file: Path) -> bool:
        """
        Export settings to a file.

        Args:
            export_file: Path to export file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(export_file, 'w') as f:
                json.dump(self._settings, f, indent=2)
            return True
        except IOError as e:
            print(f"Error exporting settings: {e}")
            return False

    def import_settings(self, import_file: Path) -> bool:
        """
        Import settings from a file.

        Args:
            import_file: Path to import file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(import_file, 'r') as f:
                imported_settings = json.load(f)

            self._settings.update(imported_settings)
            self.save_settings()

            # Update registered models
            for feature_id, model in self._feature_models.items():
                if feature_id in self._settings:
                    for key, value in self._settings[feature_id].items():
                        if hasattr(model, key):
                            setattr(model, key, value)

            # Emit changes for all features
            for feature_id in imported_settings:
                self.settings_changed.emit(
                    feature_id, self._settings.get(feature_id, {}))

            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error importing settings: {e}")
            return False
