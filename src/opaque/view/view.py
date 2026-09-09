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
        self.setup_ui()

    @property
    def context(self) -> FeatureContext:
        """The context this feature was built with."""
        return self._context

    def setup_ui(self) -> None:
        """
        Build the widgets of this window. Override this.

        It is called at the end of __init__, so `self.context` is already
        there. Use `self.setWidget(widget)` to put your content in the
        window; a sub-window with no widget shows an empty frame.

        This hook is why BaseView is a class and not an alias of
        OpaqueMdiSubWindow: it is the one place a view is built, so every
        view of every feature is built the same way and at the same moment.
        """
