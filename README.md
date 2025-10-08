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

### Basic Usage

```python
from opaque import BaseApplication, BaseFeatureWindow
from PySide6.QtWidgets import QApplication
import sys

class MyFeatureWindow(BaseFeatureWindow):
    def feature_name(self) -> str:
        return "My Feature"
    
    def feature_icon(self):
        return QIcon.fromTheme("document-open")
    
    def feature_tooltip(self) -> str:
        return "My custom feature window"
    
    def feature_visibility(self) -> bool:
        return True
    
    def feature_settings_model(self):
        return None  # Or return your settings model class
    
    def feature_state_model(self):
        return None  # Or return your state model class
    
    def __init__(self, feature_id: str, **kwargs):
        super().__init__(feature_id, **kwargs)
        # Add your UI components here

class MyApplication(BaseApplication):
    def application_name(self) -> str:
        return "MyApp"
    
    def organization_name(self) -> str:
        return "MyCompany"
    
    def application_title(self) -> str:
        return "My OPAQUE Application"
    
    def register_features(self):
        feature = MyFeatureWindow(feature_id="my_feature_1")
        self.register_window(feature)

if __name__ == "__main__":
    # The framework automatically handles QApplication setup
    app = QApplication(sys.argv)
    main_win = MyApplication()
    main_win.show()
    sys.exit(app.exec())
```

## Project Structure

```
opaque_framework/
├── src/
│   └── opaque/              # Framework package
│       ├── ui/              # UI components
│       │   ├── core/        # Core windows and widgets
│       │   ├── dialogs/     # Dialog implementations
│       │   └── layouts/     # Custom layouts
│       ├── models/          # Data models
│       │   └── base/        # Base model and field descriptors
│       ├── persistence/     # Persistence layer
│       │   └── managers/    # Settings and workspace managers
│       ├── managers/        # Application managers
│       └── settings/        # Settings implementations
├── examples/
│   └── basic_example/       # Example application
├── pyproject.toml           # Package configuration
├── MANIFEST.in              # Package manifest
└── LICENSE                  # MIT License
```

## Key Concepts

### Feature Windows
Feature windows are the building blocks of your application. Each window:
- Extends `BaseFeatureWindow`
- Implements required methods for integration
- Can have associated settings and state models
- Automatically integrates with the toolbar and MDI area

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
from opaque import BaseModel, BoolField, IntField, StringField, FloatField, ChoiceField

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

This guide walks you through creating a complete feature for your OPAQUE application. We'll build a "Text Editor" feature with settings persistence and state management.

### Step 1: Create the Feature Directory Structure

```
my_app/
├── features/
│   └── text_editor/
│       ├── __init__.py
│       ├── window.py       # Feature window implementation
│       ├── settings.py     # Settings model (optional)
│       └── state.py        # State model (optional)
└── main.py
```

### Step 2: Define the Settings Model (optional)

Create `features/text_editor/settings.py`:

```python
from opaque import BaseModel, BoolField, IntField, StringField

class TextEditorSettings(BaseModel):
    """Settings for the Text Editor feature"""
    
    # Define your settings fields
    word_wrap = BoolField(default=True, label="Word Wrap")
    font_size = IntField(default=12, min_value=8, max_value=72, label="Font Size")
    font_family = StringField(default="Consolas", label="Font Family")
    auto_save = BoolField(default=False, label="Auto Save")
    
    def apply_to_ui(self, window):
        """Apply settings to the UI when loaded"""
        if hasattr(window, 'text_edit'):
            window.text_edit.setWordWrapMode(
                Qt.TextWrapMode.WrapAtWordBoundaryOrAnywhere if self.word_wrap 
                else Qt.TextWrapMode.NoWrap
            )
            font = window.text_edit.font()
            font.setPointSize(self.font_size)
            font.setFamily(self.font_family)
            window.text_edit.setFont(font)
    
    def extract_from_ui(self, window):
        """Extract current UI state to settings before saving"""
        if hasattr(window, 'text_edit'):
            self.word_wrap = window.text_edit.wordWrapMode() != Qt.TextWrapMode.NoWrap
            font = window.text_edit.font()
            self.font_size = font.pointSize()
            self.font_family = font.family()
```

