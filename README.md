# OPAQUE Framework

**OPAQUE** - **O**pinionated **P**ython **A**pplication with **Q**t **U**I for **E**ngineering

An opinionated PySide6-based MDI application framework designed to accelerate the development of professional desktop applications. 

![OPAQUE Framework Screenshot](resources/example.gif)

## Features

- 🪟 **MDI Window Management** - Multiple Document Interface with dockable windows
- 🎨 **Theme Management** - 40+ themes including qt-material, qt-themes, and QDarkStyle
- 💾 **Persistence Layer** - Automatic saving/loading of settings and workspace state
- 🌍 **Internationalization** - Built-in i18n support with language selection
- ⚙️ **Global Settings** - Extensible application-wide settings with preview
- 🔍 **Enhanced Settings Search** - Search through both group names and individual settings
- 📦 **State Management** - Save and restore complete workspace states

## Quick Start

### Installation

```bash
# Install from PyPI (once published)
pip install opaque-framework

# With additional themes
pip install opaque-framework[themes]

# For development
pip install opaque-framework[dev]

# Install from source (development)
git clone https://github.com/yourusername/opaque-framework.git
cd opaque-framework
pip install -e .
```

## Project Structure

```
OPAQUE/
├── src/
│   └── opaque/
│       ├── core/
│       │   ├── application.py
│       │   ├── model.py
│       │   ├── view.py
│       │   └── presenter.py
│       ├── managers/
│       │   ├── settings_manager.py
│       │   ├── theme_manager.py
│       │   └── workspace_manager.py
│       ├── models/
│       │   ├── annotations.py
│       │   └── ...
│       └── widgets/
│           ├── dialogs/
│           │   └── settings.py
│           └── mdi_window.py
├── examples/
│   └── basic_example/
├── resources/
├── pyproject.toml
└── LICENSE
```

## Key Concepts

### The MVP Architecture
OPAQUE is built on the Model-View-Presenter (MVP) pattern, which separates application logic from the user interface. This promotes a clean, maintainable, and testable codebase.

- **Model (`BaseModel`)**: Represents the application's data and business logic. It is completely independent of the UI and notifies the Presenter of any changes to its state.

- **View (`BaseView`)**: The user interface component. It is responsible for displaying data from the Model and routing user input to the Presenter. The View is passive and does not contain any application logic.

- **Presenter (`BasePresenter`)**: Acts as the bridge between the Model and the View. It retrieves data from the Model, formats it for display, and updates the View. It also handles user input from the View and updates the Model accordingly.

### Features
In OPAQUE, a "feature" is a self-contained unit of functionality implemented using the MVP pattern. Each feature consists of a Model, a View, and a Presenter. Features are registered with the main application and automatically integrated into the UI, appearing as buttons in the main toolbar.

### Global Settings
OPAQUE provides a clean global settings system for application-wide configuration:
- **Built-in settings**: 
  - Theme selection (40+ themes from qt-material, qt-themes, QDarkStyle)
  - UI language (7 languages: en_US, es_ES, fr_FR, de_DE, pt_BR, ja_JP, zh_CN)
- **Extensible**: Add your own global settings by extending `GlobalSettings`
- **Apply button**: Preview changes before committing with confirmation dialog
- **Automatic persistence**: Saved and loaded like feature settings
- **Theme-aware toolbar**: Button highlighting adapts to current theme

### Settings Dialog
The enhanced settings dialog provides:
- **Smart Search**: Search through both group names and individual setting labels
- **Visual Highlighting**: Matching settings are highlighted in bold with accent color
- **Auto-Selection**: First matching group is automatically selected when searching
- **Apply & Preview**: Test global settings before committing changes

```python
from opaque import GlobalSettings, BoolField, IntField, StringField, ChoiceField

class MyGlobalSettings(GlobalSettings):
    # Inherits theme and language, adds custom settings
    auto_save = BoolField(default=True, description="Enable auto-save")
    auto_save_interval = IntField(default=5, min_value=1, max_value=60)

class MyApp(BaseApplication):
    def global_settings_model(self):
        return MyGlobalSettings  # Use custom global settings
```

