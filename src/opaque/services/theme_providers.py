# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

Theme providers for the optional third-party packages.

Every import of a theme package happens inside a method. The framework must
import on a machine that has none of them installed, so nothing here is
imported at module scope and no name below is a hard dependency.

Every provider sets a palette that matches the polarity of what it painted.
A style sheet changes what the user sees but not what QApplication.palette()
reports, and the token layer in opaque.view.theme reads only the palette. A
dark style sheet with a light palette makes every status colour wrong.
"""

import importlib.util
import logging
from typing import List

from PySide6.QtWidgets import QApplication

from opaque.services.theme_provider import ThemeProvider
from opaque.view.theme.palettes import build_dark_palette, build_light_palette

logger = logging.getLogger(__name__)


def _package_present(name: str) -> bool:
    """Return True when a package can be imported, without importing it."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _set_polarity(app: QApplication, dark: bool) -> None:
    """Give the token layer a palette that agrees with the style sheet."""
    app.setPalette(build_dark_palette() if dark else build_light_palette())


class QtThemesProvider:
    """The themes from the qt-themes package. It sets a real palette itself."""

    PACKAGE = "qt_themes"
    PREFIX = "qt-themes: "

    def names(self) -> List[str]:
        if not _package_present(self.PACKAGE):
            return []
        try:
            import qt_themes  # pylint: disable=import-outside-toplevel

            # The historic display format is kept, because a settings file
            # written by an earlier version holds these exact strings.
            return [
                self.PREFIX + key.replace("_", " ").title()
                for key in qt_themes.get_themes()
            ]
        except (ImportError, AttributeError):
            return []

    def apply(self, name: str, app: QApplication) -> bool:
        if name not in self.names():
            return False
        key = name[len(self.PREFIX):].replace(" ", "_").lower()
        try:
            import qt_themes  # pylint: disable=import-outside-toplevel

            # qt-themes installs a full palette, so clear any style sheet a
            # previous theme left behind and let the palette be the truth.
            app.setStyleSheet("")
            qt_themes.set_theme(key)
            return True
        except Exception:  # pylint: disable=broad-except
            logger.warning("qt-themes refused the theme %s", name)
            return False


class QtMaterialProvider:
    """The themes from the qt-material package. It installs a style sheet."""

    PACKAGE = "qt_material"

    def names(self) -> List[str]:
        if not _package_present(self.PACKAGE):
            return []
        try:
            from qt_material import (  # pylint: disable=import-outside-toplevel
                list_themes,
            )

            return [name.replace(".xml", "") for name in list_themes()]
        except (ImportError, AttributeError):
            return []

    def apply(self, name: str, app: QApplication) -> bool:
        if name not in self.names():
            return False
        try:
            from qt_material import (  # pylint: disable=import-outside-toplevel
                apply_stylesheet,
            )

            # A qt-material name starts with dark_ or light_, which is the
            # only statement of polarity the package makes.
            light = name.startswith("light")
            apply_stylesheet(
                app, theme=f"{name}.xml", invert_secondary=light)
            _set_polarity(app, dark=not light)
            return True
        except Exception:  # pylint: disable=broad-except
            logger.warning("qt-material refused the theme %s", name)
            return False


class QDarkStyleProvider:
    """The two QDarkStyleSheet themes. Both install a style sheet."""

    PACKAGE = "qdarkstyle"
    DARK_NAME = "QDarkStyle"
    LIGHT_NAME = "QLightStyle"

    def names(self) -> List[str]:
        if not _package_present(self.PACKAGE):
            return []
        return [self.DARK_NAME, self.LIGHT_NAME]

    def apply(self, name: str, app: QApplication) -> bool:
        if name not in self.names():
            return False
        try:
            # pylint: disable=import-outside-toplevel
            from qdarkstyle import load_stylesheet
            from qdarkstyle.light.palette import LightPalette

            if name == self.DARK_NAME:
                app.setStyleSheet(load_stylesheet())
                _set_polarity(app, dark=True)
            else:
                app.setStyleSheet(load_stylesheet(palette=LightPalette))
                _set_polarity(app, dark=False)
            return True
        except Exception:  # pylint: disable=broad-except
            logger.warning("QDarkStyle refused the theme %s", name)
            return False


def discover_providers() -> List[ThemeProvider]:
    """
    Return one instance of every provider whose package is installed.

    A provider whose package is absent reports no names, so it is dropped
    here instead of showing an empty group in the settings dialog.
    """
    candidates: List[ThemeProvider] = [
        QtThemesProvider(),
        QtMaterialProvider(),
        QDarkStyleProvider(),
    ]
    return [provider for provider in candidates if provider.names()]
