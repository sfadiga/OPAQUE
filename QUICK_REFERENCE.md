# OPAQUE Framework - Quick Reference

This document provides a concise reference for common OPAQUE Framework tasks and commands.

## Installation

```bash
# Basic installation
pip install opaque-framework

# With build tools
pip install "opaque-framework[build]"        # Both PyInstaller and Nuitka
pip install "opaque-framework[pyinstaller]"  # PyInstaller only
pip install "opaque-framework[nuitka]"       # Nuitka only

# Development installation
git clone https://github.com/sfadiga/OPAQUE.git
cd OPAQUE
pip install -e ".[dev]"
```

## Project Setup

```bash
# Using CI/CD scripts
./cicd.sh setup          # Setup virtual environment
./cicd.sh build          # Build framework
./cicd.sh run            # Run example
./cicd.sh clean          # Clean build artifacts

# Windows
.\cicd.ps1 setup
.\cicd.ps1 run
```

## Building Executables

### CLI Commands (Recommended)

```bash
# Quick builds
opaque-build pyinstaller main.py                    # Fast development build
opaque-build nuitka main.py                         # Optimized production build

# With options
opaque-build pyinstaller main.py --name MyApp       # Custom executable name
opaque-build pyinstaller main.py --onefile          # Single file executable
opaque-build pyinstaller main.py --windowed         # Hide console (GUI)
opaque-build pyinstaller main.py --debug            # Debug mode
opaque-build pyinstaller main.py --console          # Show console

# Full example
opaque-build pyinstaller main.py --name "My OPAQUE App" --onefile --windowed --icon assets/icon.ico
```

### CI/CD Scripts

```bash
# Linux/macOS
./cicd.sh build-exe pyinstaller                     # Default entry point
./cicd.sh build-exe nuitka examples/basic_example/main.py
./cicd.sh build-exe pyinstaller main.py --name MyApp

# Windows
.\cicd.ps1 build-exe pyinstaller
.\cicd.ps1 build-exe nuitka main.py
```

### Configuration Templates

```bash
# Copy templates to your project
cp src/opaque/build_tools/templates/pyinstaller_config.py .
cp src/opaque/build_tools/templates/nuitka_config.cfg .

# Edit configuration files, then build
pyinstaller pyinstaller_config.py
nuitka @nuitka_config.cfg main.py
```

## Basic Application Structure

### Minimal Application

```python
#!/usr/bin/env python3
import sys
from opaque.view.application import Application
from opaque.models.app_model import AppModel
from opaque.presenters.app_presenter import AppPresenter
from opaque.view.app_view import AppView

def main():
    app = Application(sys.argv)
    
    # Setup MVP
    model = AppModel()
    view = AppView()
    presenter = AppPresenter(model, view)
    
    # Configure and show
    view.setWindowTitle("My OPAQUE App")
    view.resize(800, 600)
    view.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
```

### MVP Pattern

```python
# Model
from opaque.models.model import BaseModel

class MyModel(BaseModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
    
    def add_item(self, item):
        self._data.append(item)
        self.dataChanged.emit()  # Emit signal

# View
from opaque.view.view import BaseView
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QListWidget

class MyView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.add_button = QPushButton("Add Item")
        layout.addWidget(self.list_widget)
        layout.addWidget(self.add_button)
        self.setLayout(layout)

# Presenter
from opaque.presenters.presenter import BasePresenter

class MyPresenter(BasePresenter):
    def __init__(self, model, view, parent=None):
        super().__init__(model, view, parent)
        self.setup_connections()
    
    def setup_connections(self):
        self.view.add_button.clicked.connect(self.on_add_item)
        self.model.dataChanged.connect(self.on_data_changed)
    
    def on_add_item(self):
        self.model.add_item(f"Item {len(self.model._data) + 1}")
    
    def on_data_changed(self):
        self.view.list_widget.clear()
        self.view.list_widget.addItems(self.model._data)
```

## Notifications & Logging

```python
# Get notification presenter
notification_presenter = self.get_notification_presenter()

# Add notifications
notification_presenter.notify_info("Title", "Message")
notification_presenter.notify_warning("Title", "Message") 
notification_presenter.notify_error("Title", "Message")
notification_presenter.notify_critical("Title", "Message")

# Logging with automatic notifications
notification_presenter.log_info("Info message", "ComponentName")
notification_presenter.log_warning("Warning message", "ComponentName")
notification_presenter.log_error("Error message", "ComponentName")

# Configure logging
notification_presenter.set_log_level("INFO")
notification_presenter.set_file_logging(True)
notification_presenter.set_console_logging(True)
```

