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
from typing import Any

from PySide6.QtWidgets import QApplication


from opaque.services.service import ServiceLocator
from opaque.services.theme_service import ThemeService
from opaque.services.notification_service import NotificationLevel, NotificationService
from opaque.features.context import FeatureContext
from opaque.presenters.presenter import BasePresenter

from opaque.models.app_model import ApplicationModel
from opaque.view.view import BaseView


class ApplicationPresenter(BasePresenter):

    def __init__(
            self,
            model: ApplicationModel,
            view: BaseView,
            context: FeatureContext,
    ):
        super().__init__(model, view, context)

        # --- Theme Management ---
        self.theme_service: ThemeService = ServiceLocator.get(ThemeService)

        # Fill the choices from the themes that are really installed. The list
        # depends on which optional packages are present, so it cannot be
        # declared on the field.
        theme_field = self.model.get_fields().get('theme')
        if theme_field:
            theme_field.choices = self.theme_service.get_available_themes()

        self._apply_current_theme()

        # The language cannot change while the process runs: every widget
        # already read its strings. Remember what was loaded, so a change can
        # be reported instead of looking as if it did nothing.
        self._language_at_start: str = str(self.model.language)

    def _apply_current_theme(self) -> None:
        """
        Apply the theme the model holds, falling back to the default.

        A settings file written by an older version, or by a machine with a
        different set of theme packages, can hold a name this machine cannot
        apply. Replace it instead of leaving the user with no theme and no
        message.
        """
        wanted = str(self.model.theme)
        if not self.theme_service.is_valid_theme(wanted):
            wanted = ThemeService.DEFAULT_THEME
            self.model.theme = wanted
        self.theme_service.apply_theme(wanted)

    def apply_settings(self) -> None:
        """Apply the theme, and report a language change."""
        self._apply_current_theme()
        self._report_language_change()

    def _report_language_change(self) -> None:
        """
        Tell the user that the new language arrives at the next start.

        Qt reads every string when a widget is built, so a running window
        cannot change language. Saying nothing made the setting look broken.
        """
        wanted = str(self.model.language)
        if wanted == self._language_at_start:
            return

        title = self.tr("Language changed")
        message = self.tr(
            "The new language is used the next time the application starts.")

        service = ServiceLocator.get(NotificationService)
        service.add_notification(
            level=NotificationLevel.INFO,
            title=title,
            message=message,
            source="Settings",
            persistent=True,
        )

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
