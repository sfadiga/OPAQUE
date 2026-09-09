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
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from PySide6.QtCore import QObject, Signal

from opaque.services.service import BaseService

logger = logging.getLogger(__name__)


def stored_language(settings_file: Path) -> str:
    """
    Read the stored interface language straight from the settings file.

    The translator has to be installed before the first widget is built,
    because a widget reads its strings once, when it is created. That is
    before SettingsService exists, so this reads the one value that is needed
    that early.

    Every feature block is searched, because the block key is the feature
    identity and this must not depend on which feature holds the application
    settings.

    Args:
        settings_file: The settings file to read.

    Returns:
        The language code, or an empty string when the file, the block or the
        key is absent, unreadable or not text.
    """
    try:
        with open(settings_file, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return ""

    if not isinstance(data, dict):
        return ""

    for block in data.values():
        if isinstance(block, dict):
            value = block.get("language")
            if isinstance(value, str) and value:
                return value

    return ""


class SettingsService(BaseService):
    """Manages application settings persistence."""

    SERVICE_NAME = "settings"

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

    def initialize(self) -> None:
        self.load_settings_file()
        return super().initialize()

    def cleanup(self) -> None:
        return super().cleanup()

    def register_model(self, feature_id: str, model: Any) -> None:
        """
        Register a model for settings management.

        Args:
            feature_id: Unique identifier for the feature
            model: Model instance with annotated fields
        """
        self._feature_models[feature_id] = model

        # Fill the model from what was already loaded. initialize() reads the
        # file once; re-reading it here made every registration touch the disk.
        self.load_settings_file()
        for key, value in self._settings.get(feature_id, {}).items():
            self._apply_stored_value(model, key, value)

    def _apply_stored_value(
            self, model: Any, key: str, value: Any) -> bool:
        """
        Write one stored value into one model field, or refuse it.

        This is the only path from stored data into a model. Four methods
        used to do it, each with a different amount of care, so a value that
        one accepted another rejected and a key that was not a field at all
        could be written as a new attribute.

        The value is converted by the field first. JSON holds no types, so a
        file written by an older version, or edited by hand, hands back a
        string where an int was stored.

        Args:
            model: The model to write into.
            key: The field name from the settings file.
            value: The stored value.

        Returns:
            True when the value was written.
        """
        field = type(model).get_fields().get(key)
        if field is None:
            logger.warning(
                "Ignoring the stored setting %s: %s declares no such field",
                key, type(model).__name__)
            return False

        if not field.is_setting:
            logger.warning(
                "Ignoring the stored setting %s: the field is not declared "
                "with settings=True", key)
            return False

        declared = getattr(type(model), key, None)
        if isinstance(declared, property) and declared.fset is None:
            return False

        try:
            setattr(model, key, field.coerce(value))
        except (TypeError, ValueError):
            # A settings file written by an older version, or edited by hand,
            # can hold a value the field no longer allows. Keep the field
            # default and carry on. Raising here would stop the application
            # from starting.
            logger.warning(
                "Ignoring the stored setting %s: the value %r is not allowed",
                key, value)
            return False

        return True

    def _collect_annotated_settings(self, model: Any) -> Dict[str, Any]:
        """
        Collect settings fields from a model using annotations.

        Args:
            model: Model instance to inspect

        Returns:
            Dictionary of field names and their current values
        """
        settings_data = {}
        # Explicitly call get_fields on the class
        fields = type(model).get_fields()
        for name, field in fields.items():
            if field.is_setting:
                settings_data[name] = getattr(model, name)
        return settings_data

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
        model = self._feature_models.get(feature_id)
        if model is not None:
            for key, value in settings.items():
                self._apply_stored_value(model, key, value)

        self.settings_changed.emit(feature_id, self._settings[feature_id])
        self.save_settings_file()

    def load_settings_file(self) -> bool:
        """
        Load settings from the file.

        A file that cannot be parsed is moved aside with the suffix
        ".corrupt" and reported, instead of being silently replaced by an
        empty dictionary that the next save then writes over the user's own
        file. A file that cannot be read at all leaves the settings already
        held in memory alone, for the same reason.

        Returns:
            True when the file was read. False when there was nothing to
            read, or when reading failed.
        """
        if not self.settings_file.exists():
            return False

        try:
            with open(self.settings_file, 'r', encoding='utf-8') as handle:
                loaded = json.load(handle)
        except json.JSONDecodeError:
            kept = self.settings_file.with_suffix(
                self.settings_file.suffix + ".corrupt")
            try:
                os.replace(self.settings_file, kept)
                logger.error(
                    "The settings file %s could not be parsed. It was kept as "
                    "%s and the defaults are in use.",
                    self.settings_file, kept)
            except OSError:
                logger.exception(
                    "The settings file %s could not be parsed and could not "
                    "be moved aside", self.settings_file)
            return False
        except OSError:
            logger.exception(
                "The settings file %s could not be read. The settings already "
                "loaded are kept.", self.settings_file)
            return False

        if not isinstance(loaded, dict):
            logger.error(
                "The settings file %s holds %s, not an object. The defaults "
                "are in use.", self.settings_file, type(loaded).__name__)
            return False

        self._settings = loaded
        return True

    def save_settings_file(self) -> bool:
        """
        Save settings to the file, atomically.

        The data is written to a temporary file next to the target and then
        moved onto it, because os.replace is atomic on Windows and on POSIX.
        Writing into the target directly left a truncated file whenever the
        write failed part way, and the next start read nothing.

        Returns:
            True when the file was written.
        """
        temporary = self.settings_file.with_suffix(
            self.settings_file.suffix + ".tmp")
        try:
            with open(temporary, 'w', encoding='utf-8') as handle:
                json.dump(self._settings, handle, indent=2)
            os.replace(temporary, self.settings_file)
            return True
        except (OSError, TypeError, ValueError):
            logger.exception(
                "Failed to save the settings to %s. The previous file is "
                "unchanged.", self.settings_file)
            try:
                if temporary.exists():
                    temporary.unlink()
            except OSError:
                logger.exception(
                    "Failed to remove the temporary file %s", temporary)
            return False

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
        self.save_settings_file()

    def load_all_settings(self) -> None:
        """Load all settings from file and update models."""
        self.load_settings_file()
        for feature_id, model in self._feature_models.items():
            for key, value in self._settings.get(feature_id, {}).items():
                self._apply_stored_value(model, key, value)

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
            self.save_settings_file()
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
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2)
            return True
        except IOError:
            logger.exception("Failed to export settings")
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
            with open(import_file, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)

            self._settings.update(imported_settings)
            self.save_settings_file()

            # Update registered models
            for feature_id, model in self._feature_models.items():
                for key, value in self._settings.get(feature_id, {}).items():
                    self._apply_stored_value(model, key, value)

            # Emit changes for all features
            for feature_id in imported_settings:
                self.settings_changed.emit(
                    feature_id, self._settings.get(feature_id, {}))

            return True
        except (json.JSONDecodeError, IOError):
            logger.exception("Failed to import settings")
            return False
