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

import logging
from typing import Optional, Dict, Any, List

from PySide6.QtCore import QObject, Qt, QPoint, QTimer
from PySide6.QtWidgets import QMainWindow, QDockWidget

from opaque.models.notification_model import NotificationModel
from opaque.models.notification_settings_model import NotificationSettingsModel
from opaque.models.logger_model import LoggerModel
from opaque.view.widgets.notification_widget import SimplifiedNotificationList, ToastWidget
from opaque.services.notification_service import NotificationLevel, Notification, NotificationService
from opaque.services.service import ServiceLocator
from opaque.view.layouts.toast_stack import (
    MAX_VISIBLE_TOASTS,
    overflow_count,
    stacked_toast_positions,
    toast_anchor,
)

logger = logging.getLogger(__name__)

# The settings.json key and the dialog page identity of the notification
# settings. It is a constant because two modules need the same string.
NOTIFICATION_SETTINGS_ID = "notification_settings"


class NotificationSettingsPage:
    """
    What SettingsDialog needs from a feature, for the notification settings.

    The dialog reads exactly three members from every entry it is given:
    feature_id, model and apply_settings(). NotificationPresenter is a QObject
    and not a BasePresenter, so it cannot be such an entry itself. This
    adapter is, and it forwards the apply to the presenter.
    """

    def __init__(
            self,
            presenter: "NotificationPresenter",
            model: NotificationSettingsModel,
    ) -> None:
        self.feature_id: str = NOTIFICATION_SETTINGS_ID
        self.model: NotificationSettingsModel = model
        self._presenter = presenter

    def apply_settings(self) -> None:
        """Called by the settings dialog after it wrote the model."""
        self._presenter.apply_settings()


