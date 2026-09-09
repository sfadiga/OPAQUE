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
from abc import abstractmethod
from typing import Any, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from opaque.features.context import FeatureContext
from opaque.view.widgets.mdi_window import OpaqueMdiSubWindow


class BaseView(OpaqueMdiSubWindow):
    """
    Base class for MVP views handle the UI presentation and user interaction
    with model support and declarative properties for toolbar integration.
    """

    def __init__(
            self,
            context: FeatureContext,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._context: FeatureContext = context

    @property
    def context(self) -> FeatureContext:
        """The context this feature was built with."""
        return self._context
