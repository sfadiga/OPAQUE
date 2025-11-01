"""
Console model for managing console output data.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QIcon

if TYPE_CHECKING:
    from opaque.view.application import BaseApplication


class ConsoleOutputItem:
    """Represents a single console output item."""

    def __init__(self, output_type: str, text: str, timestamp: datetime):
        self.output_type = output_type  # 'stdout' or 'stderr'
        self.text = text
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'type': self.output_type,
            'text': self.text,
            'timestamp': self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConsoleOutputItem':
        """Create from dictionary."""
        timestamp = datetime.fromisoformat(data['timestamp']) if isinstance(
            data['timestamp'], str) else data['timestamp']
        return cls(data['type'], data['text'], timestamp)


class ConsoleModel(QObject):
    """Model for managing console output and settings."""

    # Signals
    # Emitted when new output is added (ConsoleOutputItem)
    output_added = Signal(object)
    output_cleared = Signal()  # Emitted when output is cleared

    def __init__(self, app: 'BaseApplication'):
        super().__init__()
        self._app = app
        self._observers = []

        # Configuration settings
        self._auto_scroll = True
        self._max_buffer_size = 1000
        self._show_timestamps = True
        self._show_stdout = True
        self._show_stderr = True
        self._word_wrap = True

        # Console output buffer
        self._output_buffer: List[ConsoleOutputItem] = []

    def feature_name(self) -> str:
        """Return the feature name for this model."""
        return "Console"

    def feature_description(self) -> str:
        """Return the feature description."""
        return "Internal console for capturing stdout and stderr output"

    def feature_icon(self) -> QIcon:
        """Return the feature icon."""
        return QIcon.fromTheme("utilities-terminal")

    # BaseModel interface methods
    @property
    def app(self) -> 'BaseApplication':
        return self._app

    def attach(self, observer) -> None:
        """Attach an observer."""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer) -> None:
        """Detach an observer."""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, property_name: str, value: Any) -> None:
        """Notify observers of property changes."""
        for observer in self._observers:
            if hasattr(observer, 'update'):
                observer.update(property_name, value, None, self)

    # Configuration properties
    @property
    def auto_scroll(self) -> bool:
        return self._auto_scroll

    @auto_scroll.setter
    def auto_scroll(self, value: bool):
        self._auto_scroll = value

    @property
    def max_buffer_size(self) -> int:
        return self._max_buffer_size

    @max_buffer_size.setter
    def max_buffer_size(self, value: int):
        self._max_buffer_size = value

    @property
    def show_timestamps(self) -> bool:
        return self._show_timestamps

    @show_timestamps.setter
    def show_timestamps(self, value: bool):
        self._show_timestamps = value

    @property
    def show_stdout(self) -> bool:
        return self._show_stdout

    @show_stdout.setter
    def show_stdout(self, value: bool):
        self._show_stdout = value

    @property
    def show_stderr(self) -> bool:
        return self._show_stderr

    @show_stderr.setter
    def show_stderr(self, value: bool):
        self._show_stderr = value

    @property
    def word_wrap(self) -> bool:
        return self._word_wrap

    @word_wrap.setter
    def word_wrap(self, value: bool):
        self._word_wrap = value

    def add_output(self, output_item: ConsoleOutputItem):
        """
        Add a new output item to the buffer.

        Args:
            output_item: The output item to add
        """
        # Add to buffer
        self._output_buffer.append(output_item)

        # Trim buffer if it exceeds max size
        if len(self._output_buffer) > self.max_buffer_size:
            self._output_buffer = self._output_buffer[-self.max_buffer_size:]

        # Emit signal
        self.output_added.emit(output_item)

    def add_output_from_dict(self, output_dict: Dict[str, Any]):
        """
        Add output from dictionary (from console service).

        Args:
            output_dict: Dictionary containing output data
        """
        output_item = ConsoleOutputItem(
            output_type=output_dict['type'],
            text=output_dict['text'],
            timestamp=output_dict['timestamp']
        )
        self.add_output(output_item)

    def clear_output(self):
        """Clear all console output."""
        self._output_buffer.clear()
        self.output_cleared.emit()

    def get_output_buffer(self) -> List[ConsoleOutputItem]:
        """Get the current output buffer."""
        return self._output_buffer.copy()

    def get_filtered_output(self) -> List[ConsoleOutputItem]:
        """Get filtered output based on current settings."""
        filtered = []

        for item in self._output_buffer:
            # Filter by type
            if item.output_type == 'stdout' and not self.show_stdout:
                continue
            if item.output_type == 'stderr' and not self.show_stderr:
                continue

            filtered.append(item)

        return filtered

    def get_output_as_text(self, include_timestamps: Optional[bool] = None) -> str:
        """
        Get all output as formatted text.

        Args:
            include_timestamps: Whether to include timestamps. If None, uses model setting.

        Returns:
            Formatted text string
        """
        if include_timestamps is None:
            include_timestamps = self.show_timestamps

        lines = []
        for item in self.get_filtered_output():
            if include_timestamps:
                timestamp_str = item.timestamp.strftime("%H:%M:%S.%f")[:-3]
                prefix = f"[{timestamp_str}] "
                if item.output_type == 'stderr':
                    prefix += "[ERROR] "
            else:
                prefix = ""

            # Handle multi-line text
            text_lines = item.text.rstrip('\n').split('\n')
            for line in text_lines:
                lines.append(f"{prefix}{line}")

        return '\n'.join(lines)

    def export_to_file(self, file_path: str, include_timestamps: bool = True) -> bool:
        """
        Export console output to a text file.

        Args:
            file_path: Path to save the file
            include_timestamps: Whether to include timestamps

        Returns:
            True if successful, False otherwise
        """
        try:
            text_content = self.get_output_as_text(include_timestamps)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            return True
        except Exception as e:
            print(f"Error exporting console to file: {e}")
            return False

    def search_output(self, search_text: str, case_sensitive: bool = False) -> List[int]:
        """
        Search for text in the output buffer.

        Args:
            search_text: Text to search for
            case_sensitive: Whether search is case sensitive

        Returns:
            List of indices where matches were found
        """
        if not search_text:
            return []

        matches = []
        filtered_output = self.get_filtered_output()

        search_lower = search_text.lower() if not case_sensitive else search_text

        for i, item in enumerate(filtered_output):
            text_to_search = item.text.lower() if not case_sensitive else item.text
            if search_lower in text_to_search:
                matches.append(i)

        return matches

    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get statistics about the current buffer."""
        stdout_count = sum(
            1 for item in self._output_buffer if item.output_type == 'stdout')
        stderr_count = sum(
            1 for item in self._output_buffer if item.output_type == 'stderr')

        total_chars = sum(len(item.text) for item in self._output_buffer)

        return {
            'total_lines': len(self._output_buffer),
            'stdout_lines': stdout_count,
            'stderr_lines': stderr_count,
            'total_characters': total_chars,
            'buffer_limit': self.max_buffer_size
        }

    def cleanup(self) -> None:
        """Clean up model resources."""
        self._observers.clear()
        self._output_buffer.clear()
