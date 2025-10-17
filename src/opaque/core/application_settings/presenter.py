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
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication

from opaque.core.presenter import BasePresenter
from opaque.managers.theme_manager import ThemeManager

from opaque.core.application_settings.model import ApplicationModel
from opaque.core.application_settings.view import ApplicationView


if TYPE_CHECKING:
    from opaque.core.application import BaseApplication

class ApplicationPresenter(BasePresenter):

    def __init__(self, feature_id: str, model: ApplicationModel, view: ApplicationView, app: 'BaseApplication'):
        super().__init__(feature_id, model, view, app)

        # --- Theme Management ---
        self.theme_manager: ThemeManager = ThemeManager(QApplication.instance())
        # Dynamically populate the theme choices
        theme_field = self.model.get_fields().get('theme')
        if theme_field:
            theme_field.choices = self.theme_manager.list_themes()
        # Apply theme on startup
        self.theme_manager.apply_theme(str(self.model.theme))

    def bind_events(self) -> None:
        pass

    def apply_settings(self) -> None:
        """Apply the theme when settings are changed."""
        self.theme_manager.apply_theme(str(self.model.theme))

    def update(self, property_name: str, value: any) -> None:
        pass
