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
from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import QApplication


from opaque.services.service import ServiceLocator
from opaque.services.theme_service import ThemeService
from opaque.presenters.presenter import BasePresenter

from opaque.models.app_model import ApplicationModel
from opaque.view.app_view import ApplicationView


if TYPE_CHECKING:
    from opaque.core.application import BaseApplication


class ApplicationPresenter(BasePresenter):

    def __init__(self, model: ApplicationModel, view: ApplicationView, app: 'BaseApplication'):
        super().__init__(model, view, app)

        # --- Theme Management ---
        self.theme_service: ThemeService = ServiceLocator.get_service("themes")
        # Dynamically populate the theme choices
        theme_field = self.model.get_fields().get('theme')
        if theme_field:
            theme_field.choices = self.theme_service.get_available_themes()
        # Apply theme on startup
        self.theme_service.apply_theme(str(self.model.theme))

    def apply_settings(self) -> None:
        """Apply the theme when settings are changed."""
        self.theme_service.apply_theme(str(self.model.theme))

    def bind_events(self) -> None:
        pass

    def update(self, field_name: str, new_value: Any, old_value: Any = None, model: Any = None) -> None:
        """
        Called when a model field changes.
        Override this to update the view based on model field changes.

        Args:
            field_name: Name of the changed field
            new_value: New value of the field
            old_value: Previous value of the field (optional for backward compatibility)
            model: The model instance that changed (optional for backward compatibility)
        """
        pass

    def on_view_show(self) -> None:
        super().on_view_show()

    def on_view_close(self) -> None:
        super().on_view_close()
