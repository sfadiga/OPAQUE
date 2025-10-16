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


class WorkspaceManager(QObject):
    """Manages workspace state persistence."""

    workspace_changed = Signal()

    def __init__(self, workspace_file: Optional[Path] = None):
        """
        Initialize the workspace manager.

        Args:
            workspace_file: Path to workspace file. If None, uses default location.
        """
        super().__init__()

        if workspace_file is None:
            workspace_file = Path.home() / ".opaque" / "workspace.json"

        self.workspace_file = workspace_file
        self.workspace_file.parent.mkdir(parents=True, exist_ok=True)

        self._workspace_data: Dict[str, Any] = {}
        # Store feature models for annotation support
        self._feature_models: Dict[str, Any] = {}
        self.load_workspace()

    def register_feature_model(self, feature_id: str, model: Any) -> None:
        """
        Register a feature model for annotation-based workspace collection.

        Args:
            feature_id: Unique identifier for the feature
            model: Model instance with annotated fields
        """
        self._feature_models[feature_id] = model

        # Collect annotated workspace fields
        workspace_data = self._collect_annotated_workspace(model)

        # Merge with existing workspace
        if feature_id not in self._workspace_data:
            self._workspace_data[feature_id] = {}

        # Initialize model with saved workspace
        for field_name, field_value in workspace_data.items():
            if field_name in self._workspace_data[feature_id]:
                # Use saved value
                setattr(model, field_name,
                        self._workspace_data[feature_id][field_name])
            else:
                # Use default value from annotation
                self._workspace_data[feature_id][field_name] = field_value

    def _collect_annotated_workspace(self, model: Any) -> Dict[str, Any]:
        """
        Collect workspace fields from a model using annotations.

        Args:
            model: Model instance to inspect

        Returns:
            Dictionary of field names and their current values
        """
        workspace_data = {}

        # Check class attributes for workspace_field annotations
        for name in dir(model.__class__):
            if not name.startswith('_'):
                try:
                    attr = getattr(model.__class__, name)
                    if hasattr(attr, '_is_workspace_field') and attr._is_workspace_field:
                        # Get current value from instance
                        if hasattr(model, name):
                            workspace_data[name] = getattr(model, name)
                        else:
                            # Use default from annotation
                            workspace_data[name] = attr.default
                except AttributeError:
                    continue

        return workspace_data

    def save_feature_state(self, feature_id: str, state: Dict[str, Any]) -> None:
        """
        Save state for a specific feature (legacy approach).

        Args:
            feature_id: Unique identifier for the feature
            state: State dictionary to save
        """
        self._workspace_data[feature_id] = state
        self.save_workspace()

    def get_feature_state(self, feature_id: str) -> Dict[str, Any]:
        """
        Get saved state for a specific feature.

        Args:
            feature_id: Unique identifier for the feature

        Returns:
            State dictionary for the feature
        """
        # If we have a registered model, collect current values
        if feature_id in self._feature_models:
            model = self._feature_models[feature_id]
            workspace_data = self._collect_annotated_workspace(model)
            self._workspace_data[feature_id] = workspace_data

        return self._workspace_data.get(feature_id, {})

    def update_feature_state(self, feature_id: str, state: Dict[str, Any]) -> None:
        """
        Update state for a specific feature.

        Args:
            feature_id: Unique identifier for the feature
            state: State dictionary to update
        """
        if feature_id not in self._workspace_data:
            self._workspace_data[feature_id] = {}

        self._workspace_data[feature_id].update(state)

        # Update model if registered
        if feature_id in self._feature_models:
            model = self._feature_models[feature_id]
            for key, value in state.items():
                if hasattr(model, key):
                    setattr(model, key, value)

        self.workspace_changed.emit()
        self.save_workspace()

    def save_window_state(self, window_id: str, geometry: bytes, state: bytes) -> None:
        """
        Save window geometry and state.

        Args:
            window_id: Unique identifier for the window
            geometry: Window geometry as bytes
            state: Window state as bytes
        """
        if "windows" not in self._workspace_data:
            self._workspace_data["windows"] = {}

        self._workspace_data["windows"][window_id] = {
            "geometry": geometry.hex() if geometry else None,
            "state": state.hex() if state else None
        }
        self.save_workspace()

    def get_window_state(self, window_id: str) -> tuple:
        """
        Get saved window geometry and state.

        Args:
            window_id: Unique identifier for the window

        Returns:
            Tuple of (geometry_bytes, state_bytes)
        """
        if "windows" in self._workspace_data and window_id in self._workspace_data["windows"]:
            window_data = self._workspace_data["windows"][window_id]
            geometry = bytes.fromhex(
                window_data["geometry"]) if window_data.get("geometry") else None
            state = bytes.fromhex(
                window_data["state"]) if window_data.get("state") else None
            return geometry, state
        return None, None

    def save_mdi_state(self, mdi_state: bytes) -> None:
        """
        Save MDI area state.

        Args:
            mdi_state: MDI area state as bytes
        """
        self._workspace_data["mdi_state"] = mdi_state.hex(
        ) if mdi_state else None
        self.save_workspace()

    def get_mdi_state(self) -> Optional[bytes]:
        """
        Get saved MDI area state.

        Returns:
            MDI area state as bytes or None
        """
        if "mdi_state" in self._workspace_data and self._workspace_data["mdi_state"]:
            return bytes.fromhex(self._workspace_data["mdi_state"])
        return None

    def save_open_features(self, feature_ids: list) -> None:
        """
        Save list of open features.

        Args:
            feature_ids: List of feature identifiers
        """
        self._workspace_data["open_features"] = feature_ids
        self.save_workspace()

    def get_open_features(self) -> list:
        """
        Get list of features that were open.

        Returns:
            List of feature identifiers
        """
        return self._workspace_data.get("open_features", [])

    def load_workspace(self) -> None:
        """Load workspace from file."""
        if self.workspace_file.exists():
            try:
                with open(self.workspace_file, 'r') as f:
                    self._workspace_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading workspace: {e}")
                self._workspace_data = {}

    def save_workspace(self) -> None:
        """Save workspace to file."""
        try:
            # Collect current values from registered models
            for feature_id, model in self._feature_models.items():
                workspace_data = self._collect_annotated_workspace(model)
                if feature_id not in self._workspace_data:
                    self._workspace_data[feature_id] = {}
                self._workspace_data[feature_id].update(workspace_data)

            with open(self.workspace_file, 'w') as f:
                json.dump(self._workspace_data, f, indent=2)
        except IOError as e:
            print(f"Error saving workspace: {e}")

    def clear_workspace(self) -> None:
        """Clear all workspace data."""
        self._workspace_data = {}
        self.save_workspace()
        self.workspace_changed.emit()

    def get_all_workspace_data(self) -> Dict[str, Any]:
        """
        Get all workspace data.

        Returns:
            Complete workspace dictionary
        """
        # Update from models before returning
        for feature_id, model in self._feature_models.items():
            workspace_data = self._collect_annotated_workspace(model)
            if feature_id not in self._workspace_data:
                self._workspace_data[feature_id] = {}
            self._workspace_data[feature_id].update(workspace_data)

        return self._workspace_data.copy()

    def export_workspace(self, export_file: Path) -> bool:
        """
        Export workspace to a file.

        Args:
            export_file: Path to export file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(export_file, 'w') as f:
                json.dump(self._workspace_data, f, indent=2)
            return True
        except IOError as e:
            print(f"Error exporting workspace: {e}")
            return False

    def import_workspace(self, import_file: Path) -> bool:
        """
        Import workspace from a file.

        Args:
            import_file: Path to import file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(import_file, 'r') as f:
                imported_workspace = json.load(f)

            self._workspace_data = imported_workspace
            self.save_workspace()

            # Update registered models
            for feature_id, model in self._feature_models.items():
                if feature_id in self._workspace_data:
                    for key, value in self._workspace_data[feature_id].items():
                        if hasattr(model, key):
                            setattr(model, key, value)

            self.workspace_changed.emit()
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error importing workspace: {e}")
            return False
