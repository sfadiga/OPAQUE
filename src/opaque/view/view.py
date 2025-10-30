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
from typing import Any, Optional, TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from opaque.view.widgets.mdi_window import OpaqueMdiSubWindow

if TYPE_CHECKING:
    from opaque.view.application import BaseApplication


class BaseView(OpaqueMdiSubWindow):
    """
    Base class for MVP views handle the UI presentation and user interaction
    with model support and declarative properties for toolbar integration.
    """

    def __init__(self, app: 'BaseApplication', parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._app: 'BaseApplication' = app

        #self._content_widget = None

    @property
    def app(self) -> 'BaseApplication':
        return self._app