### Step 3: Define the State Model (optional)

Create `features/text_editor/state.py`:

```python
from opaque import BaseModel, StringField, IntField

class TextEditorState(BaseModel):
    """State for the Text Editor feature"""
    
    # Define state fields
    content = StringField(default="", label="Content")
    cursor_position = IntField(default=0, label="Cursor Position")
    file_path = StringField(default="", label="File Path")
    
    def capture_state(self, window):
        """Capture current state from the window"""
        if hasattr(window, 'text_edit'):
            self.content = window.text_edit.toPlainText()
            self.cursor_position = window.text_edit.textCursor().position()
            self.file_path = getattr(window, 'current_file', "")
    
    def restore_state(self, window):
        """Restore state to the window"""
        if hasattr(window, 'text_edit'):
            window.text_edit.setPlainText(self.content)
            cursor = window.text_edit.textCursor()
            cursor.setPosition(min(self.cursor_position, len(self.content)))
            window.text_edit.setTextCursor(cursor)
            window.current_file = self.file_path
```

### Step 4: Create the Feature Window

Create `features/text_editor/window.py`:

```python
from typing import Optional, Type
from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget, QToolBar, QFileDialog
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt
from opaque import BaseFeatureWindow, BaseModel

from .settings import TextEditorSettings
from .state import TextEditorState

class TextEditorWindow(BaseFeatureWindow):
    """A text editor feature window"""
    
    # Feature metadata
    FEATURE_NAME = "Text Editor"
    FEATURE_ICON = "accessories-text-editor"  # Standard icon name
    FEATURE_TOOLTIP = "Edit text files"
    DEFAULT_VISIBILITY = True
    
    def __init__(self, feature_id: str, **kwargs):
        super().__init__(feature_id, **kwargs)
        self.setWindowTitle(self.tr("Text Editor"))
        self.current_file = ""
        
        # Create the UI
        self._setup_ui()
        
        # Load settings if they exist
        if self.settings:
            self._load_settings()
    
    def _setup_ui(self):
        """Set up the user interface"""
        # Create main widget and layout
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        
        # Create toolbar
        toolbar = QToolBar()
        
        # Add actions
        open_action = QAction(QIcon.fromTheme("document-open"), "Open", self)
        open_action.triggered.connect(self._open_file)
        toolbar.addAction(open_action)
        
        save_action = QAction(QIcon.fromTheme("document-save"), "Save", self)
        save_action.triggered.connect(self._save_file)
        toolbar.addAction(save_action)
        
        layout.addWidget(toolbar)
        
        # Create text editor
        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)
        
        # Set the widget
        self.setWidget(main_widget)
    
    def _open_file(self):
        """Open a file dialog and load selected file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Text Files (*.txt);;All Files (*.*)"
        )
        if file_path:
            with open(file_path, 'r') as f:
                self.text_edit.setPlainText(f.read())
            self.current_file = file_path
            self.setWindowTitle(f"Text Editor - {file_path}")
    
    def _save_file(self):
        """Save the current file"""
        if not self.current_file:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save File", "", "Text Files (*.txt);;All Files (*.*)"
            )
            if file_path:
                self.current_file = file_path
        
        if self.current_file:
            with open(self.current_file, 'w') as f:
                f.write(self.text_edit.toPlainText())
            self.setWindowTitle(f"Text Editor - {self.current_file}")
    
    # Required method implementations
    def feature_name(self) -> str:
        return self.FEATURE_NAME
    
    def feature_icon(self) -> QIcon:
        return QIcon.fromTheme(self.FEATURE_ICON)
    
    def feature_tooltip(self) -> str:
        return self.FEATURE_TOOLTIP
    
    def feature_visibility(self) -> bool:
        return self.DEFAULT_VISIBILITY
    
    def feature_settings_model(self) -> Optional[Type[BaseModel]]:
        return TextEditorSettings
    
    def feature_state_model(self) -> Optional[Type[BaseModel]]:
        return TextEditorState
```

