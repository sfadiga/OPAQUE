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

from typing import Optional, Type, Dict, Any

from PySide6.QtGui import QIcon, QCloseEvent

from .base_float_window import BaseFloatWindow
from ...persistence.managers.settings_manager import SettingsManager
from ...models.base.base_model import BaseModel


class BaseFeatureWindow(BaseFloatWindow):
    """
    Enhanced feature window with model support and declarative properties
    for toolbar integration.
    """

    def __init__(self, feature_id: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.feature_id: str = feature_id

        # Set window icon from the feature interface
        self.setWindowIcon(self.feature_icon())

        # Initialize models using the feature methods
        settings_model_class = self.feature_settings_model()
        self.settings: Optional[BaseModel] = None
        if settings_model_class:
            self.settings = settings_model_class(feature_id=feature_id)

        state_model_class = self.feature_state_model()
        self.state: Optional[BaseModel] = None
        if state_model_class:
            self.state = state_model_class(feature_id=feature_id)

    # --- FEATURE API (Override in subclasses) ---

    def feature_name(self) -> str:
        """Must be overridden in subclasses"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement feature_name()")

    def feature_icon(self) -> QIcon:
        """Must be overridden in subclasses"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement feature_icon()")

    def feature_tooltip(self) -> str:
        """Must be overridden in subclasses"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement feature_tooltip()")

    def feature_visibility(self) -> bool:
        """Must be overridden in subclasses"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement feature_visibility()")

    def feature_settings_model(self) -> Optional[Type[BaseModel]]:
        """Must be overridden in subclasses"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement feature_settings_model()")

    def feature_state_model(self) -> Optional[Type[BaseModel]]:
        """Must be overridden in subclasses"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement feature_state_model()")

    # ----------------------------------------------------

    def _load_settings(self) -> None:
        """Load settings from persistence"""
        if not self.settings:
            return
        manager = SettingsManager.instance()
        # The manager now loads the data directly into the existing model instance
        manager.load_settings(self.settings)
        # After loading, apply the settings to the UI
        if hasattr(self.settings, 'apply_to_ui'):
            self.settings.apply_to_ui(self)

    def _save_settings(self) -> None:
        """Save settings to persistence"""
        if not self.settings:
            return
        if hasattr(self.settings, 'extract_from_ui'):
            self.settings.extract_from_ui(self)
        manager = SettingsManager.instance()
        # The manager now handles extracting the correct data from the model
        manager.save_settings(self.settings)

    def save_workspace_state(self) -> Dict[str, Any]:
        """Save state using model"""
        if hasattr(self, "state") and self.state:
            if hasattr(self.state, 'capture_state'):
                self.state.capture_state(self)
            return self.state.to_dict()
        return {}

    def restore_workspace_state(self, data: Dict[str, Any]) -> None:
        """Restore state using model"""
        state_model_class = self.feature_state_model()
        if state_model_class and data:
            self.state = state_model_class.from_dict(
                data, feature_id=self.feature_id)
            if hasattr(self.state, 'restore_state'):
                self.state.restore_state(self)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Save settings on close."""
        if self.settings:
            self._save_settings()
        super().closeEvent(event)
