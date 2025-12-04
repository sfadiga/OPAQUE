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
    QLabel, QFrame, QScrollArea, QApplication, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QPoint, QSize, QRect
from PySide6.QtGui import QIcon, QFont, QColor, QPainter, QBrush, QPen

from opaque.services.service import ServiceLocator
from opaque.services.notification_service import NotificationService, Notification, NotificationLevel


class ToastWidget(QWidget):
    """
    Transient notification popup (Toast).
    """
    closed = Signal(str)  # notification_id

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
        
        # Title row
        title_layout = QHBoxLayout()
        level_label = QLabel(self.notification.level.value.upper())
        level_label.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        # Set level color
        colors = self._get_level_colors()
        level_label.setStyleSheet(f"color: {colors['text']};")
        
        title_label = QLabel(self.notification.title)
        title_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {colors['text']};")
        
        title_layout.addWidget(level_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setFlat(True)
        close_btn.setStyleSheet(f"color: {colors['text']}; font-weight: bold;")
        close_btn.clicked.connect(self.close_toast)
        title_layout.addWidget(close_btn)
        
        container_layout.addLayout(title_layout)
        
        # Message
        msg_label = QLabel(self.notification.message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"color: {colors['text']};")
        container_layout.addWidget(msg_label)
        
        layout.addWidget(self.container)

    def _get_level_colors(self):
        level = self.notification.level
        if level == NotificationLevel.ERROR or level == NotificationLevel.CRITICAL:
            return {"bg": "#dc3545", "text": "white", "border": "#bd2130"}
        elif level == NotificationLevel.WARNING:
            return {"bg": "#ffc107", "text": "black", "border": "#d39e00"}
        elif level == NotificationLevel.INFO:
            return {"bg": "#0dcaf0", "text": "black", "border": "#0aa2c0"}
        else: # DEBUG
            return {"bg": "#6c757d", "text": "white", "border": "#545b62"}

    def _get_stylesheet(self):
        colors = self._get_level_colors()
        return f"""
            QFrame#ToastContainer {{
                background-color: {colors['bg']};
                border: 1px solid {colors['border']};
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
    """Simplified item for the notification list."""
    
    removed = Signal(str)

    def __init__(self, notification: Notification, parent=None):
        super().__init__(parent)
        self.notification = notification
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header
        header = QHBoxLayout()
        
        # Color indicator based on level
        self.indicator = QFrame()
        self.indicator.setFixedSize(8, 8)
        self.indicator.setStyleSheet(f"background-color: {self._get_color()}; border-radius: 4px;")
        header.addWidget(self.indicator)
        
        title = QLabel(self.notification.title)
        font = QFont()
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        
        header.addStretch()
        
        time_label = QLabel(self.notification.timestamp.strftime("%H:%M:%S"))
        time_label.setStyleSheet("color: gray; font-size: 10px;")
        header.addWidget(time_label)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(16, 16)
        close_btn.setFlat(True)
        close_btn.setStyleSheet("QPushButton { border: none; font-weight: bold; color: gray; } QPushButton:hover { color: red; }")
        close_btn.clicked.connect(lambda: self.removed.emit(self.notification.id))
        header.addWidget(close_btn)
        
        layout.addLayout(header)
        
        # Message
        msg = QLabel(self.notification.message)
        msg.setWordWrap(True)
        # Use a slightly smaller font for message
        f = msg.font()
        f.setPointSize(f.pointSize() - 1)
        msg.setFont(f)
        layout.addWidget(msg)
        
        # Style
        # Use theme-aware border and transparent background to respect app theme
        self.setStyleSheet("""
            NotificationListItem {
                background-color: transparent;
                border-bottom: 1px solid palette(mid);
            }
        """)

    def _get_color(self):
        level = self.notification.level
        if level in (NotificationLevel.ERROR, NotificationLevel.CRITICAL): return "#dc3545"
        if level == NotificationLevel.WARNING: return "#ffc107"
        if level == NotificationLevel.INFO: return "#0dcaf0"
        return "#6c757d"


class SimplifiedNotificationList(QWidget):
    """
    A simpler list widget for notifications.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.items = {}

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with Clear All
        header = QHBoxLayout()
        title = QLabel("Notifications")
        title.setStyleSheet("font-weight: bold; padding: 4px;")
        header.addWidget(title)
        header.addStretch()
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_all)
        header.addWidget(clear_btn)
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

    def add_notification(self, notification: Notification):
        item = NotificationListItem(notification)
        item.removed.connect(self._remove_item)
        self.container_layout.insertWidget(0, item)
        self.items[notification.id] = item

    def remove_notification(self, notification_id: str):
        if notification_id in self.items:
            item = self.items.pop(notification_id)
            item.setParent(None)
            item.deleteLater()

    def clear(self):
        for item in self.items.values():
            item.setParent(None)
            item.deleteLater()
        self.items.clear()

    def _remove_item(self, notification_id: str):
        # Notify service to remove
        service = ServiceLocator.get_service("notification")
        if service:
            service.remove_notification(notification_id)

    def _clear_all(self):
        service = ServiceLocator.get_service("notification")
        if service:
            service.clear_notifications()
