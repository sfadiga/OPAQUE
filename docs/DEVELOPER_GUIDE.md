# OPAQUE Framework - Developer Guide

This guide provides step-by-step instructions for creating applications with the OPAQUE Framework.

## 🚀 Bootstrapping an Application

Follow these steps to create a new OPAQUE application from scratch.

### 1. Create the File Structure

Start by creating a directory for your project:

```bash
mkdir my_opaque_app
cd my_opaque_app
touch main.py
```

### 2. Define Configuration

In `main.py`, define your application's configuration by inheriting from `DefaultApplicationConfiguration`. This handles application metadata and default settings.

```python
from opaque.models.configuration import DefaultApplicationConfiguration
from opaque.models.annotations import StringField, IntField
from PySide6.QtGui import QIcon

class MyAppConfig(DefaultApplicationConfiguration):
    # Application Metadata
    app_name = StringField(default="MyOpaqueApp")
    app_title = StringField(default="My Awesome OPAQUE Application")
    app_version = StringField(default="1.0.0")
    
    # Custom Settings (optional)
    # These will be automatically persisted to settings.json
    default_user = StringField(default="User")
    
    # Required implementation of abstract methods
    def get_application_name(self) -> str:
        return str(self.app_name)
    
    def get_application_title(self) -> str:
        return str(self.app_title)
        
    def get_application_organization(self) -> str:
        return "My Company"
        
    def get_application_description(self) -> str:
        return "An application built with OPAQUE Framework"
        
    def get_application_icon(self) -> QIcon:
        return QIcon()
```

### 3. Create the Application Class

Inherit from `BaseApplication` to get the MDI interface, service integration, and lifecycle management.

```python
from opaque.view.application import BaseApplication

class MyApplication(BaseApplication):
    def __init__(self):
        # Initialize with your configuration
        super().__init__(MyAppConfig())
        
        # Register features here (see next section)
        self.register_features()
        
    def register_features(self):
        # We will add features here later
        pass
```

### 4. Entry Point

Add the standard Python entry point to run the `QApplication`.

```python
import sys
from PySide6.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = MyApplication()
    
    # Single instance check
    if not window.try_acquire_lock():
        window.show_already_running_message()
        sys.exit(1)
        
    window.show()
    sys.exit(app.exec())
```

Run your app: `python main.py`. You should see the main window with a toolbar.

---

## 🧩 Adding Features (MVP Pattern)

OPAQUE uses the **Model-View-Presenter (MVP)** pattern. Each "feature" (like a calculator, log viewer, or custom tool) consists of three classes.

### 1. Create the Model (`model.py`)

The Model defines data, configuration, and feature metadata.

```python
from opaque.models.model import BaseModel
from PySide6.QtGui import QIcon

class MyFeatureModel(BaseModel):
    def feature_name(self) -> str:
        return "My Feature"
        
    def feature_icon(self) -> QIcon:
        # Return a QIcon here (e.g., from resources or theme)
        return QIcon() 
        
    def feature_description(self) -> str:
        return "A description of my feature"
        
    # Add business logic data here
    # properties, methods, etc.
```

### 2. Create the View (`view.py`)

The View defines the UI. Inherit from `BaseView`.

```python
from opaque.view.view import BaseView
from PySide6.QtWidgets import QLabel, QVBoxLayout, QPushButton

class MyFeatureView(BaseView):
    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add widgets
        self.label = QLabel("Welcome to My Feature")
        self.button = QPushButton("Click Me")
        
        layout.addWidget(self.label)
        layout.addWidget(self.button)
        
        # Set the layout to a container widget
        from PySide6.QtWidgets import QWidget
        container = QWidget()
        container.setLayout(layout)
        self.setWidget(container)
        
    def update_label(self, text):
        self.label.setText(text)
```

### 3. Create the Presenter (`presenter.py`)

The Presenter connects the Model and View.

```python
from opaque.presenters.presenter import BasePresenter

class MyFeaturePresenter(BasePresenter):
    def __init__(self, model, view, app):
        super().__init__(model, view, app)
        
    def bind_events(self):
        # Connect View signals to Presenter methods
        self.view.button.clicked.connect(self.on_button_clicked)
        
    def on_button_clicked(self):
        self.app.notification_presenter.notify_info("Clicked!", "You clicked the button.")
        self.view.update_label("Button Clicked!")
        
    def update(self, field_name, new_value, old_value=None, model=None):
        # Handle model changes if any
        pass
        
    def on_view_show(self):
        pass
        
    def on_view_close(self):
        pass
```

### 4. Register the Feature

Update `MyApplication.register_features` in `main.py`:

```python
    def register_features(self):
        from my_feature.model import MyFeatureModel
        from my_feature.view import MyFeatureView
        from my_feature.presenter import MyFeaturePresenter
        
        model = MyFeatureModel(self)
        view = MyFeatureView(self)
        presenter = MyFeaturePresenter(model, view, self)
        
        self.register_feature(presenter)
```

---

## 🛠️ Using Built-in Services

### Notifications (Toasts)

Use `self.app.notification_presenter` (available in Presenters) to show toast notifications.

```python
# Info
self.app.notification_presenter.notify_info("Title", "Message")

# Warning
self.app.notification_presenter.notify_warning("Warning", "Something confusing happened")

# Error (Shows toast + persists in list)
self.app.notification_presenter.notify_error("Error", "Operation failed")
```

### Console System

To add the developer console to your app:

```python
from opaque.presenters.console_presenter import ConsolePresenter
from opaque.models.console_model import ConsoleModel

# In register_features:
console_model = ConsoleModel(self)
console_presenter = ConsolePresenter(console_model, self)
self.register_feature(console_presenter)
console_presenter.initialize() # Starts capturing stdout/stderr
```

Now, any `print()` or exception tracebacks will appear in the Console window.

### Logging

Use the global logging service via `ServiceLocator` or `notification_presenter` helpers.

```python
# Helper method in Presenter
self.app.notification_presenter.log_info("Application started", "Main")

# Or via ServiceLocator
from opaque.services.service import ServiceLocator
logger = ServiceLocator.get_service("logger")
if logger:
    logger.info("Message", "Source")
```

### Tab Manager (CloseableTabWidget)

The `CloseableTabWidget` is a powerful widget for tabbed interfaces.

**In your View:**
```python
from opaque.view.widgets import CloseableTabWidget

self.tabs = CloseableTabWidget(
    widget_type=MyContentWidget,  # Widget class to create for new tabs
    default_tab_name="Document",
    show_plus_tab=True
)
layout.addWidget(self.tabs)
```

**In your Presenter:**
```python
# Handle tab events
self.view.tabs.tabAdded.connect(self.on_tab_added)
```

## 💾 Persistence

### Application Settings

Fields defined in your Configuration class (using `StringField`, `IntField`, etc.) are automatically saved to disk when the application closes and loaded on startup.

### Workspace State

To save the state of your feature windows (size, position, content):

1.  Override `save_workspace` in your **Presenter**:
    ```python
    def save_workspace(self, workspace_object: dict) -> None:
        super().save_workspace(workspace_object) # Saves window geometry
        # Save custom data
        workspace_object[self.feature_id]["my_data"] = "some value"
    ```

2.  Override `load_workspace` in your **Presenter**:
    ```python
    def load_workspace(self, workspace_object: dict) -> None:
        super().load_workspace(workspace_object) # Restores window geometry
        if self.feature_id in workspace_object:
            data = workspace_object[self.feature_id]
            # Restore custom data
            if "my_data" in data:
                self.restore_data(data["my_data"])
