"""
Notification Tester Presenter
"""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from opaque.view.application import BaseApplication

from PySide6.QtCore import QTimer

from opaque.presenters.presenter import BasePresenter
from opaque.services.notification_service import NotificationLevel
from .model import NotificationTesterModel
from .view import NotificationTesterView


class NotificationTesterPresenter(BasePresenter):
    """Presenter for the notification tester feature."""
    model_class = NotificationTesterModel
    view_class = NotificationTesterView

    def __init__(self, model: NotificationTesterModel, view: NotificationTesterView, app: 'BaseApplication'):
        super().__init__(model, view, app)
        self.demo_timer = None
        self.demo_step = 0

    def bind_events(self):
        """Bind view events to presenter methods."""
        self.view.send_notification_clicked.connect(self._on_send_notification)
        self.view.send_log_clicked.connect(self._on_send_log)
        self.view.run_demo_clicked.connect(self._on_run_demo)
        self.view.toggle_panel_clicked.connect(self._on_toggle_panel)
        self.view.clear_notifications_clicked.connect(self._on_clear_notifications)
        self.view.level_changed.connect(self._on_level_changed)

    def update(self, field_name: str, new_value, old_value=None, model=None):
        """Handle model property changes."""
        if field_name == "status_message":
            self.view.update_status(new_value)
        elif field_name == "selected_level":
            self.view.set_selected_level(new_value)

    def on_view_show(self):
        """Called when view is shown."""
        self.view.set_selected_level(self.model.selected_level)
        self.view.update_status(self.model.status_message)

    def on_view_close(self):
        """Called when view is closed."""
        if self.demo_timer:
            self.demo_timer.stop()

    def _on_level_changed(self, level: str):
        self.model.selected_level = level

    def _on_send_notification(self):
        """Send a test notification"""
        try:
            level_text = self.model.selected_level
            level = getattr(NotificationLevel, level_text)
            
            notification_id = self.app.notification_presenter.add_notification(
                level=level,
                title=f"Test {level_text} Notification",
                message=f"This is a test {level_text.lower()} notification message.",
                source="NotificationTester",
                persistent=(level_text in ["ERROR", "CRITICAL"])
            )
            
            self.model.status_message = f"Sent {level_text} notification (ID: {notification_id})"
            
        except Exception as e:
            self.model.status_message = f"Error sending notification: {e}"

    def _on_send_log(self):
        """Send a test log message"""
        try:
            level_text = self.model.selected_level.lower()
            message = f"Test {level_text} log message from NotificationTester"
            
            # Call the appropriate log method on notification presenter (which proxies to logger service/model)
            # NotificationPresenter has log_debug, log_info, etc.
            log_method = getattr(self.app.notification_presenter, f"log_{level_text}")
            log_method(message, "NotificationTester", notify=(level_text in ["warning", "error", "critical"]))
            
            self.model.status_message = f"Logged {level_text} message"
            
        except Exception as e:
            self.model.status_message = f"Error logging message: {e}"

    def _on_run_demo(self):
        """Run a demonstration sequence of notifications"""
        try:
            # Create a timer to send notifications in sequence
            self.demo_timer = QTimer()
            self.demo_step = 0
            self.demo_timer.timeout.connect(self._demo_next_step)
            self.demo_timer.start(2000)  # 2 second intervals
            
            self.model.status_message = "Running demo sequence..."
            
        except Exception as e:
            self.model.status_message = f"Error running demo: {e}"

    def _demo_next_step(self):
        """Execute the next step in the demo sequence"""
        try:
            if self.demo_step == 0:
                self.app.notification_presenter.notify_info(
                    "Demo Started", "Beginning notification system demonstration", "Demo"
                )
            elif self.demo_step == 1:
                self.app.notification_presenter.log_info(
                    "Demo step 1: Info logging", "Demo"
                )
            elif self.demo_step == 2:
                self.app.notification_presenter.notify_warning(
                    "Demo Warning", "This is a warning notification", "Demo"
                )
            elif self.demo_step == 3:
                self.app.notification_presenter.log_error(
                    "Demo error log (this will create a notification)", "Demo", notify=True
                )
            elif self.demo_step == 4:
                self.app.notification_presenter.notify_info(
                    "Demo Complete", "Notification system demonstration finished", "Demo"
                )
                self.demo_timer.stop()
                self.model.status_message = "Demo sequence completed!"
                return
            
            self.demo_step += 1
            
        except Exception as e:
            if self.demo_timer:
                self.demo_timer.stop()
            self.model.status_message = f"Demo error: {e}"

    def _on_toggle_panel(self):
        """Toggle the notifications panel visibility"""
        try:
            self.app.notification_presenter.toggle_notifications()
            self.model.status_message = "Toggled notifications panel"
        except Exception as e:
            self.model.status_message = f"Error toggling notifications: {e}"

    def _on_clear_notifications(self):
        """Clear all notifications"""
        try:
            self.app.notification_presenter.clear_notifications()
            self.model.status_message = "Cleared all notifications"
        except Exception as e:
            self.model.status_message = f"Error clearing notifications: {e}"

    def cleanup(self):
        if self.demo_timer:
            self.demo_timer.stop()
        super().cleanup()
