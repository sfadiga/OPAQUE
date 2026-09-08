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

from typing import Optional, List, Dict
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QGraphicsOpacityEffect, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation

from opaque.services.service import ServiceLocator
from opaque.services.notification_service import NotificationService, Notification, NotificationLevel
from opaque.view.theme import (
    StatusColors,
    StatusRole,
    TypeScale,
    muted_on_surface,
    status_colors,
)


# A notification level says how bad the news is. A status role says how the
# interface must show it. Two levels can share one role.
_STATUS_BY_LEVEL = {
    NotificationLevel.DEBUG: StatusRole.NEUTRAL,
    NotificationLevel.INFO: StatusRole.INFO,
    NotificationLevel.WARNING: StatusRole.WARNING,
    NotificationLevel.ERROR: StatusRole.ERROR,
    NotificationLevel.CRITICAL: StatusRole.ERROR,
}


def status_role_for_level(level: NotificationLevel) -> StatusRole:
    """Return the status role that shows this notification level."""
    return _STATUS_BY_LEVEL.get(level, StatusRole.NEUTRAL)


class ToastWidget(QWidget):
    """
    Transient notification popup (Toast).
    """
    closed = Signal(str)  # notification_id

    # 24 pixels is the smallest close target that a pointer can hit reliably.
    CLOSE_BUTTON_SIZE = 24

    def __init__(self, notification: Notification, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.notification = notification
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._setup_ui()
        self._setup_animation()
        
        # Timer to auto-close
        if not notification.persistent:
            QTimer.singleShot(4000, self.close_toast)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QFrame()
        self.container.setObjectName("ToastContainer")
        self.container.setStyleSheet(self._get_stylesheet())
        
        container_layout = QVBoxLayout(self.container)
        
        colors = self._get_level_colors()

        title_layout = QHBoxLayout()

        self.level_label = QLabel(self.notification.level.value.upper())
        self.level_label.setFont(TypeScale.emphasis(TypeScale.caption()))
        self.level_label.setStyleSheet(f"color: {colors.foreground};")

        self.title_label = QLabel(self.notification.title)
        self.title_label.setFont(TypeScale.emphasis(TypeScale.body()))
        self.title_label.setStyleSheet(f"color: {colors.foreground};")

        title_layout.addWidget(self.level_label)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(
            self.CLOSE_BUTTON_SIZE, self.CLOSE_BUTTON_SIZE)
        self.close_button.setFlat(True)
        self.close_button.setAccessibleName(self.tr("Close notification"))
        self.close_button.setToolTip(self.tr("Close this notification"))
        self.close_button.setStyleSheet(
            f"color: {colors.foreground}; font-weight: bold;")
        self.close_button.clicked.connect(self.close_toast)
        title_layout.addWidget(self.close_button)

        container_layout.addLayout(title_layout)

        self.message_label = QLabel(self.notification.message)
        self.message_label.setWordWrap(True)
        self.message_label.setFont(TypeScale.body())
        self.message_label.setStyleSheet(f"color: {colors.foreground};")
        container_layout.addWidget(self.message_label)
        
        layout.addWidget(self.container)

    def _get_level_colors(self) -> StatusColors:
        """Return the status colour triple for this notification level."""
        return status_colors(status_role_for_level(self.notification.level))

    def _get_stylesheet(self) -> str:
        """Return the container style sheet for this notification level."""
        colors = self._get_level_colors()
        return f"""
            QFrame#ToastContainer {{
                background-color: {colors.background};
                border: 1px solid {colors.border};
                border-radius: 4px;
            }}
        """

    def _setup_animation(self):
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def close_toast(self):
        self.anim.setDirection(QPropertyAnimation.Direction.Backward)
        self.anim.finished.connect(self.close)
        self.anim.start()
        self.closed.emit(self.notification.id)


class NotificationListItem(QFrame):
    """One notification row inside the notification dock."""

    removed = Signal(str)

    # 24 pixels is the smallest close target that a pointer can hit reliably.
    CLOSE_BUTTON_SIZE = 24

    def __init__(self, notification: Notification, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.notification = notification
        self.status = status_colors(status_role_for_level(notification.level))
        self.timestamp_colour = muted_on_surface()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()

        # The level is written as text, not only painted as a colour. Colour
        # alone is not readable for a user with a colour vision deficiency.
        self.level_label = QLabel(self.notification.level.value.upper())
        self.level_label.setFont(TypeScale.emphasis(TypeScale.caption()))
        self.level_label.setStyleSheet(
            f"color: {self.status.foreground};"
            f"background-color: {self.status.background};"
            f"border-radius: 3px; padding: 1px 5px;"
        )
        header.addWidget(self.level_label)

        self.title_label = QLabel(self.notification.title)
        self.title_label.setFont(TypeScale.emphasis(TypeScale.body()))
        header.addWidget(self.title_label)

        header.addStretch()

        self.time_label = QLabel(
            self.notification.timestamp.strftime("%H:%M:%S"))
        self.time_label.setFont(TypeScale.caption())
        self.time_label.setStyleSheet(f"color: {self.timestamp_colour};")
        header.addWidget(self.time_label)

        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(
            self.CLOSE_BUTTON_SIZE, self.CLOSE_BUTTON_SIZE)
        self.close_button.setFlat(True)
        self.close_button.setAccessibleName(self.tr("Dismiss notification"))
        self.close_button.setToolTip(self.tr("Dismiss this notification"))
        self.close_button.clicked.connect(
            lambda: self.removed.emit(self.notification.id))
        header.addWidget(self.close_button)

        layout.addLayout(header)

        self.message_label = QLabel(self.notification.message)
        self.message_label.setWordWrap(True)
        self.message_label.setFont(TypeScale.body())
        layout.addWidget(self.message_label)

        self.setStyleSheet("""
            NotificationListItem {
                background-color: transparent;
                border-bottom: 1px solid palette(mid);
            }
        """)


class SimplifiedNotificationList(QWidget):
    """
    A simpler list widget for notifications.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.items: Dict[str, NotificationListItem] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        header = QHBoxLayout()
        self.title_label = QLabel(self.tr("Notifications"))
        self.title_label.setFont(TypeScale.emphasis(TypeScale.body()))
        header.addWidget(self.title_label)
        header.addStretch()

        self.clear_button = QPushButton(self.tr("Clear All"))
        self.clear_button.setToolTip(self.tr("Remove every notification"))
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self._clear_all)
        header.addWidget(self.clear_button)
        layout.addLayout(header)
        
        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.container_layout.setContentsMargins(0,0,0,0)
        self.container_layout.setSpacing(1)
        
        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)

    def add_notification(self, notification: Notification) -> None:
        """Add one notification row at the top of the list."""
        item = NotificationListItem(notification)
        item.removed.connect(self._remove_item)
        self.container_layout.insertWidget(0, item)
        self.items[notification.id] = item
        self._update_clear_button()

    def remove_notification(self, notification_id: str) -> None:
        """Remove one notification row."""
        if notification_id in self.items:
            item = self.items.pop(notification_id)
            item.setParent(None)
            item.deleteLater()
            self._update_clear_button()

    def clear(self) -> None:
        """Remove every notification row."""
        for item in self.items.values():
            item.setParent(None)
            item.deleteLater()
        self.items.clear()
        self._update_clear_button()

    def _update_clear_button(self) -> None:
        """Enable Clear All only when there is something to clear."""
        self.clear_button.setEnabled(bool(self.items))

    def _remove_item(self, notification_id: str):
        # Notify service to remove
        service = ServiceLocator.get_service("notification")
        if service:
            service.remove_notification(notification_id)

    def _confirm_clear_all(self) -> bool:
        """
        Ask the user before the whole notification history is destroyed.

        A test replaces this method, so the question box never opens in a test
        run. Keep the question in this method and nothing else.
        """
        answer = QMessageBox.question(
            self,
            self.tr("Clear all notifications?"),
            self.tr("All notifications will be removed. This cannot be undone."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _clear_all(self) -> None:
        """Clear every notification, after the user confirms it."""
        if not self.items:
            return
        if not self._confirm_clear_all():
            return
        service = ServiceLocator.get_service("notification")
        if service:
            service.clear_notifications()
