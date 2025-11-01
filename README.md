# OPAQUE Framework

**OPAQUE** - *Opinionated Python Application with Qt UI for Engineering*

A flexible, modern MDI (Multiple Document Interface) application framework built on PySide6, designed for creating professional desktop applications with enterprise-grade features.

![OPAQUE Framework Screenshot](resources/showcase.gif)

## Features

### Core Architecture

- **MVP Pattern** - Clean Model-View-Presenter architecture for maintainable code
- **Service-Oriented Design** - Modular services with dependency injection via ServiceLocator
- **Plugin-Based Features** - Extensible feature system with automatic registration
- **Single Instance Support** - Prevent multiple application instances with inter-process communication

### User Interface

- **MDI Interface** - Multiple Document Interface with dockable windows
- **Theme Support** - Light and dark themes with automatic OS detection
- **Responsive Layout** - Adaptive layouts that work across different screen sizes
- **Dockable Widgets** - Flexible widget positioning and management

### Notification & Logging System

- **Multi-Level Notifications** - DEBUG, INFO, WARNING, ERROR, CRITICAL levels
- **Real-Time Notifications** - Live notification widget with visual indicators
- **Integrated Logging** - File and console logging with automatic notification integration
- **Interactive Management** - Mark as read, filter by level, clear notifications

### Configuration & Persistence

- **Annotation-Based Settings** - Type-safe configuration with automatic UI generation
- **Workspace Management** - Save and restore application state
- **Settings Persistence** - Automatic settings storage and retrieval
- **Custom Paths** - Configurable file locations for settings and workspaces

## Installation

### Requirements

- Python 3.8 or higher
- PySide6 6.0.0 or higher

### Install from PyPI

```bash
pip install opaque-framework
```

### Install from Source

```bash
git clone https://github.com/sfadiga/OPAQUE.git
cd OPAQUE
pip install -e .
```

### Optional Dependencies

```bash
# For additional themes
pip install "opaque-framework[themes]"

# For development
pip install "opaque-framework[dev]"
```

## Quick Start

### Basic Application

```python
from PySide6.QtWidgets import QApplication
from opaque.view.application import BaseApplication
from opaque.models.configuration import DefaultApplicationConfiguration
import sys

class MyAppConfig(DefaultApplicationConfiguration):
    def get_application_name(self) -> str:
        return "MyApp"
    
    def get_application_title(self) -> str:
        return "My Application"

class MyApplication(BaseApplication):
    def __init__(self):
        config = MyAppConfig()
        super().__init__(config)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MyApplication()
    
    if not main_window.try_acquire_lock():
        main_window.show_already_running_message()
        sys.exit(1)
        
    main_window.show()
    sys.exit(app.exec())
```

### Adding Features with MVP Pattern

```python
# Model
from opaque.models.model import BaseModel

class CalculatorModel(BaseModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = 0
    
    def add(self, a: float, b: float) -> float:
        self.result = a + b
        return self.result

# View  
from opaque.view.view import BaseView
from PySide6.QtWidgets import QPushButton, QLineEdit, QVBoxLayout

class CalculatorView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.input_a = QLineEdit()
        self.input_b = QLineEdit()
        self.add_button = QPushButton("Add")
        self.result_label = QLabel("Result: 0")
        
        layout.addWidget(self.input_a)
        layout.addWidget(self.input_b)
        layout.addWidget(self.add_button)
        layout.addWidget(self.result_label)
        self.setLayout(layout)

# Presenter
from opaque.presenters.presenter import BasePresenter

class CalculatorPresenter(BasePresenter):
    def __init__(self, model: CalculatorModel, view: CalculatorView, parent=None):
        super().__init__(model, view, parent)
        self.setup_connections()
    
    def setup_connections(self):
        self.view.add_button.clicked.connect(self.on_add_clicked)
    
    def on_add_clicked(self):
        a = float(self.view.input_a.text() or 0)
        b = float(self.view.input_b.text() or 0)
        result = self.model.add(a, b)
        self.view.result_label.setText(f"Result: {result}")
```

### Using the Notification System

```python
# Get notification presenter (automatically available in BaseApplication)
notification_presenter = self.get_notification_presenter()

# Add notifications
notification_presenter.notify_info("Success", "Operation completed successfully")
notification_presenter.notify_warning("Warning", "This is a warning message")
notification_presenter.notify_error("Error", "Something went wrong")

# Log with automatic notifications
notification_presenter.log_error("Critical error occurred", "MyComponent")
notification_presenter.log_warning("Performance degraded", "MyComponent")
```

## Project Structure

```cmd
opaque/
├── models/                 # Data models and business logic
│   ├── abstract_model.py   # Base model interfaces
│   ├── annotations.py      # Configuration field annotations
│   ├── app_model.py       # Application-level model
│   ├── configuration.py   # Configuration management
│   ├── logger_model.py    # Logging model
│   ├── model.py          # Base model implementation
│   ├── notification_model.py        # Notification model
│   └── notification_settings_model.py  # Notification settings
├── presenters/            # Business logic coordinators
│   ├── app_presenter.py   # Application presenter
│   ├── notification_presenter.py    # Notification system presenter
│   └── presenter.py       # Base presenter
├── services/              # Reusable services
│   ├── logger_service.py  # Logging service
│   ├── notification_service.py      # Notification service
│   ├── service.py         # Base service and ServiceLocator
│   ├── settings_service.py          # Settings persistence
│   ├── single_instance_service.py   # Single instance management
│   ├── theme_service.py   # Theme management
│   └── workspace_service.py         # Workspace persistence
└── view/                  # User interface components
    ├── dialogs/           # Dialog windows
    │   └── settings.py    # Settings dialog
    ├── layouts/           # Custom layouts
    │   └── flow.py        # Flow layout
    ├── widgets/           # Custom widgets
    │   ├── color_picker.py           # Color picker widget
    │   ├── mdi_window.py  # MDI window implementation
    │   ├── notification_widget.py    # Notification panel
    │   └── toolbar.py     # Custom toolbar
    ├── app_view.py        # Main application view
    ├── application.py     # Base application class
    └── view.py           # Base view implementation
```

