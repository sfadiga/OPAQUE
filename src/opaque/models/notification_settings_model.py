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

from opaque.models.abstract_model import AbstractModel
from opaque.models.annotations import BoolField, StringField, IntField, ChoiceField


class NotificationSettingsModel(AbstractModel):
    """
    Model for notification system settings and preferences.
    """

    # General notification settings
    notifications_enabled = BoolField(
        default=True,
        description="Enable/disable all notifications"
    )

    enable_toasts = BoolField(
        default=True,
        description="Enable transient toast notifications"
    )

    show_notification_count = BoolField(
        default=True,
        description="Show notification count in the widget"
    )

    auto_hide_notifications = BoolField(
        default=False,
        description="Automatically hide non-persistent notifications after timeout"
    )

    auto_hide_timeout = IntField(
        default=5000,
        description="Auto-hide timeout in milliseconds (5 seconds default)"
    )

    # Notification level filters
    show_debug_notifications = BoolField(
        default=False,
        description="Show DEBUG level notifications"
    )

    show_info_notifications = BoolField(
        default=True,
        description="Show INFO level notifications"
    )

    show_warning_notifications = BoolField(
        default=True,
        description="Show WARNING level notifications"
    )

    show_error_notifications = BoolField(
        default=True,
        description="Show ERROR level notifications"
    )

    show_critical_notifications = BoolField(
        default=True,
        description="Show CRITICAL level notifications"
    )

    # Logger integration settings
    log_level = ChoiceField(
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        description="Minimum logging level"
    )

    console_logging_enabled = BoolField(
        default=True,
        description="Enable console logging output"
    )

    file_logging_enabled = BoolField(
        default=True,
        description="Enable file logging output"
    )

    log_file_path = StringField(
        default="",
        description="Custom log file path (empty for default)"
    )

    notification_on_warning = BoolField(
        default=False,
        description="Create notifications for WARNING log messages"
    )

    notification_on_error = BoolField(
        default=True,
        description="Create notifications for ERROR log messages"
    )

    notification_on_critical = BoolField(
        default=True,
        description="Create notifications for CRITICAL log messages"
    )

    # Widget appearance settings
    notification_widget_position = ChoiceField(
        default="Right",
        choices=["Left", "Right", "Top", "Bottom"],
        description="Default docking position for notification widget"
    )

    max_notification_display = IntField(
        default=100,
        description="Maximum number of notifications to display in widget"
    )

    notification_widget_width = IntField(
        default=300,
        description="Default width of notification widget"
    )

    notification_widget_height = IntField(
        default=400,
        description="Default height of notification widget"
    )

    def __init__(self):
        super().__init__()

    def feature_name(self) -> str:
        """Return the feature name for this settings model"""
        return "Notification System"

    def get_enabled_notification_levels(self) -> list[str]:
        """Get list of enabled notification levels based on settings"""
        enabled_levels = []

        if self.show_debug_notifications:
            enabled_levels.append("DEBUG")
        if self.show_info_notifications:
            enabled_levels.append("INFO")
        if self.show_warning_notifications:
            enabled_levels.append("WARNING")
        if self.show_error_notifications:
            enabled_levels.append("ERROR")
        if self.show_critical_notifications:
            enabled_levels.append("CRITICAL")

        return enabled_levels

    def should_create_notification_for_log_level(self, level: str) -> bool:
        """Check if notifications should be created for the given log level"""
        level = level.upper()

        if level == "WARNING":
            return self.notification_on_warning
        elif level == "ERROR":
            return self.notification_on_error
        elif level == "CRITICAL":
            return self.notification_on_critical

        return False

    def get_logger_configuration(self) -> dict:
        """Get logger configuration based on settings"""
        return {
            "level": str(self.log_level),
            "console_enabled": bool(self.console_logging_enabled),
            "file_enabled": bool(self.file_logging_enabled),
            "file_path": str(self.log_file_path) if self.log_file_path else None,
            "notification_on_warning": bool(self.notification_on_warning),
            "notification_on_error": bool(self.notification_on_error),
            "notification_on_critical": bool(self.notification_on_critical),
        }

    def get_widget_configuration(self) -> dict:
        """Get notification widget configuration based on settings"""
        return {
            "enabled": bool(self.notifications_enabled),
            "show_count": bool(self.show_notification_count),
            "auto_hide": bool(self.auto_hide_notifications),
            "auto_hide_timeout": int(self.auto_hide_timeout),
            "position": str(self.notification_widget_position),
            "max_display": int(self.max_notification_display),
            "width": int(self.notification_widget_width),
            "height": int(self.notification_widget_height),
            "enabled_levels": self.get_enabled_notification_levels(),
        }
