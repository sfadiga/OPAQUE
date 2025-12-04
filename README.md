# OPAQUE Framework

**OPAQUE** - *Opinionated Python Application with Qt UI for Engineering*

A flexible, modern MDI (Multiple Document Interface) application framework built on PySide6, designed for creating professional desktop applications with enterprise-grade features.

![OPAQUE Framework Screenshot](resources/showcase.gif)

## 🚀 Key Features

*   **MVP Architecture**: Clean separation of concerns (Model-View-Presenter).
*   **MDI Interface**: Manage multiple feature windows within a single application.
*   **Built-in Services**:
    *   **Notification System**: Non-intrusive toast notifications and a centralized notification center.
    *   **Console System**: Real-time capture and display of stdout/stderr for debugging.
    *   **Logging**: Structured logging with file and console output.
    *   **Settings & Persistence**: Automatic saving/loading of application settings and window states.
    *   **Theme Support**: Dark/Light mode support.
*   **Professional Widgets**: `CloseableTabWidget`, `ColorPicker`, and more.
*   **Build System**: Tools to package your app as a standalone executable (PyInstaller/Nuitka).

## 📦 Installation

```bash
pip install opaque-framework
```

For development:
```bash
pip install "opaque-framework[dev]"
```

## 🏁 Quick Start

### 1. Bootstrap Your Application

Create a `main.py` file:

```python
import sys
from PySide6.QtWidgets import QApplication
from opaque.view.application import BaseApplication
from opaque.models.configuration import DefaultApplicationConfiguration
from opaque.models.annotations import StringField

# 1. Define Configuration
class MyAppConfig(DefaultApplicationConfiguration):
    app_name = StringField(default="MyApp")
    app_title = StringField(default="My OPAQUE App")

# 2. Define Application
class MyApplication(BaseApplication):
    def __init__(self):
        super().__init__(MyAppConfig())
        # Register features here (see documentation)

# 3. Run
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApplication()
    if window.try_acquire_lock():
        window.show()
        sys.exit(app.exec())
```

### 2. Add a Feature (MVP)

Create a simple feature (e.g., `MyFeature`):

```python
from opaque.models.model import BaseModel
from opaque.view.view import BaseView
from opaque.presenters.presenter import BasePresenter
from PySide6.QtWidgets import QLabel, QVBoxLayout

# Model
class MyModel(BaseModel):
    def feature_name(self): return "My Feature"
    def feature_icon(self): return None 

# View
class MyView(BaseView):
    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Hello OPAQUE!"))
        self.setLayout(layout)

# Presenter
class MyPresenter(BasePresenter):
    pass # Add logic here

# In MyApplication.__init__:
self.register_feature(MyPresenter(MyModel(self), MyView(self), self))
```

## 📚 Documentation

*   [**Developer Guide**](docs/DEVELOPER_GUIDE.md): Detailed guide on bootstrapping, adding features, and using services like the Console.
*   [**Build Guide**](docs/BUILD_GUIDE.md): How to create standalone executables.
*   [**API Reference**](docs/API.md): Class and method reference.
*   [**Version Management**](docs/VERSION_MANAGEMENT.md): Handling application versions.

## 📂 Examples

Check the `examples/` directory in the repository for complete working examples:
*   `basic_example`: Full showcase of MVP, Logging, Console, and Tabs.
*   `notification_example`: Demonstrates the notification system.
*   `closeable_tab_example`: Using the advanced Tab widget.

## 🤝 Contributing

Contributions are welcome! Please see the [Issues](https://github.com/sfadiga/OPAQUE/issues) page.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
