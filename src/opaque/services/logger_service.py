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
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, TYPE_CHECKING
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import Signal

from opaque.services.service import BaseService, ServiceLocator

if TYPE_CHECKING:
    from opaque.services.notification_service import NotificationService


class LoggerService(BaseService):
    """
    Enhanced logging service that provides file-based logging with rotation,
    console output, and integration with the notification system.
    """

    # Signals
    # level, message, source, timestamp
    log_entry_added = Signal(str, str, str, str)

    # Log level mapping
    LEVEL_MAPPING = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    def __init__(self, log_directory: Optional[str] = None, application_name: Optional[str] = None):
        super().__init__("logger")
        self._log_directory = log_directory or "logs"
        self._application_name = application_name or "application"
        self._logger: Optional[logging.Logger] = None
        self._file_handler: Optional[RotatingFileHandler] = None
        self._console_handler: Optional[logging.StreamHandler[Any]] = None

        # Generate timestamp for this session
        self._session_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._session_folder: Optional[Path] = None
        self._session_log_file: Optional[Path] = None

        # Configuration
        self._log_level = logging.INFO
        self._max_file_size = 10 * 1024 * 1024  # 10MB
        self._backup_count = 5
        self._console_logging_enabled = True
        self._file_logging_enabled = True
        self._notify_on_error = True
        self._notify_on_critical = True

    def initialize(self) -> None:
        """Initialize the logging service"""
        super().initialize()
        self._setup_logger()

    def cleanup(self) -> None:
        """Clean up logging resources"""
        if self._logger:
            # Remove all handlers
            for handler in self._logger.handlers[:]:
                handler.close()
                self._logger.removeHandler(handler)
        super().cleanup()

    def _setup_logger(self) -> None:
        """Set up the logger with file and console handlers"""
        # Create the main logger
        self._logger = logging.getLogger("opaque_app")
        self._logger.setLevel(self._log_level)

        # Clear any existing handlers
        self._logger.handlers.clear()

        # Set up file logging
        if self._file_logging_enabled:
            self._setup_file_logging()

        # Set up console logging
        if self._console_logging_enabled:
            self._setup_console_logging()

    def _setup_file_logging(self) -> None:
        """Set up rotating file handler with timestamped folder structure"""
        try:
            # Ensure base log directory exists
            base_log_dir = Path(self._log_directory)
            base_log_dir.mkdir(parents=True, exist_ok=True)

            # Create session folder name: application_name_YYYYMMDD_HHMMSS
            session_folder_name = f"{self._application_name}_{self._session_timestamp}"
            self._session_folder = base_log_dir / session_folder_name
            self._session_folder.mkdir(parents=True, exist_ok=True)

            # Create log file name: application_name_YYYYMMDD_HHMMSS.log
            log_file_name = f"{self._application_name}_{self._session_timestamp}.log"
            self._session_log_file = self._session_folder / log_file_name

            # Create rotating file handler
            self._file_handler = RotatingFileHandler(
                filename=str(self._session_log_file),
                maxBytes=self._max_file_size,
                backupCount=self._backup_count,
                encoding='utf-8'
            )

            # Set format for file logging
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            self._file_handler.setFormatter(file_formatter)
            self._file_handler.setLevel(self._log_level)

            # Add to logger
            if self._logger:
                self._logger.addHandler(self._file_handler)

        except Exception as e:
            print(f"Failed to set up file logging: {e}")

    def _setup_console_logging(self) -> None:
        """Set up console handler"""
        try:
            self._console_handler = logging.StreamHandler()

            # Set format for console logging
            console_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            self._console_handler.setFormatter(console_formatter)
            self._console_handler.setLevel(self._log_level)

            # Add to logger
            if self._logger:
                self._logger.addHandler(self._console_handler)

        except Exception as e:
            print(f"Failed to set up console logging: {e}")

    def log(self, level: str, message: str, source: str = "System", notify: Optional[bool] = None) -> None:
        """
        Log a message with the specified level.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Message to log
            source: Source component generating the log
            notify: If True, also send to notification service (auto-determined if None)
        """
        if not self._logger:
            return

        level_upper = level.upper()
        log_level = self.LEVEL_MAPPING.get(level_upper, logging.INFO)

        # Log the message
        self._logger.log(log_level, f"[{source}] {message}")

        # Emit signal for any listeners
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_entry_added.emit(level_upper, message, source, timestamp)

        # Send to notification service if appropriate
        should_notify = notify
        if should_notify is None:
            # Auto-determine based on configuration and level
            should_notify = (
                (level_upper == 'ERROR' and self._notify_on_error) or
                (level_upper == 'CRITICAL' and self._notify_on_critical)
            )

        if should_notify:
            self._send_to_notification_service(level_upper, message, source)

    def _send_to_notification_service(self, level: str, message: str, source: str) -> None:
        """Send log message to notification service if available"""
        try:
            notification_service = ServiceLocator.get_service("notification")
            if notification_service and hasattr(notification_service, 'add_notification'):
                from opaque.services.notification_service import NotificationLevel

                # Map log level to notification level
                level_mapping = {
                    'DEBUG': NotificationLevel.DEBUG,
                    'INFO': NotificationLevel.INFO,
                    'WARNING': NotificationLevel.WARNING,
                    'ERROR': NotificationLevel.ERROR,
                    'CRITICAL': NotificationLevel.CRITICAL
                }

                notif_level = level_mapping.get(level, NotificationLevel.INFO)
                title = f"{level} from {source}"

                # Make critical notifications persistent
                persistent = (level == 'CRITICAL')

                # Cast to the proper type for the method call
                from typing import cast
                notif_service = cast('NotificationService',
                                     notification_service)
                notif_service.add_notification(
                    level=notif_level,
                    title=title,
                    message=message,
                    source=source,
                    persistent=persistent
                )
        except Exception as e:
            # Don't let notification errors break logging
            print(f"Failed to send notification: {e}")

    def debug(self, message: str, source: str = "System", notify: bool = False) -> None:
        """Log a debug message"""
        self.log("DEBUG", message, source, notify)

    def info(self, message: str, source: str = "System", notify: bool = False) -> None:
        """Log an info message"""
        self.log("INFO", message, source, notify)

    def warning(self, message: str, source: str = "System", notify: bool = True) -> None:
        """Log a warning message"""
        self.log("WARNING", message, source, notify)

    def error(self, message: str, source: str = "System", notify: bool = True) -> None:
        """Log an error message"""
        self.log("ERROR", message, source, notify)

    def critical(self, message: str, source: str = "System", notify: bool = True) -> None:
        """Log a critical message"""
        self.log("CRITICAL", message, source, notify)

    def exception(self, message: str, source: str = "System", notify: bool = True) -> None:
        """Log an exception with traceback"""
        if self._logger:
            self._logger.exception(f"[{source}] {message}")

            # Also send as error to notification service
            if notify:
                self._send_to_notification_service(
                    "ERROR", f"Exception: {message}", source)

    # Configuration methods
    def set_log_level(self, level: str) -> None:
        """
        Set the logging level.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        log_level = self.LEVEL_MAPPING.get(level.upper(), logging.INFO)
        self._log_level = log_level

        if self._logger:
            self._logger.setLevel(log_level)

        if self._file_handler:
            self._file_handler.setLevel(log_level)

        if self._console_handler:
            self._console_handler.setLevel(log_level)

    def set_console_logging(self, enabled: bool) -> None:
        """Enable or disable console logging"""
        self._console_logging_enabled = enabled

        if self._logger and self._console_handler:
            if not enabled:
                self._logger.removeHandler(self._console_handler)
                self._console_handler = None
            elif enabled and not self._console_handler:
                self._setup_console_logging()

    def set_file_logging(self, enabled: bool) -> None:
        """Enable or disable file logging"""
        self._file_logging_enabled = enabled

        if self._logger and self._file_handler:
            if not enabled:
                self._logger.removeHandler(self._file_handler)
                self._file_handler.close()
                self._file_handler = None
            elif enabled and not self._file_handler:
                self._setup_file_logging()

    def set_notification_on_error(self, enabled: bool) -> None:
        """Enable or disable notifications for error messages"""
        self._notify_on_error = enabled

    def set_notification_on_critical(self, enabled: bool) -> None:
        """Enable or disable notifications for critical messages"""
        self._notify_on_critical = enabled

    def get_log_file_path(self) -> Optional[str]:
        """Get the path to the current log file"""
        if self._session_log_file:
            return str(self._session_log_file)
        elif self._file_handler:
            return self._file_handler.baseFilename
        return None

    def get_session_folder_path(self) -> Optional[str]:
        """Get the path to the current session folder"""
        if self._session_folder:
            return str(self._session_folder)
        return None

    def get_session_timestamp(self) -> str:
        """Get the timestamp for the current session"""
        return self._session_timestamp

    def get_application_name(self) -> str:
        """Get the application name used for logging"""
        return self._application_name

    def get_configuration(self) -> Dict[str, Any]:
        """Get current logger configuration"""
        return {
            'log_level': logging.getLevelName(self._log_level),
            'log_directory': self._log_directory,
            'application_name': self._application_name,
            'session_timestamp': self._session_timestamp,
            'max_file_size': self._max_file_size,
            'backup_count': self._backup_count,
            'console_logging_enabled': self._console_logging_enabled,
            'file_logging_enabled': self._file_logging_enabled,
            'notify_on_error': self._notify_on_error,
            'notify_on_critical': self._notify_on_critical,
            'log_file_path': self.get_log_file_path(),
            'session_folder_path': self.get_session_folder_path()
        }
