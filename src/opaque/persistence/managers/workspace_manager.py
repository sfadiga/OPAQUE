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
from typing import Dict, Any, TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from ui.core.base_application import BaseApplication
    from ui.core.base_feature_window import BaseFeatureWindow


class WorkspaceManager:
    def __init__(self, application: 'BaseApplication') -> None:
        """
        Initializes the WorkspaceManager.

        Args:
            application: The main BaseApplication instance.
        """
        self._app: 'BaseApplication' = application

    def save_workspace(self, file_path: str) -> None:
        """
        Saves the entire application workspace to a file.
        This includes window geometries, feature-specific states,
        and any settings marked with a 'workspace' scope.

        Args:
            file_path: The path to save the workspace file to.
        """
        workspace_data: Dict[str, Any] = {
            'windows': {},
            'workspace_settings': {}
        }

        registered_windows: List['BaseFeatureWindow'] = self._app.get_registered_windows(
        )

        for window in registered_windows:
            feature_id: str = window.feature_id

            # Get window geometry
            geometry_data: Dict[str, Any] = window.get_geometry_state()

            # Get feature's specific state from its state model
            state_data: Optional[Dict[str, Any]
                                 ] = window.save_workspace_state()

            # Extract workspace-scoped settings from the feature's settings model
            workspace_settings: Dict[str, Any] = self._extract_workspace_settings(
                window)

            workspace_data['windows'][feature_id] = {
                'state': state_data,
                'geometry': geometry_data,
            }
            workspace_data['workspace_settings'].update(workspace_settings)

        # Save the collected data to a file
        try:
            with open(file_path, 'w') as f:
                json.dump(workspace_data, f, indent=4)
        except IOError as e:
            print(f"Error saving workspace: {e}")
            # In a real app, we'd want to show an error dialog to the user

    def load_workspace(self, file_path: str) -> None:
        """
        Loads an application workspace from a file.

        Args:
            file_path: The path to the workspace file to load.
        """
        # 1. Read the workspace file
        try:
            with open(file_path, 'r') as f:
                workspace_data: Dict[str, Any] = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading workspace: {e}")
            return

        # 2. Get registered windows keyed by feature_id
        registered_windows: Dict[str, 'BaseFeatureWindow'] = {
            win.feature_id: win for win in self._app.get_registered_windows()
        }

        # 3. Restore window states and geometries
        window_states: Dict[str, Any] = workspace_data.get('windows', {})
        for feature_id, data in window_states.items():
            window: Optional['BaseFeatureWindow'] = registered_windows.get(
                feature_id)
            if not window:
                continue

            if 'geometry' in data:
                window.set_geometry_state(data['geometry'])

            if 'state' in data:
                window.restore_workspace_state(data['state'])

        # 4. Restore workspace-scoped settings
        workspace_settings: Dict[str, Any] = workspace_data.get(
            'workspace_settings', {})
        for group_name, settings in workspace_settings.items():
            # Find the window that owns this settings group
            target_window: Optional['BaseFeatureWindow'] = None
            for window in registered_windows.values():
                if window.settings and window.settings.get_settings_group() == group_name:
                    target_window = window
                    break

            if not target_window:
                continue

            settings_model = target_window.settings
            fields = settings_model.get_fields()
            for name, value in settings.items():
                field = fields.get(name)
                # Only set the attribute if it's a workspace-scoped field
                if field and field.scope == 'workspace':
                    deserialized_value: Any = field.deserialize(value)
                    setattr(settings_model, name, deserialized_value)

            # After updating the model from the workspace, apply changes to the UI
            settings_model.apply_to_ui(target_window)

    def _extract_workspace_settings(self, window: 'BaseFeatureWindow') -> Dict[str, Any]:
        """Extracts settings with 'workspace' scope from a window's settings model."""
        if not window.settings:
            return {}

        settings_model = window.settings
        group_name: str = settings_model.get_settings_group()
        workspace_settings: Dict[str, Any] = {}

        fields = settings_model.get_fields()
        for name, field in fields.items():
            if field.scope == 'workspace':
                if group_name not in workspace_settings:
                    workspace_settings[group_name] = {}
                workspace_settings[group_name][name] = getattr(
                    settings_model, name)

        return workspace_settings
