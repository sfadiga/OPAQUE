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
from qdarkstyle import load_stylesheet
from qdarkstyle.light.palette import LightPalette
from qt_material import apply_stylesheet, list_themes


class ThemeManager:
    """Discovers and applies themes from qt-material and QDarkStyleSheet."""

    def __init__(self, app: QApplication) -> None:
        """Initializes the theme manager.

        Args:
            app (QApplication): The main application instance.
        """
        self._app: QApplication = app
        self._qt_material_themes: List[str] = [
            t.replace('.xml', '') for t in list_themes()]

        # Discover qt-themes if available
        self._qt_themes: List[str] = self._discover_qt_themes()

        self._other_themes: List[str] = [
            'QDarkStyle', 'QLightStyle', 'Default']

        # Combine all available themes
        self.available_themes: List[str] = (
            self._qt_material_themes +
            self._qt_themes +
            self._other_themes
        )

    def _discover_qt_themes(self) -> List[str]:
        """Discover themes from qt-themes package if available."""
        themes = []
        try:
            import qt_themes
            available_themes = qt_themes.get_themes()
            # Add each theme with a prefix to distinguish from other sources
            for theme_name in available_themes.keys():
                # Format the theme name nicely (e.g., "atom_one" -> "Atom One")
                formatted_name = theme_name.replace('_', ' ').title()
                themes.append(f"qt-themes: {formatted_name}")

        except ImportError:
            pass

        return themes

    def list_themes(self) -> List[str]:
        """Returns a list of all discoverable theme names."""
        return self.available_themes

    def apply_theme(self, theme_name: str) -> None:
        """Applies a theme to the application by name."""
        if not theme_name or theme_name == 'Default':
            return

        # Check if it's a qt-themes theme
        if theme_name.startswith('qt-themes: '):
            actual_theme_name = theme_name.replace('qt-themes: ', '')
            try:
                import qt_themes
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
