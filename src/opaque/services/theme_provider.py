# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

The contract a theme provider must satisfy.

This module holds only the protocol. ThemeService imports it, and every
provider imports it, so the service never imports a provider and a provider
never imports the service.
"""

from typing import List, Protocol, runtime_checkable

from PySide6.QtWidgets import QApplication


@runtime_checkable
class ThemeProvider(Protocol):
    """
    One source of themes that the application can offer to the user.

    Two rules bind every implementation.

    First, `names()` must be cheap and must never raise. A provider backed by
    a package that is not installed returns an empty list. It does not raise
    ImportError, because the settings dialog calls this to fill a combo box.

    Second, `apply()` must leave the QApplication palette agreeing with what
    it painted. The token layer in opaque.view.theme reads the palette to
    decide whether the theme is dark, and every status colour follows that
    answer. A provider that installs a dark style sheet and leaves a light
    palette gives every token the wrong answer.
    """

    def names(self) -> List[str]:
        """Return the theme names this provider can apply. Empty if absent."""
        ...

    def apply(self, name: str, app: QApplication) -> bool:
        """
        Apply one of this provider's own names.

        Returns:
            True when the theme was applied. False when the name is not one
            this provider offers, or the package refused to apply it. Return
            False instead of raising.
        """
        ...
