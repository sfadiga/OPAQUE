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


from typing import List, Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from opaque.services.service import BaseService
from opaque.services.theme_provider import ThemeProvider
from opaque.services.theme_providers import discover_providers
from opaque.view.theme.palettes import build_dark_palette, build_light_palette


class ThemeService(BaseService):
    """
    Offers the themes the application can apply, and applies one.

    The service owns three built-in themes and nothing else. Every other
    theme arrives through a ThemeProvider, so no third-party theme package is
    imported here and none is a hard dependency of the framework.

    A built-in theme is a QPalette and nothing more. That matters: the token
    layer in opaque.view.theme reads QApplication.palette() for every colour,
    so a theme that changes the palette changes every widget at once.
    """

    # Emitted with the theme name after a theme is applied. A widget that
    # paints its own colours must connect to this and repaint.
    theme_changed = Signal(str)

    # The theme that is always available. Any application default must be a
    # name that get_available_themes() returns.
    DEFAULT_THEME: str = "Default"
    LIGHT_THEME: str = "Light"
    DARK_THEME: str = "Dark"

    # Built in, always offered, needs no package.
    BUILT_IN_THEMES: tuple = (DEFAULT_THEME, LIGHT_THEME, DARK_THEME)

    def __init__(self, app: QApplication) -> None:
        """Initializes the theme manager.

        Args:
            app (QApplication): The main application instance.
        """
        super().__init__("themes")

        self._app: QApplication = app

        # The palette Qt gave us before any theme was applied. "Default"
        # means "what the operating system chose", so it must be captured
        # here, before the first apply_theme call overwrites it.
        self._default_palette: QPalette = QPalette(app.palette())

        self._providers: List[ThemeProvider] = []
        self._available_themes: List[str] = list(self.BUILT_IN_THEMES)

        # The name of the theme applied most recently.
        self._current_theme: str = self.DEFAULT_THEME

    def initialize(self) -> None:
        # Ask once, at start. A package cannot appear while the process runs,
        # and the settings dialog needs a stable list.
        for provider in discover_providers():
            self._providers.append(provider)
        self._rebuild_available_themes()
        return super().initialize()

    def cleanup(self) -> None:
        self._providers.clear()
        self._available_themes = list(self.BUILT_IN_THEMES)
        return super().cleanup()

    def register_provider(self, provider: ThemeProvider) -> None:
        """
        Add a source of extra themes.

        Call this before the settings dialog is built. The names the provider
        reports join the list immediately.
        """
        self._providers.append(provider)
        self._rebuild_available_themes()

    def _rebuild_available_themes(self) -> None:
        """Recompute the offered names from the built-ins and the providers."""
        names: List[str] = list(self.BUILT_IN_THEMES)
        for provider in self._providers:
            for name in provider.names():
                if name not in names:
                    names.append(name)
        self._available_themes = names

    def get_available_themes(self) -> List[str]:
        """Returns a list of all available theme names."""
        return list(self._available_themes)

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
        return theme_name in self._available_themes

    def apply_theme(self, theme_name: str) -> bool:
        """
        Apply a theme to the application by name.

        Returns:
            True when the theme was applied. False when the name is unknown
            or the provider refused it, in which case the current theme is
            left alone.
        """
        if not self.is_valid_theme(theme_name):
            return False

        if theme_name in self.BUILT_IN_THEMES:
            applied = self._apply_built_in(theme_name)
        else:
            applied = self._apply_from_provider(theme_name)

        if not applied:
            return False

        self._current_theme = theme_name
        self.theme_changed.emit(theme_name)
        return True

    def _apply_built_in(self, theme_name: str) -> bool:
        """Apply one of the three built-in themes."""
        # Clear the style sheet first. A style sheet left by a previous theme
        # paints over the palette, so the palette would stop being the truth.
        self._app.setStyleSheet("")

        if theme_name == self.DEFAULT_THEME:
            self._app.setPalette(QPalette(self._default_palette))
        elif theme_name == self.LIGHT_THEME:
            self._app.setPalette(build_light_palette())
        else:
            self._app.setPalette(build_dark_palette())

        return True

    def _provider_for(self, theme_name: str) -> Optional[ThemeProvider]:
        """Return the first provider that offers this name, or None."""
        for provider in self._providers:
            if theme_name in provider.names():
                return provider
        return None

    def _apply_from_provider(self, theme_name: str) -> bool:
        """Hand the name to the provider that offers it."""
        provider = self._provider_for(theme_name)
        if provider is None:
            return False
        return provider.apply(theme_name, self._app)