### Settings Models
OPAQUE provides a declarative way to define settings with field descriptors:
```python
from opaque.models.annotations import BaseModel, BoolField, IntField, StringField, FloatField, ChoiceField

class MyFeatureSettings(BaseModel):
    # Boolean field with description (searchable in settings dialog)
    auto_refresh = BoolField(default=True, description="Auto refresh")
    
    # Integer field with min/max constraints
    interval = IntField(default=60, min_value=1, max_value=3600, description="Refresh interval (seconds)")
    
    # String field for text input
    output_path = StringField(default="./output", description="Output directory")
    
    # Float field for decimal values
    zoom_level = FloatField(default=1.0, min_value=0.1, max_value=5.0, description="Zoom level")
    
    # Choice field for dropdown selection
    theme_variant = ChoiceField(
        default="auto",
        choices=["auto", "light", "dark"],
        description="Theme variant"
    )
```

**Note**: The `description` parameter is used by the settings dialog's search feature to help users find settings quickly.

### State Management
Save and restore complete workspace states including:
- Window positions and sizes
- Feature-specific state data
- Application settings (both global and feature-specific)
- Active workspace configuration

## Step-by-Step Guide: Creating a Feature

This guide walks you through creating a "Calculator" feature using the MVP pattern.

### Step 1: Create the Feature Directory Structure

```
my_app/
├── features/
│   └── calculator/
│       ├── __init__.py
│       ├── model.py
│       ├── view.py
│       └── presenter.py
└── main.py
```

### Step 2: Define the Model

Create `features/calculator/model.py`:

```python
from PySide6.QtGui import QIcon
from opaque.core.model import BaseModel
from opaque.models.annotations import FloatField

class CalculatorModel(BaseModel):
    num1 = FloatField(default=0.0)
    num2 = FloatField(default=0.0)
    result = FloatField(default=0.0)

    def feature_name(self) -> str:
        return "Calculator"

    def feature_icon(self) -> QIcon:
        return QIcon.fromTheme("accessories-calculator")

    def feature_description(self) -> str:
        return "A simple calculator feature."

    def feature_modal(self) -> bool:
        return False

    def add(self):
        self.result = self.num1 + self.num2

    def subtract(self):
        self.result = self.num1 - self.num2
```

### Step 3: Create the View

Create `features/calculator/view.py`:

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel
from opaque.core.view import BaseView

class CalculatorView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calculator")
        self._setup_ui()

    def _setup_ui(self):
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)

        self.num1_input = QLineEdit()
        self.num2_input = QLineEdit()
        self.add_button = QPushButton("Add")
        self.subtract_button = QPushButton("Subtract")
        self.result_label = QLabel("Result: 0.0")

        layout.addWidget(QLabel("Number 1:"))
        layout.addWidget(self.num1_input)
        layout.addWidget(QLabel("Number 2:"))
        layout.addWidget(self.num2_input)
        layout.addWidget(self.add_button)
        layout.addWidget(self.subtract_button)
        layout.addWidget(self.result_label)

        self.set_content(main_widget)
```

### Step 4: Create the Presenter

Create `features/calculator/presenter.py`:

```python
from opaque.core.presenter import BasePresenter
from .model import CalculatorModel
from .view import CalculatorView

class CalculatorPresenter(BasePresenter):
    def __init__(self, model: CalculatorModel, view: CalculatorView):
        super().__init__(model, view)

    def bind_events(self):
        self.view.add_button.clicked.connect(self.on_add)
        self.view.subtract_button.clicked.connect(self.on_subtract)
        self.view.num1_input.textChanged.connect(self.on_num1_changed)
        self.view.num2_input.textChanged.connect(self.on_num2_changed)

    def on_add(self):
        self.model.add()

    def on_subtract(self):
        self.model.subtract()

    def on_num1_changed(self, text: str):
        try:
            self.model.num1 = float(text)
        except ValueError:
            self.model.num1 = 0.0

    def on_num2_changed(self, text: str):
        try:
            self.model.num2 = float(text)
        except ValueError:
            self.model.num2 = 0.0

    def update(self, property_name: str, value: any):
        if property_name == "result":
            self.view.result_label.setText(f"Result: {value}")
```

### Step 5: Register the Feature in Your Application

Create `main.py`:

```python
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from opaque.core.application import BaseApplication
from features.calculator.model import CalculatorModel
from features.calculator.view import CalculatorView
from features.calculator.presenter import CalculatorPresenter

