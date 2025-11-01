# OPAQUE Framework - API Documentation

This document provides detailed API documentation for the OPAQUE Framework's build tools and core components.

## Build Tools API

### CLI Module

#### `opaque.build_tools.cli`

The CLI module provides command-line interface for building executables.

```python
from opaque.build_tools.cli import main, build_executable

# Main CLI entry point
main(args: Optional[List[str]] = None) -> int

# Direct function call
build_executable(
    builder: str,           # "pyinstaller" or "nuitka"
    entry_point: str,       # Path to main Python file
    name: Optional[str] = None,      # Executable name
    onefile: bool = True,            # Single file executable
    windowed: bool = False,          # Hide console
    debug: bool = False,             # Debug mode
    icon: Optional[str] = None,      # Icon path
    additional_args: Optional[List[str]] = None  # Extra arguments
) -> bool
```

**Example Usage:**

```python
from opaque.build_tools.cli import build_executable

# Build with PyInstaller
success = build_executable(
    builder="pyinstaller",
    entry_point="main.py",
    name="MyApp",
    onefile=True,
    windowed=True,
    icon="assets/icon.ico"
)

if success:
    print("Build completed successfully")
else:
    print("Build failed")
```

### Builder Classes

#### `opaque.build_tools.pyinstaller_builder.PyInstallerBuilder`

PyInstaller builder implementation.

**Constructor:**

```python
PyInstallerBuilder(logger: Optional[logging.Logger] = None)
```

**Methods:**

```python
def build(
    self,
    entry_point: str,                    # Main Python file
    name: Optional[str] = None,          # Executable name
    onefile: bool = True,                # Single file mode
    windowed: bool = False,              # Hide console
    console: bool = False,               # Show console (overrides windowed)
    debug: bool = False,                 # Debug mode
    icon: Optional[str] = None,          # Icon file path
    add_data: Optional[List[Tuple[str, str]]] = None,  # Data files
    hidden_imports: Optional[List[str]] = None,        # Additional imports
    exclude_modules: Optional[List[str]] = None,       # Exclude modules
    additional_args: Optional[List[str]] = None,       # Extra arguments
    output_dir: str = "dist"             # Output directory
) -> bool
```

**Example:**

```python
from opaque.build_tools.pyinstaller_builder import PyInstallerBuilder

builder = PyInstallerBuilder()

success = builder.build(
    entry_point="main.py",
    name="MyOpaqueApp",
    onefile=True,
    windowed=True,
    icon="assets/icon.ico",
    add_data=[("config.json", "."), ("assets/", "assets/")],
    hidden_imports=["my_custom_module"],
    exclude_modules=["tkinter", "matplotlib"]
)
```

#### `opaque.build_tools.nuitka_builder.NuitkaBuilder`

Nuitka builder implementation.

**Constructor:**

```python
NuitkaBuilder(logger: Optional[logging.Logger] = None)
```

**Methods:**

```python
def build(
    self,
    entry_point: str,                    # Main Python file
    standalone: bool = True,             # Standalone mode
    onefile: bool = True,                # Single file mode
    enable_plugin: Optional[List[str]] = None,         # Enabled plugins
    disable_console: bool = False,       # Hide console
    optimization_level: int = 1,         # Optimization (0-2)
    icon: Optional[str] = None,          # Icon file path
    include_data_files: Optional[List[Tuple[str, str]]] = None,  # Data files
    nofollow_imports: Optional[List[str]] = None,      # Exclude imports
    additional_args: Optional[List[str]] = None,       # Extra arguments
    output_dir: str = "dist"             # Output directory
) -> bool
```

**Example:**

```python
from opaque.build_tools.nuitka_builder import NuitkaBuilder

builder = NuitkaBuilder()

success = builder.build(
    entry_point="main.py",
    standalone=True,
    onefile=True,
    enable_plugin=["pyside6"],
    disable_console=True,
    optimization_level=2,
    icon="assets/icon.ico",
    include_data_files=[("config.json", ".")]
)
```

#### `opaque.build_tools.builder.BaseBuilder`

Abstract base class for all builders.

**Methods:**

```python
def build(self, entry_point: str, **kwargs) -> bool:
    """Build executable from entry point."""
    # Abstract method - must be implemented by subclasses

def validate_entry_point(self, entry_point: str) -> bool:
    """Validate that entry point file exists."""

def create_output_dir(self, output_dir: str) -> bool:
    """Create output directory if it doesn't exist."""

def log_info(self, message: str) -> None:
    """Log informational message."""

def log_error(self, message: str) -> None:
    """Log error message."""
```

## Core Framework API

### Application Classes

#### `opaque.view.application.Application`

Main application class with MDI support.

