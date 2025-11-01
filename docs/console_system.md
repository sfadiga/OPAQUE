# OPAQUE Framework Console System

## Overview

The OPAQUE Framework includes a built-in console system that captures and displays stdout/stderr output from your application. This is particularly useful for debugging, monitoring, and providing user feedback during long-running operations.

## Features

- **Automatic Output Capture**: Captures all stdout and stderr output
- **Real-time Display**: Shows output as it's generated
- **Search and Filter**: Find specific content and filter by output type
- **Export Functionality**: Save console output to text files
- **Configurable Display**: Timestamps, word wrapping, auto-scroll
- **Color Coding**: Different colors for stdout vs stderr
- **Thread-Safe**: Works with multi-threaded applications

## Architecture

The console system follows the MVP (Model-View-Presenter) pattern:

- **ConsoleService**: Handles stdout/stderr redirection and capture
- **ConsoleModel**: Stores console output and manages configuration
- **ConsoleWidget/ConsoleView**: UI components for display
- **ConsolePresenter**: Coordinates between service, model, and view

## Quick Start

### Basic Integration

```python
from opaque.view.application import OpaqueApplication
from opaque.presenters.console_presenter import ConsolePresenter
from opaque.models.console_model import ConsoleModel
from opaque.view.widgets.console_widget import ConsoleView

class MyApp(OpaqueApplication):
    def initialize_features(self):
        super().initialize_features()
        
        # Create console components
        console_model = ConsoleModel()
        console_view = ConsoleView()
        console_presenter = ConsolePresenter(console_model, console_view)
        
        # Add to toolbar
        self.main_toolbar.add_feature(console_presenter)
        
        # Initialize (starts capturing)
        console_presenter.initialize()
```

### Programmatic Output

```python
# Write directly to console
console_presenter.write_to_console("Custom message", "stdout")
console_presenter.write_to_console("Error message", "stderr")

# Regular print statements are automatically captured
print("This appears in the console")
print("This is an error", file=sys.stderr)
```

## Configuration Options

The console system supports various configuration options through the ConsoleModel:

### Display Settings

```python
# Access model configuration
model = console_presenter.model

# Auto-scroll to bottom
model.auto_scroll.set(True)

# Maximum buffer size (lines)
model.max_buffer_size.set(1000)

# Show timestamps
model.show_timestamps.set(True)

# Show/hide output types
model.show_stdout.set(True)
model.show_stderr.set(True)

# Word wrapping
model.word_wrap.set(True)
```

### Runtime Control

```python
# Toggle capture on/off
console_presenter.toggle_console_capture(True)

# Check if capturing
if console_presenter.is_console_capturing():
    print("Console is active")

# Clear console
console_presenter._clear_console()

# Get statistics
stats = console_presenter.get_console_stats()
print(f"Total lines: {stats['total_lines']}")
```

## User Interface

### Toolbar Controls

- **Clear**: Remove all console output
- **Auto-scroll**: Automatically scroll to new output
- **Word wrap**: Enable/disable line wrapping
- **Timestamps**: Show/hide timestamps
- **stdout/stderr**: Filter output types
- **Search**: Find text in console output
- **Export**: Save output to file

### Search Functionality

- Type search terms in the search box
- Use "Case sensitive" checkbox for exact matching
- Navigate through results with Previous/Next buttons
- Results are highlighted in the display

### Export Options

- Export current console content to text file
- Option to include or exclude timestamps
- Respects current filter settings (stdout/stderr)

## Advanced Usage

### Custom Output Formatting

```python
# Create custom output items
from opaque.models.console_model import ConsoleOutputItem
from datetime import datetime

item = ConsoleOutputItem(
    output_type="stdout",
    text="Custom formatted message\n",
    timestamp=datetime.now()
)

# Add to model (will appear in console)
console_model.add_output(item)
```

### Service Integration

```python
# Access the console service directly
from opaque.services.service import ServiceLocator

console_service = ServiceLocator.get_service("console")

# Start/stop capture manually
console_service.start_capture(preserve_original=True)
console_service.stop_capture()

# Write to specific streams
console_service.write_to_console("Message", "stdout")
```

### Event Handling

```python
# Connect to console events
console_model.output_added.connect(my_output_handler)
console_model.output_cleared.connect(my_clear_handler)

def my_output_handler(output_item):
    print(f"New output: {output_item.text}")

def my_clear_handler():
    print("Console was cleared")
```

## Implementation Details

### Stream Redirection

The console system uses a custom `StreamRedirector` class that:
- Preserves original stdout/stderr functionality
- Captures all output in real-time
- Emits signals for new output
- Handles both string and bytes output
- Thread-safe operation

### Buffer Management

- Configurable maximum buffer size
- Automatic trimming of old entries
- Efficient memory usage
- Fast search and filtering

### Performance Considerations

- Batched UI updates to prevent blocking
- Separate thread for output processing
- Configurable buffer limits
- Minimal overhead when not displayed

## Troubleshooting

### Common Issues

1. **No output appearing**:
   - Check if console capture is started
   - Verify stdout/stderr checkboxes are enabled
   - Check buffer size limits

2. **Performance issues**:
   - Reduce buffer size
   - Disable timestamps if not needed
   - Clear console regularly

3. **Missing output**:
   - Ensure `preserve_original=True` when starting capture
   - Check if output is being filtered

### Debug Mode

```python
# Enable debug output for console system
import logging
logging.getLogger('opaque.console').setLevel(logging.DEBUG)
```

## Examples

See `examples/console_example/main.py` for a complete working example that demonstrates:

- Basic console integration
- Automatic output capture
- Programmatic output generation
- Feature interaction
- Error handling

## API Reference

### ConsoleService

```python
class ConsoleService(BaseService):
    def start_capture(preserve_original: bool = True)
    def stop_capture()
    def is_capturing() -> bool
    def write_to_console(text: str, stream_type: str = 'stdout')
    
    # Signals
    output_received = Signal(dict)  # {'type': str, 'text': str, 'timestamp': datetime}
```

### ConsoleModel

```python
class ConsoleModel(BaseModel):
    # Configuration fields
    auto_scroll: BoolField
    max_buffer_size: IntField
    show_timestamps: BoolField
    show_stdout: BoolField
    show_stderr: BoolField
    word_wrap: BoolField
    
    # Methods
    def add_output(item: ConsoleOutputItem)
    def clear_output()
    def get_filtered_output() -> List[ConsoleOutputItem]
    def search_output(text: str, case_sensitive: bool) -> List[int]
    def export_to_file(path: str, include_timestamps: bool) -> bool
    def get_buffer_stats() -> Dict[str, Any]
    
    # Signals
    output_added = Signal(ConsoleOutputItem)
    output_cleared = Signal()
```

### ConsolePresenter

```python
class ConsolePresenter(BasePresenter):
    def initialize()
    def cleanup()
    def toggle_console_capture(enabled: bool)
    def is_console_capturing() -> bool
    def write_to_console(text: str, output_type: str = 'stdout')
    def get_console_stats() -> Dict[str, Any]
```

This console system provides a comprehensive solution for capturing, displaying, and managing application output within the OPAQUE framework.
