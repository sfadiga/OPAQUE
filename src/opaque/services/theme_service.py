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


from typing import List

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QApplication

import qt_themes
from qdarkstyle import load_stylesheet
from qdarkstyle.light.palette import LightPalette
from qt_material import apply_stylesheet, list_themes

from opaque.services.service import BaseService


class ThemeService(BaseService):
    """Discovers and applies themes from qt-material and QDarkStyleSheet."""

    # Emitted with the theme name after a theme is applied. A widget that
    # paints its own colours must connect to this and repaint.
    theme_changed = Signal(str)

    # The one theme name that is always available. Any application default must
    # be a name that get_available_themes() returns.
    DEFAULT_THEME: str = "Default"

    def __init__(self, app: QApplication) -> None:
        """Initializes the theme manager.

        Args:
            app (QApplication): The main application instance.
        """
        super().__init__("themes")

        self._app: QApplication = app

        # Qt Material themes
        self._qt_material_themes: List[str] = []

        # Discover qt-themes if available
        self._qt_themes: List[str] = []

        # Qt System default themes
        self._system_themes: List[str] = [
            'QDarkStyle', 'QLightStyle', 'Default']

        # Combine all available themes
        self.available_themes: List[str] = []

        # The name of the theme applied most recently.
        self._current_theme: str = self.DEFAULT_THEME

    def initialize(self) -> None:
        self._qt_material_themes = [
            t.replace('.xml', '') for t in list_themes()]
        self._qt_themes = self._list_qt_themes()
        self.available_themes = (
            self._qt_material_themes +
            self._qt_themes +
            self._system_themes
        )
        return super().initialize()

    def cleanup(self) -> None:
        self._qt_material_themes.clear()
        self._qt_themes.clear()
        self._system_themes.clear()
        self.available_themes.clear()
        return super().cleanup()

    def _list_qt_themes(self) -> List[str]:
        """Discover themes from qt-themes package if available."""
        themes: List[str] = []
        try:
            # Add each theme with a prefix to distinguish from other sources
            for theme_name in qt_themes.get_themes().keys():
                # Format the theme name nicely (e.g., "atom_one" -> "Atom One")
                formatted_name = theme_name.replace('_', ' ').title()
                themes.append(f"qt-themes: {formatted_name}")

        except ImportError:
            pass

        return themes

    def get_available_themes(self) -> List[str]:
        """Returns a list of all discoverable theme names."""
        return self.available_themes

    def current_theme(self) -> str:
        """Return the name of the theme applied most recently."""
        return self._current_theme

    def is_valid_theme(self, theme_name: str) -> bool:
        """
        Return True when the name is one this service can apply.

        Call this before you store a theme name in a settings model. A name
        that is not on the list is applied silently as nothing, which leaves
        the settings dialog reporting a theme the user is not looking at.
        """
        return theme_name in self.available_themes

    def apply_theme(self, theme_name: str) -> bool:
        """
        Apply a theme to the application by name.

        Returns:
            True when the theme was applied. False when the name is unknown,
            in which case the current theme is left alone.
        """
        if not self.is_valid_theme(theme_name):
            return False

        if theme_name == self.DEFAULT_THEME:
            self._app.setStyleSheet("")

        elif theme_name.startswith('qt-themes: '):
            actual_theme_name = theme_name.replace('qt-themes: ', '')
            theme_key = actual_theme_name.replace(' ', '_').lower()
            try:
                qt_themes.set_theme(theme_key)
            except Exception:
                return False

        elif theme_name in self._qt_material_themes:
            # Invert secondary colors for light themes from qt-material
            invert: bool = 'light_' in theme_name
            apply_stylesheet(
                self._app, theme=f"{theme_name}.xml", invert_secondary=invert)

        elif theme_name == 'QDarkStyle':
            self._app.setStyleSheet(load_stylesheet())

        elif theme_name == 'QLightStyle':
            self._app.setStyleSheet(load_stylesheet(palette=LightPalette))

        else:
            return False

        self._current_theme = theme_name
        self.theme_changed.emit(theme_name)
        return True