## Configuration

### Type-Safe Settings

```python
from opaque.models.annotations import StringField, IntField, BoolField
from opaque.models.configuration import DefaultApplicationConfiguration

class MyAppConfig(DefaultApplicationConfiguration):
    app_name = StringField(default="MyApp")
    window_width = IntField(default=1280, description="Window width")
    enable_feature = BoolField(default=True, description="Enable feature")
    
    def get_application_name(self) -> str:
        return self.app_name
```

### Theme Management

```python
from opaque.services.service import ServiceLocator

# Get theme service
theme_service = ServiceLocator.get_service("theme")

# Set themes
theme_service.set_theme("light")   # Light theme
theme_service.set_theme("dark")    # Dark theme  
theme_service.set_theme("auto")    # Follow system
```

## Services

### Using ServiceLocator

```python
from opaque.services.service import ServiceLocator

# Get services
logger_service = ServiceLocator.get_service("logger")
notification_service = ServiceLocator.get_service("notification")
settings_service = ServiceLocator.get_service("settings")

# Register custom service
from opaque.services.service import BaseService

class MyService(BaseService):
    def __init__(self):
        super().__init__("my_service")

ServiceLocator.register_service(MyService())
my_service = ServiceLocator.get_service("my_service")
```

## Common File Locations

```
your_project/
├── main.py                          # Application entry point
├── requirements.txt                 # Dependencies
├── pyinstaller_config.py           # PyInstaller build config (optional)
├── nuitka_config.cfg               # Nuitka build config (optional)
├── assets/                         # Icons, images, etc.
│   └── icon.ico
├── config/                         # Configuration files
├── dist/                           # Built executables
└── features/                       # Your application features
    ├── feature1/
    │   ├── model.py
    │   ├── view.py
    │   └── presenter.py
    └── feature2/
        ├── model.py
        ├── view.py
        └── presenter.py
```

## Build Options Reference

### PyInstaller Options

| Option | Description | Example |
|--------|-------------|---------|
| `--name` | Executable name | `--name MyApp` |
| `--onefile` | Single file executable | `--onefile` |
| `--windowed` | Hide console | `--windowed` |
| `--console` | Show console | `--console` |
| `--debug` | Debug mode | `--debug` |
| `--icon` | Application icon | `--icon assets/icon.ico` |
| `--add-data` | Include data files | `--add-data "config.json:."` |
| `--hidden-import` | Include module | `--hidden-import mymodule` |
| `--exclude-module` | Exclude module | `--exclude-module tkinter` |

### Nuitka Options (via config file)

```cfg
--standalone                        # Standalone executable
--onefile                          # Single file
--windows-disable-console          # Hide console (Windows)
--enable-plugin=pyside6            # Enable PySide6 support
--optimization-level=1             # Optimization (0-2)
--include-data-files=src=dst       # Include data files
--nofollow-import-to=module        # Exclude module
--windows-icon-from-ico=icon.ico   # Windows icon
```

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| Missing modules | Add `--hidden-import module_name` |
| Missing files | Use `--add-data "source:dest"` |
| Large executable | Exclude unused modules with `--exclude-module` |
| Slow startup | Use Nuitka or `--onefile=False` |
| Qt/PySide6 errors | Ensure `--enable-plugin=pyside6` (Nuitka) |

### Debug Commands

```bash
# Verbose PyInstaller output
pyinstaller --log-level DEBUG pyinstaller_config.py

# Nuitka debug output  
nuitka --debug @nuitka_config.cfg main.py

# Test built executable
./dist/MyApp --help
```

## Example Workflows

### Development Cycle

```bash
# 1. Setup
./cicd.sh setup

# 2. Code & test
./cicd.sh run

# 3. Quick build test  
opaque-build pyinstaller main.py --debug

# 4. Test executable
./dist/main
```

### Production Release

```bash
# 1. Setup environment
./cicd.sh setup

# 2. Build optimized executable
opaque-build nuitka main.py --name ProductionApp

# 3. Test thoroughly
./dist/ProductionApp

# 4. Package for distribution
```

## Getting Help

- **Full Documentation**: [BUILD_GUIDE.md](BUILD_GUIDE.md)
- **Framework Documentation**: [README.md](README.md)
- **Examples**: `examples/` directory
- **Issues**: [GitHub Issues](https://github.com/sfadiga/OPAQUE/issues)

---

This quick reference covers the most common OPAQUE Framework tasks. For detailed information, see the complete documentation.