### Step 5: Register the Feature in Your Application

Create `main.py`:

```python
from PySide6.QtWidgets import QApplication
from opaque import BaseApplication
import sys

from features.text_editor.window import TextEditorWindow

class MyApplication(BaseApplication):
    """Main application class"""
    
    def application_name(self) -> str:
        """Return the application name for settings persistence."""
        return "MyTextEditorApp"
    
    def organization_name(self) -> str:
        """Return the organization name for settings persistence."""
        return "MyCompany"
    
    def application_title(self) -> str:
        """Return the main window title."""
        return "My Text Editor App"
    
    def register_features(self):
        """Register all features for this application."""
        # Create and register the text editor feature
        text_editor = TextEditorWindow(feature_id="text_editor_1")
        self.register_window(text_editor)
        
        # Add more features as needed
        # another_feature = AnotherFeatureWindow(feature_id="feature_2")
        # self.register_window(another_feature)

if __name__ == "__main__":
    # The framework automatically handles QApplication setup
    app = QApplication(sys.argv)
    main_window = MyApplication()
    main_window.show()
    sys.exit(app.exec())
```

### Step 6: Run Your Application

```bash
python main.py
```

## What You Get Automatically

When you follow this guide, OPAQUE automatically provides:

✅ **Toolbar Integration** - Your feature appears as a button in the main toolbar  
✅ **MDI Management** - Your window can be minimized, maximized, and arranged  
✅ **Settings Dialog** - Your settings appear in the application settings dialog  
✅ **Settings Persistence** - Settings are saved/loaded automatically  
✅ **Workspace Support** - Save/load complete workspace states  
✅ **Theme Support** - Your feature inherits the application theme  
✅ **Window State** - Window positions and sizes are remembered  

## Advanced Features

### Custom Field Types

Create custom field descriptors for specialized data:

```python
from opaque.models.base.field_descriptors import FieldDescriptor

class ColorField(FieldDescriptor):
    """Custom field for color values"""
    
    def __init__(self, default="#000000", **kwargs):
        super().__init__(default=default, **kwargs)
    
    def validate(self, value):
        if not isinstance(value, str) or not value.startswith("#"):
            raise ValueError("Color must be a hex string")
        return value
```

### Multiple Feature Instances

Register multiple instances of the same feature:

```python
def init_features(self):
    # Create multiple text editors
    for i in range(3):
        editor = TextEditorWindow(feature_id=f"text_editor_{i}")
        self.register_window(editor)
```

### Dynamic Feature Loading

Load features based on configuration or plugins:

```python
def init_features(self):
    # Load features from a configuration file
    import json
    with open("features.json") as f:
        feature_config = json.load(f)
    
    for feature in feature_config["enabled_features"]:
        if feature == "text_editor":
            self.register_window(TextEditorWindow(feature_id="text_editor"))
        elif feature == "data_viewer":
            self.register_window(DataViewerWindow(feature_id="data_viewer"))
```

## Tips and Best Practices

1. **Feature IDs** - Use unique, descriptive IDs for each feature instance
2. **Settings Models** - Keep settings focused on user preferences, not runtime state
3. **State Models** - Use for data that should persist across sessions
4. **Field Descriptions** - Always provide descriptive labels for settings fields (enables search)
5. **UI Updates** - Always check for attribute existence in `apply_to_ui` and `extract_from_ui`
6. **Translations** - Use `self.tr()` for all user-visible strings
7. **Icons** - Use theme icons for better integration across different themes
8. **Error Handling** - Add try-except blocks in file operations and state restoration
9. **PySide6 Only** - Framework is designed specifically for PySide6, not PyQt

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
