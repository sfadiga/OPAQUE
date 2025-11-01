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

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from PySide6.QtCore import Signal, QTimer

from opaque.services.service import BaseService


class NotificationLevel(Enum):
    """Notification severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Notification:
    """Data class representing a single notification"""
    id: str
    level: NotificationLevel
    title: str
    message: str
    source: str
    timestamp: datetime
    read: bool = False
    persistent: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary for serialization"""
        return {
            'id': self.id,
            'level': self.level.value,
            'title': self.title,
            'message': self.message,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'read': self.read,
            'persistent': self.persistent
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Notification':
        """Create notification from dictionary"""
        return cls(
            id=data['id'],
            level=NotificationLevel(data['level']),
            title=data['title'],
            message=data['message'],
            source=data['source'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            read=data.get('read', False),
            persistent=data.get('persistent', False)
        )


class NotificationService(BaseService):
    """
    Service for managing application notifications with different severity levels.
    Supports filtering, persistence, and integration with logging systems.
    """

    # Signals
    notification_added = Signal(Notification)
    notification_updated = Signal(Notification)
    notification_removed = Signal(str)  # notification id
    notifications_cleared = Signal(NotificationLevel)  # level or None for all

    def __init__(self):
        super().__init__("notification")
        self._notifications: List[Notification] = []
        self._max_notifications = 1000
        self._auto_clear_timer = QTimer()
        self._auto_clear_timer.timeout.connect(
            self._auto_clear_old_notifications)
        self._notification_counter = 0

    def initialize(self) -> None:
        """Initialize the notification service"""
        super().initialize()
        # Start auto-clear timer (every 10 minutes)
        self._auto_clear_timer.start(600000)

    def cleanup(self) -> None:
        """Clean up service resources"""
        self._auto_clear_timer.stop()
        self._notifications.clear()
        super().cleanup()

    def add_notification(
        self,
        level: NotificationLevel,
        title: str,
        message: str,
        source: str = "System",
        persistent: bool = False
    ) -> str:
        """
        Add a new notification to the system.

        Args:
            level: Severity level of the notification
            title: Short title for the notification
            message: Detailed message
            source: Source component that generated the notification
            persistent: If True, notification won't be auto-cleared

        Returns:
            Notification ID
        """
        self._notification_counter += 1
        notification_id = f"notif_{self._notification_counter}_{int(datetime.now().timestamp())}"

        notification = Notification(
            id=notification_id,
            level=level,
            title=title,
            message=message,
            source=source,
            timestamp=datetime.now(),
            persistent=persistent
        )

        self._notifications.append(notification)

        # Trim notifications if we exceed the limit
        self._trim_notifications()

        # Emit signal
        self.notification_added.emit(notification)

        return notification_id

    def get_notifications(
        self,
        level_filter: Optional[NotificationLevel] = None,
        unread_only: bool = False,
        limit: Optional[int] = None
    ) -> List[Notification]:
        """
        Get notifications with optional filtering.

        Args:
            level_filter: Filter by notification level
            unread_only: Return only unread notifications
            limit: Maximum number of notifications to return

        Returns:
            List of notifications (most recent first)
        """
        notifications = self._notifications.copy()

        # Apply filters
        if level_filter:
            notifications = [
                n for n in notifications if n.level == level_filter]

        if unread_only:
            notifications = [n for n in notifications if not n.read]

        # Sort by timestamp (most recent first)
        notifications.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply limit
        if limit:
            notifications = notifications[:limit]

        return notifications

    def get_notification_by_id(self, notification_id: str) -> Optional[Notification]:
        """Get a specific notification by ID"""
        for notification in self._notifications:
            if notification.id == notification_id:
                return notification
        return None

    def mark_as_read(self, notification_id: str) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: ID of the notification to mark as read

        Returns:
            True if notification was found and updated
        """
        notification = self.get_notification_by_id(notification_id)
        if notification:
            notification.read = True
            self.notification_updated.emit(notification)
            return True
        return False

    def mark_all_as_read(self, level_filter: Optional[NotificationLevel] = None) -> int:
        """
        Mark all notifications as read.

        Args:
            level_filter: Optional filter to mark only notifications of specific level

        Returns:
            Number of notifications marked as read
        """
        count = 0
        for notification in self._notifications:
            if not notification.read and (not level_filter or notification.level == level_filter):
                notification.read = True
                self.notification_updated.emit(notification)
                count += 1
        return count

    def remove_notification(self, notification_id: str) -> bool:
        """
        Remove a specific notification.

        Args:
            notification_id: ID of the notification to remove

        Returns:
            True if notification was found and removed
        """
        for i, notification in enumerate(self._notifications):
            if notification.id == notification_id:
                del self._notifications[i]
                self.notification_removed.emit(notification_id)
                return True
        return False

    def clear_notifications(self, level_filter: Optional[NotificationLevel] = None) -> int:
        """
        Clear notifications with optional level filtering.

        Args:
            level_filter: If specified, only clear notifications of this level

        Returns:
            Number of notifications cleared
        """
        initial_count = len(self._notifications)

        if level_filter:
            # Remove notifications of specific level (except persistent ones)
            self._notifications = [
                n for n in self._notifications
                if n.level != level_filter or n.persistent
            ]
        else:
            # Remove all non-persistent notifications
            self._notifications = [
                n for n in self._notifications if n.persistent]

        cleared_count = initial_count - len(self._notifications)

        if cleared_count > 0:
            self.notifications_cleared.emit(level_filter)

        return cleared_count

    def get_notification_count(self, level_filter: Optional[NotificationLevel] = None, unread_only: bool = False) -> int:
        """
        Get count of notifications with optional filtering.

        Args:
            level_filter: Filter by notification level
            unread_only: Count only unread notifications

        Returns:
            Number of notifications
        """
        notifications = self._notifications

        if level_filter:
            notifications = [
                n for n in notifications if n.level == level_filter]

        if unread_only:
            notifications = [n for n in notifications if not n.read]

        return len(notifications)

    def set_max_notifications(self, max_count: int) -> None:
        """
        Set the maximum number of notifications to keep in memory.

        Args:
            max_count: Maximum number of notifications
        """
        self._max_notifications = max(100, max_count)  # Minimum 100
        self._trim_notifications()

    def _trim_notifications(self) -> None:
        """Remove old notifications if we exceed the maximum count"""
        if len(self._notifications) > self._max_notifications:
            # Sort by timestamp and keep the most recent ones (plus persistent ones)
            persistent = [n for n in self._notifications if n.persistent]
            non_persistent = [
                n for n in self._notifications if not n.persistent]

            # Sort non-persistent by timestamp (newest first)
            non_persistent.sort(key=lambda x: x.timestamp, reverse=True)

            # Keep only the most recent non-persistent notifications
            max_non_persistent = self._max_notifications - len(persistent)
            if max_non_persistent > 0:
                non_persistent = non_persistent[:max_non_persistent]
            else:
                non_persistent = []

            self._notifications = persistent + non_persistent

    def _auto_clear_old_notifications(self) -> None:
        """Automatically clear old non-persistent notifications (older than 24 hours)"""
        cutoff_time = datetime.now().timestamp() - (24 * 60 * 60)  # 24 hours ago

        initial_count = len(self._notifications)
        self._notifications = [
            n for n in self._notifications
            if n.persistent or n.timestamp.timestamp() > cutoff_time
        ]

        if len(self._notifications) < initial_count:
            self.notifications_cleared.emit(None)

    # Convenience methods for common notification levels
    def debug(self, title: str, message: str, source: str = "System") -> str:
        """Add a debug notification"""
        return self.add_notification(NotificationLevel.DEBUG, title, message, source)

    def info(self, title: str, message: str, source: str = "System") -> str:
        """Add an info notification"""
        return self.add_notification(NotificationLevel.INFO, title, message, source)

    def warning(self, title: str, message: str, source: str = "System") -> str:
        """Add a warning notification"""
        return self.add_notification(NotificationLevel.WARNING, title, message, source)

    def error(self, title: str, message: str, source: str = "System") -> str:
        """Add an error notification"""
        return self.add_notification(NotificationLevel.ERROR, title, message, source)

    def critical(self, title: str, message: str, source: str = "System", persistent: bool = True) -> str:
        """Add a critical notification (persistent by default)"""
        return self.add_notification(NotificationLevel.CRITICAL, title, message, source, persistent)
