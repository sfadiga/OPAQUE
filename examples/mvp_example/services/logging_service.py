"""
Example Logging Service
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from opaque.core.services import BaseService
from datetime import datetime


class LoggingService(BaseService):
    """Service that provides logging functionality to features."""

    def __init__(self):
        super().__init__("LoggingService")
        self._logs = []

    def initialize(self, **kwargs):
        """Initialize the logging service."""
        super().initialize(**kwargs)
        self.log("info", "Logging service initialized")

    def log(self, level: str, message: str) -> None:
        """
        Log a message with a given level.

        Args:
            level: Log level (info, warning, error, debug)
            message: Message to log
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            'timestamp': timestamp,
            'level': level.upper(),
            'message': message
        }
        self._logs.append(log_entry)

        # Also print to console
        print(f"[{timestamp}] {level.upper()}: {message}")

    def get_logs(self, level: str = None) -> list:
        """
        Get all logs or logs of a specific level.

        Args:
            level: Optional level filter

        Returns:
            List of log entries
        """
        if level:
            return [log for log in self._logs if log['level'] == level.upper()]
        return self._logs.copy()

    def clear_logs(self) -> None:
        """Clear all logs."""
        self._logs.clear()

    def get_info(self) -> dict:
        """Get service information."""
        info = super().get_info()
        info['log_count'] = len(self._logs)
        return info
