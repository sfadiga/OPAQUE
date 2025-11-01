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

### Console System

- **Real-Time Output Capture** - Automatic stdout/stderr redirection and display
- **Rich Console Display** - Color-coded output with timestamp support
- **Export Functionality** - Save console output to text files for analysis
- **Search & Filter** - Find specific text and filter by output type
- **Interactive Controls** - Clear, auto-scroll, word wrap, and visibility toggles
- **MDI Integration** - Full console window with comprehensive toolbar

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
│   ├── app_model.py        # Application-level model
│   ├── configuration.py    # Configuration management
│   ├── console_model.py    # Console output model
│   ├── logger_model.py     # Logging model
│   ├── model.py                        # Base model implementation
│   ├── notification_model.py           # Notification model
│   └── notification_settings_model.py  # Notification settings
├── presenters/                      # Business logic coordinators
│   ├── app_presenter.py             # Application presenter
│   ├── console_presenter.py         # Console system presenter
│   ├── notification_presenter.py    # Notification system presenter
│   └── presenter.py                 # Base presenter
├── services/                        # Reusable services
│   ├── console_service.py           # Console output capture service
│   ├── logger_service.py            # Logging service
│   ├── notification_service.py      # Notification service
│   ├── service.py                   # Base service and ServiceLocator
│   ├── settings_service.py          # Settings persistence
│   ├── single_instance_service.py   # Single instance management
│   ├── theme_service.py             # Theme management
│   └── workspace_service.py         # Workspace persistence
└── view/                  # User interface components
    ├── dialogs/           # Dialog windows
    │   └── settings.py    # Settings dialog
    ├── layouts/           # Custom layouts
    │   └── flow.py        # Flow layout
    ├── widgets/           # Custom widgets
    │   ├── closeable_tab_widget.py   # Closeable tab widget
    │   ├── color_picker.py           # Color picker widget
    │   ├── console_widget.py         # Console display widget
    │   ├── mdi_window.py             # MDI window implementation
    │   ├── notification_widget.py    # Notification panel
    │   └── toolbar.py                # Custom toolbar
    ├── app_view.py        # Main application view
    ├── application.py     # Base application class
    └── view.py            # Base view implementation
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

### Console Example

```bash
cd examples/console_example
python main.py
```

Features: Complete console system demonstration with real-time output capture, export functionality, and interactive controls.

### Professional Build System

- **Dual Build Tools** - Support for both PyInstaller and Nuitka with optimized configurations
- **Version Management** - Automatic version detection and injection into executables
- **CI/CD Integration** - Shell and PowerShell scripts for automated building
- **Professional Executables** - Windows version resources, icons, and metadata

## Building Executables

OPAQUE Framework provides a comprehensive build system for creating professional standalone executables using **PyInstaller** or **Nuitka**. The system automatically handles version management, metadata injection, and resource bundling.

### Key Features

✅ **Automatic Version Detection** - From pyproject.toml, setup.py, Git tags, or environment variables  
✅ **Professional Metadata** - Windows version resources, company info, descriptions  
✅ **Icon Integration** - Automatic icon embedding from multiple formats  
✅ **Advanced Optimization** - Performance tuning for both development and production  
✅ **CI/CD Ready** - Automated scripts for continuous integration  
✅ **Cross-Platform** - Windows, macOS, and Linux support  

### Quick Start

```bash
# Install with build tools
pip install "opaque-framework[build]"  # Both PyInstaller and Nuitka
pip install "opaque-framework[pyinstaller]"  # PyInstaller only  
pip install "opaque-framework[nuitka]"  # Nuitka only

# Simple builds
opaque-build pyinstaller main.py               # Fast development build
opaque-build nuitka main.py                    # Optimized production build

# Professional builds with metadata
opaque-build pyinstaller main.py \
    --name "MyApp" \
    --version "1.2.0" \
    --icon assets/icon.ico \
    --onefile --windowed

opaque-build nuitka main.py \
    --name "MyApp" \
    --version "auto" \
    --icon assets/icon.ico \
    --optimize --windows-disable-console
```

### CI/CD Integration

Use the included automation scripts for continuous integration:

```bash
# Linux/macOS Shell Scripts
./cicd.sh build_pyinstaller_exe "MyApp" "1.0.0"  # Explicit version
./cicd.sh build_nuitka_exe "MyApp" "auto"        # Auto-detect version

# Windows PowerShell Scripts  
.\cicd.ps1 Build-PyInstallerExe -AppName "MyApp" -Version "1.0.0"
.\cicd.ps1 Build-NuitkaExe -AppName "MyApp" -Version "auto"
```

### Version Management System

The framework includes a sophisticated version management system:

```python
# Automatic version detection in your app
from opaque.models.configuration import DefaultApplicationConfiguration

class MyAppConfig(DefaultApplicationConfiguration):
    def __init__(self):
        super().__init__()
        # Version info automatically available from:
        # - pyproject.toml
        # - setup.py  
        # - Git tags
        # - Environment variables
        version_info = self.version_manager.get_version_info()
        print(f"App version: {version_info['version']}")
```

### Builder Comparison

| Feature | PyInstaller | Nuitka |
|---------|-------------|--------|
| **Build Speed** | ⚡ Fast (2-5 min) | 🐌 Slow (10-60 min) |
| **Executable Size** | 📦 Larger (50-200MB) | 📦 Smaller (20-100MB) |
| **Runtime Performance** | ⚙️ Standard Python speed | 🚀 2-10x faster |
| **Startup Time** | ⚡ Fast startup | ⚡ Very fast startup |
| **Memory Usage** | 💾 Higher | 💾 Lower |
| **Best For** | Development/Testing | Production/Performance |
| **Compatibility** | 🟢 Excellent | 🟡 Good (some limitations) |

### Advanced Configuration

For complex applications, use configuration templates:

```bash
# Generate template files
opaque-build generate-config pyinstaller > build_config.py
opaque-build generate-config nuitka > build_config.cfg

# Customize and build
pyinstaller build_config.py
nuitka @build_config.cfg main.py
```

### Version UI Integration

Display version information in your application:

```python
from opaque.view.dialogs.version_info import (
    VersionInfoDialog, VersionStatusWidget, AboutDialog
)

# Show comprehensive version dialog
version_info = self.configuration.version_manager.get_version_info()
dialog = VersionInfoDialog(version_info, parent=self)
dialog.exec()

# Add version widget to status bar
version_widget = VersionStatusWidget(version_info)
self.status_bar.addPermanentWidget(version_widget)

# Professional about dialog
about_dialog = AboutDialog(version_info, self.windowIcon(), self)
about_dialog.exec()
```

**📖 Complete Documentation:**

- [BUILD_GUIDE.md](docs/BUILD_GUIDE.md) - Comprehensive building guide
- [VERSION_MANAGEMENT.md](docs/VERSION_MANAGEMENT.md) - Version system documentation  
- [QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - Quick command reference
- [API_REFERENCE.md](docs/API_REFERENCE.md) - Complete API documentation

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
