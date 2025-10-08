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

from typing import Optional, Dict, Any, Tuple
from PySide6.QtCore import Qt, Signal, QObject, QEvent
from PySide6.QtGui import QCloseEvent, QIcon, QPixmap, QFocusEvent
from PySide6.QtWidgets import QMdiSubWindow, QWidget


class FocusInEventFilter(QObject):
    """this class is a filter to be applied on each widget from the mdi sub window
    it will allow us to trigger a focus signal on a widget is interacted with"""
    widgetFocused: Signal = Signal()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.FocusIn:
            self.widgetFocused.emit()
        return super().eventFilter(obj, event)


class BaseFloatWindow(QMdiSubWindow):
    """ A MDI sub window, that hide/show on close and load subwidget geometry"""

    windowFocused: Signal = Signal()
    windowUnfocused: Signal = Signal()
    windowOpen: Signal = Signal()
    windowClosed: Signal = Signal()

    def __init__(
        self,
        fixed_size: bool = False,
        start_open: bool = False,
        closeable: bool = False,
        parent: Optional[QWidget] = None,
        flags: Qt.WindowType = Qt.WindowType.Widget,
    ) -> None:
        super().__init__(parent, flags)
        self.setWindowIcon(QIcon(QPixmap(0, 0)))
        self._fixed_size: bool = fixed_size
        # if true close event will do real close
        self._closeable: bool = closeable
        self._minimum_size: Tuple[int, int] = (300, 200)
        if not start_open:
            self.hide()

    def focusInEvent(self, event: QFocusEvent) -> None:
        super().focusInEvent(event)
        self.windowFocused.emit()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        super().focusOutEvent(event)
        self.windowUnfocused.emit()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj == self:
            if event.type() == QEvent.Type.WindowActivate:
                self.windowFocused.emit()
            elif event.type() == QEvent.Type.WindowDeactivate:
                self.windowUnfocused.emit()
        return super().eventFilter(obj, event)

    def setWidget(self, widget: QWidget) -> None:
        super().setWidget(widget)

        widget_size_hint = widget.sizeHint()
        if widget_size_hint.isValid() and not widget_size_hint.isEmpty():
            preferred_width: int = max(
                widget_size_hint.width(), self._minimum_size[0])
            preferred_height: int = max(
                widget_size_hint.height(), self._minimum_size[1])
        else:
            preferred_width = max(widget.width(), self._minimum_size[0])
            preferred_height = max(widget.height(), self._minimum_size[1])

        self._minimum_size = (preferred_width, preferred_height)
        self.resize(preferred_width, preferred_height)

        if self._fixed_size:
            self.setMaximumSize(preferred_width, preferred_height)
            self.setMinimumSize(preferred_width, preferred_height)
            self.setWindowFlags((self.windowFlags(
            ) | Qt.WindowType.CustomizeWindowHint) & ~Qt.WindowType.WindowMaximizeButtonHint)

        focus_event_filter = FocusInEventFilter(self)
        focus_event_filter.widgetFocused.connect(self.windowFocused.emit)
        widget.installEventFilter(focus_event_filter)
        for w in widget.children():
            w.installEventFilter(focus_event_filter)

    def get_geometry_state(self) -> Dict[str, Any]:
        """Returns a dictionary containing the window's geometry and state."""
        rect = self.geometry()
        return {
            'left': rect.left(),
            'top': rect.top(),
            'width': rect.width(),
            'height': rect.height(),
            'state': self.windowState().name,
            'visible': self.isVisible()
        }

    def set_geometry_state(self, state: Dict[str, Any]) -> None:
        """Applies a geometry and state from a dictionary."""
        if not state:
            return

        width = max(
            state.get('width', self._minimum_size[0]), self._minimum_size[0])
        height = max(
            state.get('height', self._minimum_size[1]), self._minimum_size[1])
        self.setGeometry(state.get('left', 0),
                         state.get('top', 0), width, height)

        state_name = state.get('state')
        if state_name:
            qt_state = Qt.WindowState.WindowNoState
            if state_name == Qt.WindowState.WindowMaximized.name:
                qt_state = Qt.WindowState.WindowMaximized
            elif state_name == Qt.WindowState.WindowMinimized.name:
                qt_state = Qt.WindowState.WindowMinimized
            elif state_name == Qt.WindowState.WindowFullScreen.name:
                qt_state = Qt.WindowState.WindowFullScreen
            self.setWindowState(qt_state)

        if state.get('visible', False):
            self.show()
        else:
            self.hide()

    def openClose(self) -> None:
        if self.isHidden():
            self.showNormal()
        else:
            self.hide()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._closeable:
            super().closeEvent(event)
        else:
            event.accept()
            self.hide()
        self.windowClosed.emit()
