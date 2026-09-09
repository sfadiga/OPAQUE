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

Create a `main.py`. This is `examples/quickstart/main.py`; the test suite builds it on every run, so it cannot go stale.

<!-- quickstart:begin -->
```python
# This Python file uses the following encoding: utf-8
"""
The smallest OPAQUE application that runs.

This file is the README quick start. tests/test_quickstart.py proves the two
are identical and builds this window headless, so the first thing a user
copies cannot be broken.
"""
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from opaque import (
    BaseApplication,
    BaseModel,
    BasePresenter,
    BaseView,
    DefaultApplicationConfiguration,
)


class QuickStartConfiguration(DefaultApplicationConfiguration):
    """The five accessors below are abstract. Every application must write them."""

    def get_application_name(self) -> str:
        return "QuickStart"

    def get_application_title(self) -> str:
        return "OPAQUE Quick Start"

    def get_application_description(self) -> str:
        return "The smallest OPAQUE application."

    def get_application_organization(self) -> str:
        return "My Company"

    def get_application_icon(self) -> QIcon:
        return QIcon()


class GreetingModel(BaseModel):
    """A feature model. feature_name() is the text the toolbar shows."""

    FEATURE_ID = "greeting"

    def feature_name(self) -> str:
        return "Greeting"

    def feature_icon(self) -> QIcon:
        return QIcon()

    def feature_description(self) -> str:
        return "Says hello."


class GreetingView(BaseView):
    """A feature view is one MDI sub-window. Build the UI before the presenter exists."""

    def __init__(self, app, parent=None) -> None:
        super().__init__(app, parent)
        self.label = QLabel(self.tr("Hello OPAQUE"))
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self.label)
        self.setWidget(content)


class GreetingPresenter(BasePresenter):
    """
    bind_events(), update() and on_view_show() are abstract on BasePresenter.
    A subclass that leaves one out cannot be instantiated. on_view_close() is
    a plain hook with a working default; override it only to save state, and
    never call super() or cleanup() from it.
    """

    def bind_events(self) -> None:
        pass

    def update(self, field_name, new_value, old_value=None, model=None) -> None:
        pass

    def on_view_show(self) -> None:
        pass


class QuickStartApplication(BaseApplication):
    """
    The registration order is fixed: model, then view, then presenter, then
    register_feature. Each of the three takes the application object.
    """

    def __init__(self) -> None:
        super().__init__(QuickStartConfiguration())
        model = GreetingModel(self)
        view = GreetingView(self)
        self.register_feature(GreetingPresenter(model, view, self))


if __name__ == "__main__":
    qt_application = QApplication(sys.argv)
    window = QuickStartApplication()
    if not window.try_acquire_lock():
        window.show_already_running_message()
        sys.exit(1)
    window.show()
    sys.exit(qt_application.exec())
```
<!-- quickstart:end -->

Run it:

```bash
uv run python examples/quickstart/main.py
```

### What the framework demands of you

| You write | The framework needs |
|---|---|
| A configuration | The five `get_application_*` accessors. They are abstract; field declarations do not satisfy them. |
| A model | `FEATURE_ID`, `feature_name()`, `feature_icon()`, `feature_description()`. |
| A view | A widget tree, built in `__init__`, handed to `setWidget()`. |
| A presenter | `bind_events()`, `update()`, `on_view_show()`. All three are abstract. `on_view_close()` has a working default; override it only to save state. |
| Registration | Model, then view, then presenter, then `register_feature(presenter)`. In that order. |

Two traps that cost an hour each:

- `BasePresenter.__init__` calls `bind_events()` at its end. An attribute your subclass creates *after* `super().__init__(...)` does not exist yet inside `bind_events()`. Create it before the `super()` call, or connect it in `on_view_show()`. Getting it wrong raises an `AttributeError` that states this rule.
- `on_view_close()` is a plain hook. Override it to save state; do not call `super()` and do not call `cleanup()`. `BasePresenter._handle_view_closed()` owns the order and calls `cleanup()` straight after the hook returns.

## 📚 Documentation

*   [**Quick Reference**](docs/QUICK_REFERENCE.md): The contract on one page. Every name is checked by the test suite.
*   [**Developer Guide**](docs/DEVELOPER_GUIDE.md): Bootstrapping, features, and the built-in services.
*   [**Build Guide**](docs/BUILD_GUIDE.md): How to create standalone executables.
*   [**Version Management**](docs/VERSION_MANAGEMENT.md): Handling application versions.
*   [**Engineering Review**](docs/ENGINEERING_REVIEW.md): The current known-defect list.

## 📂 Examples

*   `examples/quickstart`: The smallest application that runs. The suite builds it on every run.
*   `examples/basic_example`: Full showcase of MVP, logging, console, tabs, and notifications.

## 🤝 Contributing

Contributions are welcome! Please see the [Issues](https://github.com/sfadiga/OPAQUE/issues) page.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