**Constructor:**

```python
Application(argv: List[str])
```

**Key Methods:**

```python
def register_feature(self, presenter: BasePresenter) -> None:
    """Register a feature presenter with the application."""

def get_notification_presenter(self) -> NotificationPresenter:
    """Get the notification system presenter."""

def try_acquire_lock(self) -> bool:
    """Try to acquire single instance lock."""

def show_already_running_message(self) -> None:
    """Show message when app is already running."""

def save_workspace(self) -> None:
    """Save current workspace state."""

def load_workspace(self) -> None:
    """Load workspace state."""
```

### MVP Base Classes

#### `opaque.models.model.BaseModel`

Base class for data models.

**Constructor:**

```python
BaseModel(parent: Optional[QObject] = None)
```

**Signals:**

```python
dataChanged = Signal()  # Emitted when data changes
```

#### `opaque.view.view.BaseView`

Base class for UI views.

**Constructor:**

```python
BaseView(parent: Optional[QWidget] = None)
```

**Methods:**

```python
def create_docking_widget(self, title: str, parent: QMainWindow) -> QDockWidget:
    """Create a docking widget for this view."""

def setup_ui(self) -> None:
    """Setup the user interface (override in subclasses)."""
```

#### `opaque.presenters.presenter.BasePresenter`

Base class for MVP presenters.

**Constructor:**

```python
BasePresenter(
    model: BaseModel,
    view: BaseView,
    parent: Optional[QObject] = None
)
```

**Methods:**

```python
def initialize(self) -> None:
    """Initialize the presenter (called after construction)."""

def cleanup(self) -> None:
    """Clean up resources."""

def get_view_title(self) -> str:
    """Get the title for the view."""
```

### Service Classes

#### `opaque.services.service.ServiceLocator`

Central service registry.

**Static Methods:**

```python
@staticmethod
def register_service(name: str, service: BaseService) -> None:
    """Register a service with the given name."""

@staticmethod
def get_service(name: str) -> Optional[BaseService]:
    """Get a service by name."""

@staticmethod
def unregister_service(name: str) -> None:
    """Unregister a service."""

@staticmethod
def get_all_services() -> Dict[str, BaseService]:
    """Get all registered services."""
```

#### `opaque.services.notification_service.NotificationService`

Notification management service.

**Constructor:**

```python
NotificationService()
```

**Methods:**

```python
def add_notification(
    self,
    level: str,                          # "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    title: str,                          # Notification title
    message: str,                        # Notification message
    source: str = "System",              # Source component
    persistent: bool = False             # Whether notification persists
) -> str:                               # Returns notification ID
    """Add a new notification."""

def mark_as_read(self, notification_id: str) -> bool:
    """Mark notification as read."""

def get_notifications(
    self,
    level_filter: Optional[str] = None,  # Filter by level
    unread_only: bool = False            # Only unread notifications
) -> List[NotificationModel]:
    """Get notifications."""

def clear_notifications(self, level_filter: Optional[str] = None) -> int:
    """Clear notifications, returns count cleared."""
```

#### `opaque.services.logger_service.LoggerService`

Logging service with file and console output.

**Constructor:**

```python
LoggerService(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    console_logging: bool = True,
    file_logging: bool = True
)
```

**Methods:**

```python
def debug(self, message: str, source: str = "System") -> None:
def info(self, message: str, source: str = "System") -> None:
def warning(self, message: str, source: str = "System") -> None:
def error(self, message: str, source: str = "System") -> None:
def critical(self, message: str, source: str = "System") -> None:

def set_log_level(self, level: str) -> None:
def set_file_logging(self, enabled: bool) -> None:
def set_console_logging(self, enabled: bool) -> None:
```

### Configuration System

#### `opaque.models.annotations`

Type-safe configuration field annotations.

**Field Types:**

```python
class StringField:
    def __init__(
        self,
        default: str = "",
        description: str = "",
        choices: Optional[List[str]] = None
    )

class IntField:
    def __init__(
        self,
        default: int = 0,
        description: str = "",
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    )

class FloatField:
    def __init__(
        self,
        default: float = 0.0,
        description: str = "",
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    )

class BoolField:
    def __init__(
        self,
        default: bool = False,
        description: str = ""
    )

class PathField:
    def __init__(
        self,
        default: str = "",
        description: str = "",
        must_exist: bool = False
    )
```

**Usage Example:**

```python
from opaque.models.annotations import StringField, IntField, BoolField
from opaque.models.configuration import DefaultApplicationConfiguration

class MyConfig(DefaultApplicationConfiguration):
    app_name = StringField(
        default="MyApp",
        description="Application name"
    )
    
    window_width = IntField(
        default=1280,
        description="Main window width",
        min_value=800,
        max_value=3840
    )
    
    debug_mode = BoolField(
        default=False,
        description="Enable debug mode"
    )
```