class MyApplication(BaseApplication):
    def application_name(self) -> str:
        return "MyCalculatorApp"

    def organization_name(self) -> str:
        return "MyCompany"

    def application_title(self) -> str:
        return "My Calculator App"

    def application_description(self) -> str:
        return "A simple calculator app."

    def application_icon(self) -> QIcon:
        return QIcon.fromTheme("accessories-calculator")

    def register_features(self):
        calc_model = CalculatorModel()
        calc_view = CalculatorView()
        calc_presenter = CalculatorPresenter(model=calc_model, view=calc_view)
        self.register_feature(calc_presenter)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MyApplication()
    main_window.register_features()
    main_window.show()
    sys.exit(app.exec())
```

### Step 6: Run Your Application

```bash
python main.py
```

## What You Get Automatically

When you follow this guide, OPAQUE automatically provides:

✅ **Toolbar Integration**: Your feature appears as a button in the main toolbar.
✅ **MDI Management**: Your feature's window can be docked, tabbed, and floated.
✅ **Settings Persistence**: If your model includes fields for settings, they are automatically saved and loaded.
✅ **Workspace Management**: The state of your feature can be saved and restored as part of a workspace.
✅ **Theme Support**: Your feature's UI automatically adapts to the selected theme.

## Advanced Features

### Custom Field Types

Create custom field descriptors for specialized data:

```python
from opaque.models.annotations import Field

class ColorField(Field):
    """Custom field for color values"""
    
    def __init__(self, default="#000000", **kwargs):
        super().__init__(default=default, **kwargs)
    
    def validate(self, value):
        if not isinstance(value, str) or not value.startswith("#"):
            raise ValueError("Color must be a hex string")
        return value
```

### Multiple Feature Instances

Register multiple instances of the same feature by creating separate MVP triads:

```python
def register_features(self):
    for i in range(3):
        model = CalculatorModel()
        model.num1 = i * 10
        view = CalculatorView()
        presenter = CalculatorPresenter(model=model, view=view)
        self.register_feature(presenter)
```

### Dynamic Feature Loading

Load features based on a configuration file or other dynamic sources:

```python
def register_features(self):
    import json
    with open("features.json") as f:
        feature_config = json.load(f)
    
    for feature_name in feature_config["enabled_features"]:
        if feature_name == "calculator":
            model = CalculatorModel()
            view = CalculatorView()
            presenter = CalculatorPresenter(model=model, view=view)
            self.register_feature(presenter)
        # Add other features here
```

## Tips and Best Practices

1.  **Separation of Concerns**: Keep logic in the Presenter, data in the Model, and UI code in the View.
2.  **Model Independence**: The Model should not have any knowledge of the View or Presenter.
3.  **View Passivity**: The View should be as "dumb" as possible, only displaying data and emitting signals on user interaction.
4.  **Field Annotations**: Use the `@Field` annotation in your models to define properties that should be automatically handled by the settings and persistence layers.
5.  **Translations**: Use `self.tr()` for all user-visible strings to support internationalization.
6.  **Icons**: Use theme icons (e.g., `QIcon.fromTheme("document-open")`) for better integration across different themes.
7.  **Error Handling**: Implement robust error handling in your Presenter and Model to ensure a stable application.
8.  **PySide6 Only**: The framework is designed specifically for PySide6 and is not compatible with PyQt.

## Examples

Check the `examples/` directory for complete working examples:
- **basic_example** - Demonstrates data analysis and logging features with settings and state management
- **custom_global_settings_example** - Shows how to extend global settings with custom fields

To run examples:
```bash
# Basic example
python examples/basic_example/main.py

# Custom global settings example
python examples/custom_global_settings_example.py
```

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

MIT License - See LICENSE file for details

## Support

For questions and support, please open an issue on GitHub or contact the maintainers.

## Theme Support

OPAQUE includes 40+ professional themes from multiple sources:

- **qt-material** (20+ themes): Material design themes with various color schemes
- **qt-themes** (15 themes): Modern themes including Catppuccin, Dracula, Nord, Github, and more
- **QDarkStyle**: Professional dark and light themes
- **Default**: System native theme

The toolbar automatically adapts its button highlighting to match the current theme's accent color.

## Requirements

- Python 3.8+
- PySide6 >= 6.0.0
- qt-material >= 2.14
- QDarkStyle >= 3.2.0
- qt-themes >= 1.0.0 (optional, for additional themes)

## Package Information

- **Package Name**: `opaque-framework`
- **Version**: 1.0.0
- **License**: MIT
- **PyPI**: https://pypi.org/project/opaque-framework/ (once published)

---

Built with ❤️ (and a LOT of AI help) using PySide6 and Python
