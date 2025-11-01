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
from opaque.services.logger_service import LoggerService


class LogEntry:
    """Represents a single log entry"""
    
    def __init__(self, level: str, message: str, source: str, timestamp: str):
        self.level = level
        self.message = message
        self.source = source
        self.timestamp = timestamp


class LoggerModel(QObject):
    """
    Model for managing logger data and business logic.
    Provides an interface between the logger service and the UI.
    """

    # Signals
    log_entry_added = Signal(str, str, str, str)  # level, message, source, timestamp
    configuration_changed = Signal()
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._logger_service: Optional[LoggerService] = None
        self._log_entries: List[LogEntry] = []
        self._max_entries = 1000  # Limit in-memory log entries
        self._connected = False
        
        # Don't connect immediately - will be done during initialize()

    def _connect_to_logger_service(self) -> None:
        """Connect to the logger service"""
        self._logger_service = ServiceLocator.get_service("logger")
        if self._logger_service and hasattr(self._logger_service, 'log_entry_added'):
            self._logger_service.log_entry_added.connect(self._on_log_entry_added)

    def _on_log_entry_added(self, level: str, message: str, source: str, timestamp: str) -> None:
        """Handle log entry added from service"""
        # Add to internal list
        entry = LogEntry(level, message, source, timestamp)
        self._log_entries.append(entry)
        
        # Maintain size limit
        if len(self._log_entries) > self._max_entries:
            self._log_entries = self._log_entries[-self._max_entries:]
        
        # Emit signal
        self.log_entry_added.emit(level, message, source, timestamp)

    def get_log_entries(
        self, 
        level_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[LogEntry]:
        """
        Get log entries based on filters.
        
        Args:
            level_filter: Filter by log level
            source_filter: Filter by source
            limit: Maximum number of entries to return
            
        Returns:
            List of log entries
        """
        entries = self._log_entries.copy()
        
        # Apply filters
        if level_filter:
            entries = [e for e in entries if e.level == level_filter]
        
        if source_filter:
            entries = [e for e in entries if e.source == source_filter]
        
        # Apply limit (return most recent entries)
        if limit and len(entries) > limit:
            entries = entries[-limit:]
        
        return entries

    def clear_log_entries(self) -> None:
        """Clear all in-memory log entries"""
        self._log_entries.clear()

    # Logging methods
    def debug(self, message: str, source: str = "System", notify: bool = False) -> None:
        """Log a debug message"""
        if self._logger_service:
            from typing import cast
            service = cast(LoggerService, self._logger_service)
            service.debug(message, source, notify)

    def info(self, message: str, source: str = "System", notify: bool = False) -> None:
        """Log an info message"""
        if self._logger_service:
            from typing import cast
            service = cast(LoggerService, self._logger_service)
            service.info(message, source, notify)

    def warning(self, message: str, source: str = "System", notify: bool = True) -> None:
        """Log a warning message"""
        if self._logger_service:
            from typing import cast
            service = cast(LoggerService, self._logger_service)
            service.warning(message, source, notify)

    def error(self, message: str, source: str = "System", notify: bool = True) -> None:
        """Log an error message"""
        if self._logger_service:
            from typing import cast
            service = cast(LoggerService, self._logger_service)
            service.error(message, source, notify)

    def critical(self, message: str, source: str = "System", notify: bool = True) -> None:
        """Log a critical message"""
        if self._logger_service:
            from typing import cast
            service = cast(LoggerService, self._logger_service)
            service.critical(message, source, notify)

    def exception(self, message: str, source: str = "System", notify: bool = True) -> None:
        """Log an exception with traceback"""
        if self._logger_service:
            from typing import cast
            service = cast(LoggerService, self._logger_service)
            service.exception(message, source, notify)

    # Configuration methods
    def set_log_level(self, level: str) -> None:
        """
        Set the logging level.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if self._logger_service:
            from typing import cast
            service = cast(LoggerService, self._logger_service)
            service.set_log_level(level)
            self.configuration_changed.emit()

    def set_console_logging(self, enabled: bool) -> None:
        """Enable or disable console logging"""
        if self._logger_service:
            from typing import cast
            service = cast(LoggerService, self._logger_service)
            service.set_console_logging(enabled)
            self.configuration_changed.emit()

    def set_file_logging(self, enabled: bool) -> None:
        """Enable or disable file logging"""
        if self._logger_service:
            from typing import cast
            service = cast(LoggerService, self._logger_service)
            service.set_file_logging(enabled)
            self.configuration_changed.emit()

    def set_notification_on_error(self, enabled: bool) -> None:
        """Enable or disable notifications for error messages"""
        if self._logger_service:
            from typing import cast
            service = cast(LoggerService, self._logger_service)
            service.set_notification_on_error(enabled)
            self.configuration_changed.emit()

    def set_notification_on_critical(self, enabled: bool) -> None:
        """Enable or disable notifications for critical messages"""
        if self._logger_service:
            from typing import cast
            service = cast(LoggerService, self._logger_service)
            service.set_notification_on_critical(enabled)
            self.configuration_changed.emit()

    def get_log_file_path(self) -> Optional[str]:
        """Get the path to the current log file"""
        if self._logger_service:
            from typing import cast
            service = cast(LoggerService, self._logger_service)
            return service.get_log_file_path()
        return None

    def get_configuration(self) -> Dict[str, Any]:
        """Get current logger configuration"""
        if self._logger_service:
            from typing import cast
            service = cast(LoggerService, self._logger_service)
            return service.get_configuration()
        return {}

    def get_available_log_levels(self) -> List[str]:
        """Get list of available log levels"""
        return ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def get_unique_sources(self) -> List[str]:
        """Get list of unique sources from log entries"""
        sources = set()
        for entry in self._log_entries:
            sources.add(entry.source)
        return sorted(list(sources))

    def set_max_entries(self, max_entries: int) -> None:
        """
        Set maximum number of in-memory log entries.
        
        Args:
            max_entries: Maximum number of entries to keep
        """
        self._max_entries = max_entries
        
        # Trim current entries if needed
        if len(self._log_entries) > max_entries:
            self._log_entries = self._log_entries[-max_entries:]

    def get_max_entries(self) -> int:
        """Get maximum number of in-memory log entries"""
        return self._max_entries

    def initialize(self) -> None:
        """Initialize the model after services are ready"""
        if not self._connected:
            self._connect_to_logger_service()
            self._connected = True
