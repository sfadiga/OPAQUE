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
from typing import Dict, Optional

from opaque.services.service import BaseService
from opaque.presenters.presenter import BasePresenter


class WorkspaceService(BaseService):
    """Manages workspace state persistence."""

    def __init__(self):
        """
        Initialize the workspace manager.

        Args:
            workspace_file: Path to workspace file. If None, uses default location.
        """
        super().__init__(name="workspace")

        # Store feature models for annotation support
        self._features: Dict[str, BasePresenter] = {}

    def register_feature(self, presenter: BasePresenter) -> None:
        """
        Register a feature model for annotation-based workspace collection.

        Args:
            feature_id: Unique identifier for the feature
            model: Model instance with annotated fields
        """
        self._features[presenter.feature_id] = presenter

    def unregister_feature(self, feature_id: str) -> Optional[BasePresenter]:
        """
        Collect workspace fields from a model using annotations.

        Args:
            model: Model instance to inspect

        Returns:
            Dictionary of field names and their current values
        """
        if feature_id in self._features:
            return self._features.pop(feature_id)
        return None

    def save_workspace(self, workspace_file: str) -> Optional[str]:
        """Save workspace to file."""
        workspace_data = {}
        # Collect current values from registered models
        for _, presenter in self._features.items():
            presenter.save_workspace(workspace_data)

        if workspace_data:
            with open(workspace_file, 'w', encoding='utf-8') as f:
                json.dump(workspace_data, f, indent=2)
            return Path(workspace_file).name
        return None

    def load_workspace(self, workspace_file: str) -> Optional[str]:
        """Load workspace from file."""
        if Path(workspace_file).exists():
            with open(workspace_file, 'r', encoding='utf-8') as f:
                workspace_data = json.load(f)
            if workspace_data:
                for _, presenter in self._features.items():
                    presenter.load_workspace(workspace_data)
                return Path(workspace_file).name
        return None

    def initialize(self) -> None:
        super().initialize()
        self._features.clear()

    def cleanup(self) -> None:
        super().initialize()
        self._features.clear()
