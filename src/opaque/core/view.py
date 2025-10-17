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

from typing import Any, Optional, TYPE_CHECKING

from PySide6.QtGui import QCloseEvent, QShowEvent
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from opaque.widgets.mdi_window import OpaqueMdiSubWindow

if TYPE_CHECKING:
    from opaque.core.application import BaseApplication


class BaseView(OpaqueMdiSubWindow):
    """
    Base class for MVP views handle the UI presentation and user interaction
    with model support and declarative properties for toolbar integration.
    """

    # Signals for common view events
    view_shown = Signal()
    view_closed = Signal()

    def __init__(self, feature_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._content_widget = None
        self._feature_id: str = feature_id
        self._app: Optional['BaseApplication'] = None

    @property
    def feature_id(self):
        return self._feature_id

    def set_application(self, app: 'BaseApplication'):
        self._app = app

    def app(self) -> Optional['BaseApplication']:
        return self._app

    def set_content(self, widget: QWidget):
        """Set the central content widget for the view."""
        self._content_widget = widget
        self.setWidget(self._content_widget)

    def showEvent(self, event: QShowEvent):
        """Handle show event"""
        super().showEvent(event)
        self.view_shown.emit()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Emit view_closed signal on close."""
        self.view_closed.emit()
        super().closeEvent(event)
