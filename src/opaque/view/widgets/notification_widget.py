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

from typing import Optional, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
    QLabel, QFrame, QScrollArea, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation

from opaque.services.service import ServiceLocator
from opaque.services.notification_service import (
    NotificationService, Notification, NotificationLevel)
from opaque.view.widgets.close_button import CloseButton
from opaque.view.widgets.confirm import confirm_destructive_action
from opaque.view.theme import (
    MINIMUM_HIT_TARGET,
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


def _build_notification_header_row(notification: Notification):
    """
    Build the header row every notification widget shows.

    ToastWidget and NotificationListItem each built this same three-part row
    (the level as text, the title, then a stretch) before this helper
    existed, then went on to style the two labels differently and add their
    own trailing widgets (a timestamp, a close button). Returns the layout
    and the two labels, so each caller can still style them its own way and
    add whatever comes after the stretch.
    """
    header = QHBoxLayout()

    level_label = QLabel(notification.level.value.upper())
    level_label.setFont(TypeScale.emphasis(TypeScale.caption()))
    header.addWidget(level_label)

    title_label = QLabel(notification.title)
    title_label.setFont(TypeScale.emphasis(TypeScale.body()))
    header.addWidget(title_label)

    header.addStretch()

    return header, level_label, title_label


class ToastWidget(QWidget):
    """
    Transient notification popup (Toast).
    """
    closed = Signal(str)  # notification_id

    # The minimum hit target from opaque.view.theme, aliased here so the
    # widget's own tests can keep reading it as a class attribute.
    CLOSE_BUTTON_SIZE = MINIMUM_HIT_TARGET

    # How long each level stays on the screen, in milliseconds. A worse level
    # needs more reading time. None means the toast never closes on its own.
    DURATION_BY_LEVEL = {
        NotificationLevel.DEBUG: 4000,
        NotificationLevel.INFO: 4000,
        NotificationLevel.WARNING: 7000,
        NotificationLevel.ERROR: 10000,
        NotificationLevel.CRITICAL: None,
    }

    @staticmethod
    def duration_for_level(level: NotificationLevel) -> Optional[int]:
        """Return the auto close delay in milliseconds, or None to never close."""
        return ToastWidget.DURATION_BY_LEVEL.get(level, 4000)

    def __init__(self, notification: Notification, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.notification = notification
        self._closing = False
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._setup_ui()
        self._setup_animation()

        # A persistent notification waits for the user. Every other level
        # closes itself after a delay that matches how bad the news is.
        self.duration = (
            None if notification.persistent
            else self.duration_for_level(notification.level)
        )
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.close_toast)
        if self.duration is not None:
            self.close_timer.start(self.duration)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setObjectName("ToastContainer")
        self.container.setStyleSheet(self._get_stylesheet())

        container_layout = QVBoxLayout(self.container)

        colors = self._get_level_colors()

        title_layout, self.level_label, self.title_label = (
            _build_notification_header_row(self.notification))
        self.level_label.setStyleSheet(f"color: {colors.foreground};")
        self.title_label.setStyleSheet(f"color: {colors.foreground};")

        self.close_button = CloseButton()
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

    def _setup_animation(self) -> None:
        """Build the fade animation. It runs forward to open, backward to close."""
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        # Connect once, in the constructor. A connection made inside
        # close_toast would be added again on every call.
        self.anim.finished.connect(self._on_fade_finished)
        self.anim.start()

    def close_toast(self) -> None:
        """
        Start the fade out. The closed signal comes when the fade has finished.

        The old code reported the close at once, so the presenter deleted the
        widget while the animation was still running and the fade out never
        appeared on the screen.
        """
        if self._closing:
            return
        self._closing = True
        self.close_timer.stop()
        # Stop before restarting. Reversing a running animation without
        # stopping it first can crash on a widget destroyed right after.
        self.anim.stop()
        self.anim.setDirection(QPropertyAnimation.Direction.Backward)
        self.anim.start()

    def _on_fade_finished(self) -> None:
        """Report the close after the fade out. Do nothing after the fade in."""
        if not self._closing:
            return
        self.close()
        self.closed.emit(self.notification.id)

    def keyPressEvent(self, event) -> None:
        """Escape closes the toast when the toast holds the keyboard focus."""
        if event.key() == Qt.Key.Key_Escape:
            self.close_toast()
            event.accept()
            return
        super().keyPressEvent(event)

    def pause_auto_close(self) -> None:
        """Stop the auto close delay. The user is reading the toast."""
        self.close_timer.stop()

    def resume_auto_close(self) -> None:
        """Start the auto close delay again, from the beginning."""
        if self.duration is not None and not self._closing:
            self.close_timer.start(self.duration)

    def enterEvent(self, event) -> None:
        """The pointer is over the toast, so hold it on the screen."""
        self.pause_auto_close()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """The pointer has left the toast, so let it close again."""
        self.resume_auto_close()
        super().leaveEvent(event)


class NotificationListItem(QFrame):
    """One notification row inside the notification dock."""

    removed = Signal(str)

    # The minimum hit target from opaque.view.theme, aliased here so the
    # widget's own tests can keep reading it as a class attribute.
    CLOSE_BUTTON_SIZE = MINIMUM_HIT_TARGET

    def __init__(self, notification: Notification, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.notification = notification
        self._setup_ui()
        self.apply_theme()

    def apply_theme(self) -> None:
        """Re-read the theme tokens. The shell calls this after a theme change."""
        self.status = status_colors(status_role_for_level(self.notification.level))
        self.timestamp_colour = muted_on_surface()
        self.level_label.setStyleSheet(
            f"color: {self.status.foreground};"
            f"background-color: {self.status.background};"
            f"border-radius: 3px; padding: 1px 5px;"
        )
        self.time_label.setStyleSheet(f"color: {self.timestamp_colour};")

    def _setup_ui(self) -> None:
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 8, 8, 8)

        # The level is written as text, not only painted as a colour. Colour
        # alone is not readable for a user with a colour vision deficiency.
        header, self.level_label, self.title_label = (
            _build_notification_header_row(self.notification))

        self.time_label = QLabel(
            self.notification.timestamp.strftime("%H:%M:%S"))
        self.time_label.setFont(TypeScale.caption())
        header.addWidget(self.time_label)

        self.close_button = CloseButton()
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
        # 0 means no limit. The notification presenter sets a real limit from
        # the max_notification_display setting.
        self._maximum_rows: int = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        self.title_label = QLabel(self.tr("Notifications"))
        self.title_label.setFont(TypeScale.emphasis(TypeScale.body()))
        header.addWidget(self.title_label)
        header.addStretch()

        self.level_box = QComboBox()
        self.level_box.setAccessibleName(self.tr("Filter by level"))
        self.level_box.setToolTip(self.tr("Show only one notification level"))
        # The first entry carries None, which means show every level.
        self.level_box.addItem(self.tr("All levels"), None)
        for level in NotificationLevel:
            self.level_box.addItem(level.value.upper(), level)
        self.level_box.currentIndexChanged.connect(
            lambda _index: self._apply_level_filter())
        header.addWidget(self.level_box)

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
        self._trim_to_maximum()
        self._update_clear_button()
        self._apply_level_filter()

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

    def set_maximum_rows(self, maximum: int) -> None:
        """
        Keep at most `maximum` rows, dropping the oldest first.

        0 means no limit. A list that grows without a limit slows the panel
        down, and nobody reads the thousandth row.
        """
        self._maximum_rows = max(0, int(maximum))
        self._trim_to_maximum()

    def _trim_to_maximum(self) -> None:
        """Remove the oldest rows until the list fits the limit."""
        if self._maximum_rows <= 0:
            return
        # items is insertion ordered, so the first key is the oldest row.
        while len(self.items) > self._maximum_rows:
            self.remove_notification(next(iter(self.items)))

    def _update_clear_button(self) -> None:
        """Enable Clear All only when there is something to clear."""
        self.clear_button.setEnabled(bool(self.items))

    def level_filter(self) -> Optional[NotificationLevel]:
        """Return the level the list is filtered to, or None for every level."""
        return self.level_box.currentData()

    def set_level_filter(self, level: Optional[NotificationLevel]) -> None:
        """
        Show only one level, or every level when level is None.

        Args:
            level: The level to show, or None.
        """
        index = self.level_box.findData(level)
        if index >= 0:
            self.level_box.setCurrentIndex(index)
        self._apply_level_filter()

    def _apply_level_filter(self) -> None:
        """Hide every row that does not match the chosen level."""
        wanted = self.level_filter()
        for item in self.items.values():
            item.setVisible(wanted is None or item.notification.level is wanted)

    def _remove_item(self, notification_id: str):
        # Notify service to remove
        service = ServiceLocator.get(NotificationService)
        service.remove_notification(notification_id)

    def _confirm_clear_all(self) -> bool:
        """
        Ask the user before the whole notification history is destroyed.

        A test replaces this method, so the question box never opens in a test
        run. Keep the question in this method and nothing else.
        """
        return confirm_destructive_action(
            self,
            self.tr("Clear all notifications?"),
            self.tr("All notifications will be removed. This cannot be undone."),
        )

    def _clear_all(self) -> None:
        """Clear every notification, after the user confirms it."""
        if not self.items:
            return
        if not self._confirm_clear_all():
            return
        service = ServiceLocator.get(NotificationService)
        service.clear_notifications()
