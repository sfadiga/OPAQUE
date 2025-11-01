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

from PySide6.QtWidgets import QApplication

import qt_themes
from qdarkstyle import load_stylesheet
from qdarkstyle.light.palette import LightPalette
from qt_material import apply_stylesheet, list_themes

from opaque.services.service import BaseService


class ThemeService(BaseService):
    """Discovers and applies themes from qt-material and QDarkStyleSheet."""

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

    def apply_theme(self, theme_name: str) -> None:
        """Applies a theme to the application by name."""
        if not theme_name or theme_name == 'Default':
            self._app.setStyleSheet("")
            return

        # Check if it's a qt-themes theme
        if theme_name.startswith('qt-themes: '):
            actual_theme_name = theme_name.replace('qt-themes: ', '')
            try:
                # Convert formatted name back to key (e.g., "Atom One" -> "atom_one")
                theme_key = actual_theme_name.replace(' ', '_').lower()
                # qt_themes.set_theme expects the theme key or Theme object as first parameter
                # It will apply to the current QApplication automatically
                qt_themes.set_theme(theme_key)
            except Exception as e:
                print(
                    f"Warning: Could not apply qt-themes theme '{actual_theme_name}': {e}")
            return

        if theme_name in self._qt_material_themes:
            # Invert secondary colors for light themes from qt-material
            invert: bool = 'light_' in theme_name
            apply_stylesheet(
                self._app, theme=f"{theme_name}.xml", invert_secondary=invert)

        elif theme_name == 'QDarkStyle':
            self._app.setStyleSheet(load_stylesheet())

        elif theme_name == 'QLightStyle':
            try:
                self._app.setStyleSheet(load_stylesheet(palette=LightPalette))
            except ImportError:
                print(
                    "Warning: QLightStyle not available in this version of QDarkStyleSheet.")