## Error Handling

### Build Exceptions

The build tools raise specific exceptions for different error conditions:

```python
from opaque.build_tools.exceptions import (
    BuildError,           # General build error
    BuilderNotFoundError, # Builder executable not found
    EntryPointError,      # Invalid entry point
    ConfigurationError    # Invalid configuration
)

try:
    success = build_executable("pyinstaller", "main.py")
except BuilderNotFoundError:
    print("PyInstaller not installed")
except EntryPointError:
    print("Entry point file not found")
except BuildError as e:
    print(f"Build failed: {e}")
```

## Integration Examples

### Custom Build Script

```python
#!/usr/bin/env python3
"""Custom build script using OPAQUE build tools."""

import sys
import logging
from pathlib import Path
from opaque.build_tools.pyinstaller_builder import PyInstallerBuilder
from opaque.build_tools.nuitka_builder import NuitkaBuilder

def build_app(builder_type: str, entry_point: str):
    """Build application with specified builder."""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Common build options
    build_options = {
        "entry_point": entry_point,
        "name": "MyOpaqueApp",
        "onefile": True,
        "icon": "assets/icon.ico",
        "add_data": [("config/", "config/"), ("assets/", "assets/")]
    }
    
    if builder_type == "pyinstaller":
        builder = PyInstallerBuilder(logger)
        success = builder.build(
            windowed=True,
            exclude_modules=["tkinter", "matplotlib"],
            **build_options
        )
    elif builder_type == "nuitka":
        builder = NuitkaBuilder(logger)
        success = builder.build(
            standalone=True,
            disable_console=True,
            enable_plugin=["pyside6"],
            optimization_level=2,
            **build_options
        )
    else:
        logger.error(f"Unknown builder: {builder_type}")
        return False
    
    return success

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: build.py <builder> <entry_point>")
        sys.exit(1)
    
    builder = sys.argv[1]
    entry_point = sys.argv[2]
    
    if build_app(builder, entry_point):
        print("Build completed successfully!")
    else:
        print("Build failed!")
        sys.exit(1)
```

### Framework Integration

```python
"""Example of integrating build tools into a larger application."""

from opaque.view.application import Application
from opaque.build_tools.cli import build_executable
from opaque.services.service import ServiceLocator
import logging

class BuildService:
    """Service for managing application builds."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def build_release(self, entry_point: str, builder: str = "nuitka"):
        """Build optimized release version."""
        
        notification_service = ServiceLocator.get_service("notification")
        
        try:
            notification_service.add_notification(
                "INFO", "Build Started", f"Building with {builder}..."
            )
            
            success = build_executable(
                builder=builder,
                entry_point=entry_point,
                name="MyApp-Release",
                onefile=True,
                windowed=True
            )
            
            if success:
                notification_service.add_notification(
                    "INFO", "Build Complete", "Release build completed successfully!"
                )
            else:
                notification_service.add_notification(
                    "ERROR", "Build Failed", "Release build failed. Check logs."
                )
                
            return success
            
        except Exception as e:
            self.logger.error(f"Build error: {e}")
            notification_service.add_notification(
                "ERROR", "Build Error", f"Build failed with error: {e}"
            )
            return False

# Register the service
ServiceLocator.register_service("build", BuildService())
```

## Best Practices

### 1. Error Handling

Always wrap build operations in try-catch blocks:

```python
from opaque.build_tools.cli import build_executable
from opaque.build_tools.exceptions import BuildError

try:
    success = build_executable("pyinstaller", "main.py")
    if not success:
        print("Build completed with warnings")
except BuildError as e:
    print(f"Build failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### 2. Logging

Use proper logging for build operations:

```python
import logging
from opaque.build_tools.pyinstaller_builder import PyInstallerBuilder

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use logger with builder
builder = PyInstallerBuilder(logger)
```

### 3. Configuration Management

Use configuration objects for complex builds:

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class BuildConfig:
    entry_point: str
    name: str
    builder: str = "pyinstaller"
    onefile: bool = True
    windowed: bool = True
    icon: Optional[str] = None
    data_files: List[tuple] = None
    
    def build(self):
        return build_executable(
            builder=self.builder,
            entry_point=self.entry_point,
            name=self.name,
            onefile=self.onefile,
            windowed=self.windowed,
            icon=self.icon
        )

# Usage
config = BuildConfig(
    entry_point="main.py",
    name="MyApp",
    icon="assets/icon.ico"
)
config.build()
```

This API documentation provides comprehensive information for using the OPAQUE Framework's build tools and core components programmatically.
