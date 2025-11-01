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

from typing import Optional, List, Dict, Any
from PySide6.QtCore import Signal, QObject
from opaque.services.service import ServiceLocator
from opaque.services.notification_service import NotificationService, Notification, NotificationLevel


class NotificationModel(QObject):
    """
    Model for managing notification data and business logic.
    Provides an interface between the notification service and the UI.
    """

    # Signals
    notifications_changed = Signal()
    notification_count_changed = Signal(int)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._notification_service: Optional[NotificationService] = None
        self._current_filter: Optional[NotificationLevel] = None
        self._show_unread_only: bool = False
        self._connected = False

        # Don't connect immediately - will be done during initialize()

    def _connect_to_notification_service(self) -> None:
        """Connect to the notification service"""
        self._notification_service = ServiceLocator.get_service("notification")
        if self._notification_service and hasattr(self._notification_service, 'notification_added'):
            self._notification_service.notification_added.connect(
                self._on_service_notification_added)
            self._notification_service.notification_updated.connect(
                self._on_service_notification_updated)
            self._notification_service.notification_removed.connect(
                self._on_service_notification_removed)
            self._notification_service.notifications_cleared.connect(
                self._on_service_notifications_cleared)

    def get_notifications(self, limit: Optional[int] = None) -> List[Notification]:
        """
        Get notifications based on current filters.

        Args:
            limit: Maximum number of notifications to return

        Returns:
            List of notifications
        """
        if not self._notification_service:
            return []

        from typing import cast
        service = cast(NotificationService, self._notification_service)

        return service.get_notifications(
            level_filter=self._current_filter,
            unread_only=self._show_unread_only,
            limit=limit
        )

    def get_notification_count(self, unread_only: bool = False) -> int:
        """
        Get count of notifications.

        Args:
            unread_only: Count only unread notifications

        Returns:
            Number of notifications
        """
        if not self._notification_service:
            return 0

        from typing import cast
        service = cast(NotificationService, self._notification_service)

        return service.get_notification_count(
            level_filter=self._current_filter,
            unread_only=unread_only
        )

    def add_notification(
        self,
        level: NotificationLevel,
        title: str,
        message: str,
        source: str = "System",
        persistent: bool = False
    ) -> str:
        """
        Add a new notification.

        Args:
            level: Notification level
            title: Notification title
            message: Notification message
            source: Source component
            persistent: Whether notification is persistent

        Returns:
            Notification ID
        """
        if not self._notification_service:
            return ""

        from typing import cast
        service = cast(NotificationService, self._notification_service)

        return service.add_notification(level, title, message, source, persistent)

    def mark_as_read(self, notification_id: str) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: ID of notification to mark as read

        Returns:
            True if successful
        """
        if not self._notification_service:
            return False

        from typing import cast
        service = cast(NotificationService, self._notification_service)

        return service.mark_as_read(notification_id)

    def mark_all_as_read(self) -> int:
        """
        Mark all filtered notifications as read.

        Returns:
            Number of notifications marked as read
        """
        if not self._notification_service:
            return 0

        from typing import cast
        service = cast(NotificationService, self._notification_service)

        return service.mark_all_as_read(self._current_filter)

    def remove_notification(self, notification_id: str) -> bool:
        """
        Remove a specific notification.

        Args:
            notification_id: ID of notification to remove

        Returns:
            True if successful
        """
        if not self._notification_service:
            return False

        from typing import cast
        service = cast(NotificationService, self._notification_service)

        return service.remove_notification(notification_id)

    def clear_notifications(self, level_filter: Optional[NotificationLevel] = None) -> int:
        """
        Clear notifications.

        Args:
            level_filter: Optional filter for specific notification level

        Returns:
            Number of notifications cleared
        """
        if not self._notification_service:
            return 0

        from typing import cast
        service = cast(NotificationService, self._notification_service)

        return service.clear_notifications(level_filter)

    # Filter management
    def set_level_filter(self, level: Optional[NotificationLevel]) -> None:
        """
        Set the level filter for notifications.

        Args:
            level: Notification level to filter by (None for all)
        """
        if self._current_filter != level:
            self._current_filter = level
            self.notifications_changed.emit()

    def get_level_filter(self) -> Optional[NotificationLevel]:
        """Get current level filter"""
        return self._current_filter

    def set_unread_only_filter(self, unread_only: bool) -> None:
        """
        Set whether to show only unread notifications.

        Args:
            unread_only: True to show only unread notifications
        """
        if self._show_unread_only != unread_only:
            self._show_unread_only = unread_only
            self.notifications_changed.emit()

    def get_unread_only_filter(self) -> bool:
        """Get current unread only filter"""
        return self._show_unread_only

    # Service event handlers
    def _on_service_notification_added(self, notification: Notification) -> None:
        """Handle notification added from service"""
        self.notifications_changed.emit()

        # Emit count change for unread notifications
        unread_count = self.get_notification_count(unread_only=True)
        self.notification_count_changed.emit(unread_count)

    def _on_service_notification_updated(self, notification: Notification) -> None:
        """Handle notification updated from service"""
        self.notifications_changed.emit()

        # Emit count change for unread notifications
        unread_count = self.get_notification_count(unread_only=True)
        self.notification_count_changed.emit(unread_count)

    def _on_service_notification_removed(self, notification_id: str) -> None:
        """Handle notification removed from service"""
        self.notifications_changed.emit()

        # Emit count change for unread notifications
        unread_count = self.get_notification_count(unread_only=True)
        self.notification_count_changed.emit(unread_count)

    def _on_service_notifications_cleared(self, level_filter: Optional[NotificationLevel]) -> None:
        """Handle notifications cleared from service"""
        self.notifications_changed.emit()

        # Emit count change for unread notifications
        unread_count = self.get_notification_count(unread_only=True)
        self.notification_count_changed.emit(unread_count)

    # Convenience methods for different notification levels
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

    def initialize(self) -> None:
        """Initialize the model after services are ready"""
        if not self._connected:
            self._connect_to_notification_service()
            self._connected = True
