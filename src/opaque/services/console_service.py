"""
Console service for capturing and redirecting stdout/stderr output.

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

import sys
import io
from typing import TextIO, Optional, Callable, Dict, Any
from threading import Lock
from queue import Queue, Empty
from PySide6.QtCore import Signal, QTimer

from opaque.services.service import BaseService


class StreamRedirector(io.TextIOBase):
    """Custom stream that redirects output to a queue while preserving original functionality."""

    def __init__(self, output_queue: Queue[Dict[str, Any]], stream_type: str, original_stream: Optional[TextIO] = None):
        super().__init__()
        self.output_queue = output_queue
        self.stream_type = stream_type
        self.original_stream = original_stream
        self._lock = Lock()

    def write(self, text: str) -> int:
        """Write text to both the queue and original stream if available."""
        if not text:
            return 0

        with self._lock:
            # Add to queue for console display
            try:
                self.output_queue.put({
                    'type': self.stream_type,
                    'text': text,
                    'timestamp': None  # Will be set by console service
                }, block=False)
            except:
                pass  # Queue full, ignore

            # Write to original stream if available (for actual console)
            if self.original_stream:
                try:
                    result = self.original_stream.write(text)
                    self.original_stream.flush()
                    return result
                except:
                    pass

            return len(text)

    def flush(self):
        """Flush the original stream if available."""
        if self.original_stream:
            try:
                self.original_stream.flush()
            except:
                pass

    def readable(self) -> bool:
        return False

    def writable(self) -> bool:
        return True


class ConsoleService(BaseService):
    """Service for capturing stdout/stderr and providing console functionality."""

    # Signals
    output_received = Signal(dict)  # Emitted when new output is captured

    def __init__(self):
        super().__init__("console")

        self.output_queue: Queue[Dict[str, Any]] = Queue(maxsize=1000)
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        self.stdout_redirector: Optional[StreamRedirector] = None
        self.stderr_redirector: Optional[StreamRedirector] = None

        self._is_capturing = False
        self._output_handlers: list[Callable[[Dict[str, Any]], None]] = []

        # Timer to process queued output
        self._process_timer = QTimer()
        self._process_timer.timeout.connect(self._process_output_queue)
        self._process_timer.setInterval(50)  # Process every 50ms

    def initialize(self):
        """Initialize the console service."""
        super().initialize()
        self._process_timer.start()

    def cleanup(self):
        """Clean up the console service."""
        self.stop_capture()
        self._process_timer.stop()
        super().cleanup()

    def start_capture(self, preserve_original: bool = True):
        """
        Start capturing stdout/stderr.

        Args:
            preserve_original: If True, also write to original streams
        """
        if self._is_capturing:
            return

        # Create redirectors
        original_stdout = self.original_stdout if preserve_original else None
        original_stderr = self.original_stderr if preserve_original else None

        self.stdout_redirector = StreamRedirector(
            self.output_queue, 'stdout', original_stdout
        )
        self.stderr_redirector = StreamRedirector(
            self.output_queue, 'stderr', original_stderr
        )

        # Redirect streams
        sys.stdout = self.stdout_redirector
        sys.stderr = self.stderr_redirector

        self._is_capturing = True

    def stop_capture(self):
        """Stop capturing stdout/stderr and restore original streams."""
        if not self._is_capturing:
            return

        # Restore original streams
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

        self.stdout_redirector = None
        self.stderr_redirector = None
        self._is_capturing = False

    def is_capturing(self) -> bool:
        """Check if currently capturing output."""
        return self._is_capturing

    def add_output_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Add a handler for output events."""
        if handler not in self._output_handlers:
            self._output_handlers.append(handler)

    def remove_output_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Remove an output handler."""
        if handler in self._output_handlers:
            self._output_handlers.remove(handler)

    def clear_queue(self):
        """Clear the output queue."""
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except Empty:
                break

    def _process_output_queue(self):
        """Process items from the output queue and emit signals."""
        from datetime import datetime

        while not self.output_queue.empty():
            try:
                output_item = self.output_queue.get_nowait()

                # Add timestamp if not present
                if output_item.get('timestamp') is None:
                    output_item['timestamp'] = datetime.now()

                # Emit signal
                self.output_received.emit(output_item)

                # Call handlers
                for handler in self._output_handlers:
                    try:
                        handler(output_item)
                    except Exception as e:
                        # Don't let handler errors break the service
                        print(f"Console handler error: {e}")

            except Empty:
                break
            except Exception as e:
                print(f"Console processing error: {e}")
                break

    def write_to_console(self, text: str, stream_type: str = 'stdout'):
        """
        Manually write text to the console (for programmatic output).

        Args:
            text: Text to write
            stream_type: 'stdout' or 'stderr'
        """
        from datetime import datetime

        output_item = {
            'type': stream_type,
            'text': text,
            'timestamp': datetime.now()
        }

        try:
            self.output_queue.put(output_item, block=False)
        except:
            pass  # Queue full, ignore
