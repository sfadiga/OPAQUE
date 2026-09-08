# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

Localisation.

The source language of the framework is English. A missing translation file is
normal, not an error, so nothing here raises and nothing here logs an error
when a file is not found.
"""

import logging
import os
from typing import List, Optional

from PySide6.QtCore import QLocale, QTranslator, Qt
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

TRANSLATION_PREFIX = "opaque"


def translations_directory() -> str:
    """Return the directory that ships the compiled .qm files."""
    return os.path.join(os.path.dirname(__file__), "translations")


def translation_candidates(
    locale: QLocale,
    prefix: str = TRANSLATION_PREFIX,
) -> List[str]:
    """
    Return the translation file base names to try, most specific first.

    Args:
        locale: The locale to translate into.
        prefix: The file name prefix, without the language part.

    Returns:
        A list such as ["opaque_pt_BR", "opaque_pt"]. The list holds no
        duplicates and keeps its order.
    """
    names: List[str] = []

    def _add(name: str) -> None:
        candidate = f"{prefix}_{name}"
        if candidate not in names:
            names.append(candidate)

    _add(locale.name())
    for language in locale.uiLanguages():
        _add(language.replace("-", "_"))
    _add(locale.name().split("_")[0])

    return names


def install_translator(
    app: QApplication,
    directory: Optional[str] = None,
    locale: Optional[QLocale] = None,
) -> Optional[QTranslator]:
    """
    Load the best matching translation and install it on the application.

    Args:
        app: The application to install the translator on.
        directory: Where the .qm files live. Defaults to the directory that
            ships with the framework.
        locale: The locale to load. Defaults to the system locale.

    Returns:
        The installed QTranslator, or None when no file matched.
    """
    locale = locale or QLocale.system()
    directory = directory or translations_directory()

    for name in translation_candidates(locale):
        translator = QTranslator(app)
        if translator.load(name, directory):
            app.installTranslator(translator)
            logger.info("Loaded the translation %s", name)
            return translator

    logger.debug("No translation found for %s, showing the source language",
                 locale.name())
    return None


def apply_layout_direction(
    app: QApplication,
    locale: Optional[QLocale] = None,
) -> Qt.LayoutDirection:
    """
    Mirror the whole interface when the language reads right to left.

    Arabic, Hebrew, Farsi and Urdu mirror the layout, so navigation moves from
    right to left and a back arrow points right. Qt mirrors anchors and
    layouts by itself once the direction is set on the application.

    Args:
        app: The application to set the direction on.
        locale: The locale to read the direction from. Defaults to the system
            locale.

    Returns:
        The direction that was applied.
    """
    locale = locale or QLocale.system()
    direction = locale.textDirection()
    app.setLayoutDirection(direction)
    return direction