class NotificationPresenter(QObject):
    """
    Presenter for managing notification system integration.
    Coordinates between notification models, services, and views.
    This is a special system presenter that doesn't follow the standard MVP pattern.
    """

    def __init__(self, main_window: Optional[QMainWindow] = None):
        super().__init__()
        self._main_window = main_window

        # Models
        self._notification_model: Optional[NotificationModel] = None
        self._settings_model: Optional[NotificationSettingsModel] = None
        self._settings_page: Optional[NotificationSettingsPage] = None
        self._logger_model: Optional[LoggerModel] = None

        # Views
        self._notification_list: Optional[SimplifiedNotificationList] = None
        self._dock_widget: Optional[QDockWidget] = None
        
        # Toasts
        self._active_toasts: List[ToastWidget] = []

        # Initialize components
        self._setup_models()
        self._setup_views()
        self._connect_signals()
        
        # Connect to service for direct toast trigger
        service = ServiceLocator.get_service("notification")
        if service and isinstance(service, NotificationService):
            service.notification_added.connect(self._on_service_notification_added)
            service.notification_removed.connect(self._on_service_notification_removed)
            service.notifications_cleared.connect(self._on_service_notifications_cleared)

    def _setup_models(self) -> None:
        """Initialize the models"""
        try:
            self._notification_model = NotificationModel(self._main_window)
            self._settings_model = NotificationSettingsModel()
            self._logger_model = LoggerModel(self._main_window)

            # Initialize models after services are ready
            if self._notification_model:
                self._notification_model.initialize()
            if self._logger_model:
                self._logger_model.initialize()
            
            # Register the settings model so its values are saved and drawn.
            settings_service = ServiceLocator.get_service("settings")
            if settings_service is not None:
                settings_service.register_model(
                    NOTIFICATION_SETTINGS_ID, self._settings_model)
                settings_service.save_feature_settings(
                    NOTIFICATION_SETTINGS_ID, self._settings_model)

            self._settings_page = NotificationSettingsPage(
                self, self._settings_model)

        except Exception:
            logger.exception("Failed to set up the notification models")

    def _setup_views(self) -> None:
        """Initialize the views"""
        try:
            # Create simplified list widget
            self._notification_list = SimplifiedNotificationList(self._main_window)
            
            self._dock_widget = QDockWidget(
                self.tr("Notifications"), self._main_window)
            # QMainWindow.saveState() drops any dock without an object name.
            self._dock_widget.setObjectName("NotificationDock")
            self._dock_widget.setWidget(self._notification_list)
            self._dock_widget.setAllowedAreas(
                Qt.DockWidgetArea.AllDockWidgetAreas)

            if self._main_window:
                self._main_window.addDockWidget(
                    Qt.DockWidgetArea.BottomDockWidgetArea,
                    self._dock_widget
                )
                # The dock starts closed. The toolbar button opens it. An empty
                # panel must not take height from the MDI area at start up.
                self._dock_widget.hide()

        except Exception:
            logger.exception("Failed to set up the notification views")

    def _connect_signals(self) -> None:
        """Connect model and view signals"""
        try:
            if self._notification_model:
                # Connect notification model signals
                self._notification_model.notifications_changed.connect(
                    self._on_notifications_changed
                )
                self._notification_model.notification_count_changed.connect(
                    self._on_notification_count_changed
                )

            if self._logger_model:
                # Connect logger model signals
                self._logger_model.log_entry_added.connect(
                    self._on_log_entry_added
                )
                self._logger_model.configuration_changed.connect(
                    self._on_logger_configuration_changed
                )

        except Exception:
            logger.exception("Failed to connect the notification signals")

    def _on_service_notification_added(self, notification: Notification):
        # Every notification reaches the interface through this method, so
        # this is the one place the display settings have to be honoured.
        if not self._shows(notification):
            return

        if self._notification_list:
            self._notification_list.add_notification(notification)

        # Show Toast if enabled
        if self._settings_model and self._settings_model.enable_toasts:
            self._show_toast(notification)

    def _shows(self, notification: Notification) -> bool:
        """
        Return True when the settings allow this notification to be shown.

        notifications_enabled switches every notification off. The five
        show_*_notifications fields switch off one level each. Both were
        declared and read by nothing.
        """
        settings = self._settings_model
        if settings is None:
            return True

        if not settings.notifications_enabled:
            return False

        allowed = settings.get_enabled_notification_levels()
        return notification.level.name in allowed

    def _on_service_notification_removed(self, notification_id: str):
        """Handle notification removal from service"""
        if self._notification_list:
            self._notification_list.remove_notification(notification_id)

    def _on_service_notifications_cleared(self, level_filter: Optional[NotificationLevel] = None):
        """Handle notifications cleared from service"""
        if self._notification_list:
            # If a filter is applied, we might need to handle it selectively
            # For now, if no filter or if filter matches, we reload or clear
            if level_filter is None:
                self._notification_list.clear()
            else:
                # If specific level cleared, might need to iterate and check
                # For simplicity in this fix, we'll just clear all if the intention was to clear
                # But to be precise, we should probably re-sync with service or iterate items
                # Given SimplifiedNotificationList structure, 'clear' removes all widgets.
                # If we only cleared some, we should probably just remove those.
                # Since SimplifiedNotificationList doesn't store level easily accessible without object inspection,
                # let's just clear all for now as 'Clear All' button passes None.
                # If we needed to support partial clear, we'd need to improve SimplifiedNotificationList
                self._notification_list.clear()
                
                # Reload remaining notifications
                service = ServiceLocator.get_service("notification")
                if service and isinstance(service, NotificationService):
                    notifications = service.get_notifications()
                    for notification in notifications:
                        self._notification_list.add_notification(notification)

    def _show_toast(self, notification: Notification) -> None:
        """Show one toast and keep the stack inside the visible limit."""
        if not self._main_window:
            return

        self._drop_oldest_toasts()

        toast = ToastWidget(notification, self._main_window)
        self._apply_toast_lifetime(toast)
        toast.closed.connect(self._on_toast_closed)
        self._active_toasts.append(toast)
        toast.show()
        self._reposition_toasts()

    def _apply_toast_lifetime(self, toast: ToastWidget) -> None:
        """
        Replace the per level toast lifetime when the user asked for one.

        ToastWidget picks its duration from the notification level. The two
        auto_hide settings were declared and read by nothing.

        A toast whose timer is not running has no duration at all, which is
        how a critical notification stays on screen until the user dismisses
        it. That toast is left alone: an auto-hide timeout must not take away
        the one notification the user must see.
        """
        settings = self._settings_model
        if settings is None or not settings.auto_hide_notifications:
            return

        if not toast.close_timer.isActive():
            return

        timeout = int(settings.auto_hide_timeout)
        if timeout > 0:
            toast.close_timer.start(timeout)

    def _drop_oldest_toasts(self) -> None:
        """
        Remove the oldest toasts so that one more toast still fits.

        More than MAX_VISIBLE_TOASTS toasts at the same time cannot be read
        before they expire, and they hide the window behind them.
        """
        for _ in range(overflow_count(len(self._active_toasts),
                                      MAX_VISIBLE_TOASTS)):
            oldest = self._active_toasts.pop(0)
            oldest.hide()
            oldest.deleteLater()

    def _on_toast_closed(self, notification_id: str) -> None:
        """Drop a toast that has finished its fade out, then close the gap."""
        for toast in self._active_toasts[:]:
            if toast.notification.id == notification_id:
                self._active_toasts.remove(toast)
                toast.deleteLater()
        self._reposition_toasts()

    def _reposition_toasts(self) -> None:
        """
        Place the toast stack in the bottom right corner of the main window.

        A toast is a top level window, so move() takes global screen
        coordinates. The width and the height of the main window are widget
        local lengths and must never be used as coordinates here.
        """
        if not self._main_window:
            return

        newest_first = list(reversed(self._active_toasts))
        for toast in newest_first:
            toast.adjustSize()

        sizes = [toast.size() for toast in newest_first]
        positions = stacked_toast_positions(
            toast_anchor(self._main_window), sizes)
        for toast, position in zip(newest_first, positions):
            toast.move(position)

    # Model event handlers
    def _on_notifications_changed(self) -> None:
        """Handle notifications changed in model"""
        # Logic moved to _on_service_notification_added mostly
        pass

    def _on_notification_count_changed(self, count: int) -> None:
        """Handle notification count changed"""
        # Could be used to update main window title bar or status
        pass

    def _on_log_entry_added(self, level: str, message: str, source: str, timestamp: str) -> None:
        """Handle log entry added from logger model"""
        # Log entries are automatically forwarded to notifications by the logger service
        pass

    def _on_logger_configuration_changed(self) -> None:
        """Handle logger configuration changed"""
        pass

    # Public API for other presenters/components
    def show_notifications(self) -> None:
        """Show the notification widget"""
        if self._dock_widget:
            self._dock_widget.show()
            self._dock_widget.raise_()

    def hide_notifications(self) -> None:
        """Hide the notification widget"""
        if self._dock_widget:
            self._dock_widget.hide()

    def toggle_notifications(self) -> None:
        """Toggle notification widget visibility"""
        if self._dock_widget:
            if self._dock_widget.isVisible():
                self.hide_notifications()
            else:
                self.show_notifications()

    def add_notification(
        self,
        level: NotificationLevel,
        title: str,
        message: str,
        source: str = "System",
        persistent: bool = False
    ) -> str:
        """
        Add a new notification through the model.

        Args:
            level: Notification level
            title: Notification title
            message: Notification message
            source: Source component
            persistent: Whether notification is persistent

        Returns:
            Notification ID
        """
        if self._notification_model:
            return self._notification_model.add_notification(level, title, message, source, persistent)
        return ""

    def log_debug(self, message: str, source: str = "System", notify: bool = False) -> None:
        """Log a debug message"""
        if self._logger_model:
            self._logger_model.debug(message, source, notify)

    def log_info(self, message: str, source: str = "System", notify: bool = False) -> None:
        """Log an info message"""
        if self._logger_model:
            self._logger_model.info(message, source, notify)

    def log_warning(self, message: str, source: str = "System", notify: bool = True) -> None:
        """Log a warning message"""
        if self._logger_model:
            self._logger_model.warning(message, source, notify)

    def log_error(self, message: str, source: str = "System", notify: bool = True) -> None:
        """Log an error message"""
        if self._logger_model:
            self._logger_model.error(message, source, notify)

    def log_critical(self, message: str, source: str = "System", notify: bool = True) -> None:
        """Log a critical message"""
        if self._logger_model:
            self._logger_model.critical(message, source, notify)

    # Configuration methods
    def get_notification_widget(self) -> Optional[QDockWidget]:
        """Get the notification widget instance"""
        return self._dock_widget

    def get_notification_model(self) -> Optional[NotificationModel]:
        """Get the notification model instance"""
        return self._notification_model

    def get_logger_model(self) -> Optional[LoggerModel]:
        """Get the logger model instance"""
        return self._logger_model

    def settings_page(self) -> Optional[NotificationSettingsPage]:
        """
        Return the settings dialog page for the notification settings.

        None only when the models failed to build, which _setup_models logs.
        """
        return self._settings_page

    def apply_settings(self) -> None:
        """
        Apply every notification setting to the running interface.

        Called by the settings dialog through NotificationSettingsPage, and by
        BaseApplication when SettingsService reports a change from anywhere
        else. Task 7, Task 8 and Task 9 of this plan fill it in.
        """

    def set_log_level(self, level: str) -> None:
        """Set logging level"""
        if self._logger_model:
            self._logger_model.set_log_level(level)

    def set_console_logging(self, enabled: bool) -> None:
        """Enable/disable console logging"""
        if self._logger_model:
            self._logger_model.set_console_logging(enabled)

    def set_file_logging(self, enabled: bool) -> None:
        """Enable/disable file logging"""
        if self._logger_model:
            self._logger_model.set_file_logging(enabled)

    def set_notification_on_error(self, enabled: bool) -> None:
        """Enable/disable notifications for error logs"""
        if self._logger_model:
            self._logger_model.set_notification_on_error(enabled)

    def set_notification_on_critical(self, enabled: bool) -> None:
        """Enable/disable notifications for critical logs"""
        if self._logger_model:
            self._logger_model.set_notification_on_critical(enabled)

    def get_logger_configuration(self) -> Dict[str, Any]:
        """Get current logger configuration"""
        if self._logger_model:
            return self._logger_model.get_configuration()
        return {}

    def clear_notifications(self, level_filter: Optional[NotificationLevel] = None) -> None:
        """Clear notifications"""
        if self._notification_model:
            self._notification_model.clear_notifications(level_filter)

    def clear_log_entries(self) -> None:
        """Clear in-memory log entries"""
        if self._logger_model:
            self._logger_model.clear_log_entries()

    # Convenience methods for common notification types
    def notify_info(self, title: str, message: str, source: str = "System") -> str:
        """Add an info notification"""
        return self.add_notification(NotificationLevel.INFO, title, message, source)

    def notify_warning(self, title: str, message: str, source: str = "System") -> str:
        """Add a warning notification"""
        return self.add_notification(NotificationLevel.WARNING, title, message, source)

    def notify_error(self, title: str, message: str, source: str = "System") -> str:
        """Add an error notification"""
        return self.add_notification(NotificationLevel.ERROR, title, message, source)

    def notify_critical(self, title: str, message: str, source: str = "System") -> str:
        """Add a critical notification (persistent)"""
        return self.add_notification(NotificationLevel.CRITICAL, title, message, source, persistent=True)

    def cleanup(self) -> None:
        """Clean up resources"""
        try:
            if self._dock_widget:
                self._dock_widget.setParent(None)
                self._dock_widget = None
            self._notification_list = None

            if self._notification_model:
                self._notification_model = None

            if self._logger_model:
                self._logger_model = None

        except Exception:
            logger.exception("Failed to clean up the notification presenter")

    def initialize(self) -> None:
        """
        Initialize the notification system.

        Nothing is shown to the user here. A start up toast that reports that
        the notification system started tells the user nothing, and it covers
        the corner of the window before the user has done anything.
        """
        try:
            self.log_info("Notification system initialized",
                          "NotificationPresenter")
        except Exception:
            logger.exception("Failed to initialize the notification system")
            # Still continue - don't let this crash the application