## Examples

The framework includes several comprehensive examples:

### Basic Example

```bash
cd examples/basic_example
python main.py
```

Features: Calculator, Data Viewer, and Logging components demonstrating MVP pattern.

### Notification Example

```bash
cd examples/notification_example  
python main.py
```

Features: Complete notification and logging system demonstration.

### Todo List Example

```bash
cd examples/my_example
python main.py
```

Features: Simple todo list application showing basic framework usage.

## Configuration

### Application Configuration

Use annotations to define type-safe configuration:

```python
from opaque.models.annotations import StringField, IntField, BoolField
from opaque.models.configuration import DefaultApplicationConfiguration

class MyAppConfig(DefaultApplicationConfiguration):
    # Basic app info
    app_name = StringField(default="MyApp")
    app_version = StringField(default="1.0.0")
    app_title = StringField(default="My Application")
    
    # Window settings
    window_width = IntField(default=1280, description="Window width")
    window_height = IntField(default=720, description="Window height")
    
    # Features
    enable_notifications = BoolField(default=True, description="Enable notifications")
    enable_logging = BoolField(default=True, description="Enable file logging")
```

### Theme Configuration

```python
# Available themes
themes = ["light", "dark", "auto"]  # auto follows system

# Set theme programmatically
theme_service = ServiceLocator.get_service("theme")
theme_service.set_theme("dark")
```

### Notification Settings

```python
# Configure notification behavior
notification_presenter = self.get_notification_presenter()

# Set logging levels that trigger notifications
notification_presenter.set_notification_on_error(True)
notification_presenter.set_notification_on_critical(True)

# Configure logging
notification_presenter.set_log_level("INFO")
notification_presenter.set_file_logging(True)
notification_presenter.set_console_logging(True)
```

## API Reference

### Core Classes

#### BaseApplication

Main application class providing MDI interface and service management.

**Key Methods:**

- `register_feature(presenter)` - Register a feature presenter
- `get_notification_presenter()` - Get notification system access
- `try_acquire_lock()` - Single instance management
- `save_workspace()` / `load_workspace()` - Workspace persistence

#### BasePresenter

Base class for implementing MVP presenters.

**Key Methods:**

- `initialize()` - Initialize presenter after construction
- `cleanup()` - Clean up resources
- `get_view_title()` - Get display title for the view

#### BaseModel

Base class for data models with automatic persistence.

**Key Features:**

- Automatic property persistence with annotations
- Signal emission on property changes
- Integration with settings service

#### BaseView

Base class for UI components with MDI support.

**Key Features:**

- Automatic docking widget creation
- Theme-aware styling
- Signal/slot connection helpers

### Services

#### NotificationService

Manages application notifications with multiple severity levels.

**Key Methods:**

- `add_notification(level, title, message, source, persistent)` - Add notification
- `mark_as_read(notification_id)` - Mark notification as read
- `get_notifications(level_filter, unread_only)` - Retrieve notifications
- `clear_notifications(level_filter)` - Clear notifications

#### LoggerService  

Provides structured logging with file and console output.

**Key Methods:**

- `debug()`, `info()`, `warning()`, `error()`, `critical()` - Log messages
- `set_log_level(level)` - Configure logging level
- `set_file_logging(enabled)` - Enable/disable file logging

#### ServiceLocator

Central registry for application services.

**Key Methods:**

- `register_service(name, service)` - Register a service
- `get_service(name)` - Retrieve a service
- `unregister_service(name)` - Remove a service

## Development

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/sfadiga/OPAQUE.git
cd OPAQUE

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ examples/

# Type checking
mypy src/
```

### Creating Custom Features

1. **Create Model** - Implement business logic and data management
2. **Create View** - Design user interface components  
3. **Create Presenter** - Connect model and view, handle user interactions
4. **Register Feature** - Add to application using `register_feature()`

### Extending Services

```python
from opaque.services.service import BaseService

class MyCustomService(BaseService):
    def __init__(self):
        super().__init__("my_service")
        # Initialize service
    
    def my_method(self):
        # Implement functionality
        pass

# Register with ServiceLocator
ServiceLocator.register_service(MyCustomService())
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Guidelines

1. Follow PEP 8 code style
2. Add tests for new features
3. Update documentation
4. Ensure compatibility with Python 3.8+

### Development Process

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Run the test suite
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/sfadiga/OPAQUE/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sfadiga/OPAQUE/discussions)  
- **Email**: <sfadiga@gmail.com>

## Acknowledgments

- Built with [PySide6](https://doc.qt.io/qtforpython-6/) - Qt for Python
- Inspired by enterprise application patterns
- Thanks to the Qt and Python communities

---

**OPAQUE Framework** - Building professional desktop applications made simple.
