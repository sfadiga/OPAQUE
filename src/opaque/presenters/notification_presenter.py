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

from typing import Optional, Dict, Any, List

from PySide6.QtCore import QObject, Qt, QPoint, QTimer
from PySide6.QtWidgets import QMainWindow, QDockWidget

from opaque.models.notification_model import NotificationModel
from opaque.models.notification_settings_model import NotificationSettingsModel
from opaque.models.logger_model import LoggerModel
from opaque.view.widgets.notification_widget import SimplifiedNotificationList, ToastWidget
from opaque.services.notification_service import NotificationLevel, Notification, NotificationService
from opaque.services.service import ServiceLocator


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
            
            # Register settings model
            settings_service = ServiceLocator.get_service("settings")
            if settings_service:
                 # settings_service.register_model("notification_settings", self._settings_model)
                 pass # Assuming registration happens elsewhere or manual loading

        except Exception as e:
            print(f"Failed to setup notification models: {e}")

    def _setup_views(self) -> None:
        """Initialize the views"""
        try:
            # Create simplified list widget
            self._notification_list = SimplifiedNotificationList(self._main_window)
            
            # Wrap in a dock widget for layout compatibility
            self._dock_widget = QDockWidget("Notifications", self._main_window)
            self._dock_widget.setWidget(self._notification_list)
            self._dock_widget.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)

            # Add to main window as dock widget if available
            if self._main_window:
                self._main_window.addDockWidget(
                    Qt.DockWidgetArea.BottomDockWidgetArea,
                    self._dock_widget
                )

        except Exception as e:
            print(f"Failed to setup notification views: {e}")

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

        except Exception as e:
            print(f"Failed to connect notification signals: {e}")

    def _on_service_notification_added(self, notification: Notification):
        # Add to list
        if self._notification_list:
            self._notification_list.add_notification(notification)
            
        # Show Toast if enabled
        if self._settings_model and self._settings_model.enable_toasts:
            self._show_toast(notification)

    def _show_toast(self, notification: Notification):
        if not self._main_window:
            return

        toast = ToastWidget(notification, self._main_window)
        toast.closed.connect(self._on_toast_closed)
        
        # Position logic (bottom right stack)
        self._active_toasts.append(toast)
        self._reposition_toasts()
        
        toast.show()

    def _on_toast_closed(self, notification_id: str):
        # Find and remove toast
        for toast in self._active_toasts[:]:
            if toast.notification.id == notification_id:
                self._active_toasts.remove(toast)
                toast.deleteLater()
        self._reposition_toasts()

    def _reposition_toasts(self):
        if not self._main_window: return
        
        margin = 10
        spacing = 5
        x = self._main_window.width() - margin
        y = self._main_window.height() - margin
        
        for toast in reversed(self._active_toasts):
            width = toast.sizeHint().width()
            height = toast.sizeHint().height()
            
            # Ensure proper size
            toast.adjustSize()
            width = toast.width()
            height = toast.height()
            
            toast.move(x - width, y - height)
            y -= (height + spacing)

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

        except Exception as e:
            print(f"Error during notification presenter cleanup: {e}")

    def initialize(self) -> None:
        """Initialize the notification system"""
        try:
            # Log system initialization
            self.log_info("Notification system initialized",
                          "NotificationPresenter")

            # Add welcome notification
            self.notify_info(
                "System Ready",
                "Notification and logging system is now active",
                "System"
            )
        except Exception as e:
            print(f"Failed to initialize notification system: {e}")
            # Still continue - don't let this crash the application
