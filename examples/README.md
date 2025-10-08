# OPAQUE Framework Examples

This directory contains example applications demonstrating how to use the OPAQUE Framework.

## Basic Example

The `basic_example` directory contains a simple application that demonstrates:
- Creating custom feature windows
- Implementing settings and state models
- Registering features with the application
- Using the framework's MDI capabilities

### Running the Basic Example

1. Make sure you have the required dependencies installed:
   ```bash
   pip install PySide6
   ```

2. Navigate to the example directory:
   ```bash
   cd examples/basic_example
   ```

3. Run the application:
   ```bash
   python main.py
   ```

### Project Structure

```
basic_example/
├── main.py                 # Application entry point
└── features/              # Feature implementations
    ├── data_analysis/     # Data analysis feature
    │   ├── window.py      # Feature window implementation
    │   ├── settings.py    # Settings model
    │   └── state.py       # State model
    └── logging/           # Logging feature
        ├── window.py      # Feature window implementation
        └── settings.py    # Settings model
```

## Creating Your Own Application

To create your own application using the OPAQUE Framework:

1. **Install the framework** (once it's packaged):
   ```bash
   pip install opaque-framework
   # Or install from source:
   pip install -e /path/to/opaque_framework
   ```

2. **Create your feature windows** by extending `BaseFeatureWindow`:
   ```python
   from opaque import BaseFeatureWindow, BaseModel
   
   class MyFeatureWindow(BaseFeatureWindow):
       FEATURE_NAME = "My Feature"
       FEATURE_ICON = "document-open"
       FEATURE_TOOLTIP = "My custom feature"
       DEFAULT_VISIBILITY = True
       
       def __init__(self, feature_id: str, **kwargs):
           super().__init__(feature_id, **kwargs)
           # Initialize your UI here
   ```

3. **Create your application** by extending `BaseApplication`:
   ```python
   from opaque import BaseApplication
   
   class MyApplication(BaseApplication):
       def __init__(self):
           super().__init__()
           self.setWindowTitle("My Application")
           self.init_features()
           
       def init_features(self):
           # Register your feature windows
           feature = MyFeatureWindow(feature_id="my_feature_1")
           self.register_window(feature)
   ```

4. **Run your application**:
   ```python
   if __name__ == "__main__":
       from PySide6.QtWidgets import QApplication
       import sys
       
       QApplication.setApplicationName("MyApp")
       QApplication.setOrganizationName("MyCompany")
       
       app = QApplication(sys.argv)
       main_win = MyApplication()
       main_win.show()
       sys.exit(app.exec())
   ```

## Key Concepts

### Feature Windows
Feature windows are MDI sub-windows that provide specific functionality. They must implement:
- `feature_name()`: Returns the feature's display name
- `feature_icon()`: Returns a QIcon for the toolbar
- `feature_tooltip()`: Returns tooltip text
- `feature_visibility()`: Returns default visibility state
- `feature_settings_model()`: Returns the settings model class (or None)
- `feature_state_model()`: Returns the state model class (or None)

### Settings Models
Settings models persist user preferences across sessions. They should:
- Extend `BaseModel`
- Define fields using field descriptors (BoolField, IntField, etc.)
- Implement `apply_to_ui()` and `extract_from_ui()` methods

### State Models
State models save and restore the workspace state. They should:
- Extend `BaseModel`
- Define fields for state data
- Implement `capture_state()` and `restore_state()` methods

### Workspace Management
The framework automatically handles:
- Saving
