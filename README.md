# OPAQUE Framework

**OPAQUE** - **O**pinionated **P**ython **A**pplication with **Q**t **U**I for **E**ngineering

An opinionated PySide6-based MDI application framework designed to accelerate the development of professional desktop applications following the Model-View-Presenter (MVP) pattern.

![OPAQUE Framework Screenshot](resources/example.gif)

## Features

- 🪟 **MDI Window Management** - Multiple Document Interface with dockable windows.
- 🏗️ **MVP Architecture** - Clean separation of concerns between data (Model), UI (View), and logic (Presenter).
- 🎨 **Theme Management** - 40+ themes including qt-material, qt-themes, and QDarkStyle.
- 💾 **Persistence Layer** - Automatic saving/loading of settings and workspace state.
- ⚙️ **Global & Feature Settings** - Extensible settings system with a unified dialog.
- 🔍 **Enhanced Settings Search** - Search through both group names and individual settings.
- 📦 **State Management** - Save and restore complete workspace states.
- 🔧 **Service Locator** - Manages shared services across the application.

## Quick Start

### Installation

```bash
# Install from PyPI (once published)
pip install opaque-framework

# With additional themes
pip install opaque-framework[themes]

# For development
pip install opaque-framework[dev]
```

### Basic Usage

```python
# main.py
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from opaque.core.application import BaseApplication
from features.my_feature.presenter import MyFeaturePresenter

class MyApplication(BaseApplication):
    def application_name(self) -> str:
        return "MyApp"

    def organization_name(self) -> str:
        return "MyCompany"

    def application_title(self) -> str:
        return "My OPAQUE Application"

    def application_icon(self) -> QIcon:
        return QIcon("path/to/your/icon.ico")
    
    def application_description(self) -> str:
        return "A simple application created with the OPAQUE framework."

    def __init__(self):
        super().__init__()
        self._register_features()

    def _register_features(self):
        # Register features using their presenters
        my_feature_presenter = MyFeaturePresenter(feature_id="my_feature_1")
        self.register_feature(my_feature_presenter)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MyApplication()
    main_win.show()
    sys.exit(app.exec())
```

## Project Structure

```
src/
└── opaque/
    ├── core/               # Core MVP components (BaseApplication, BaseModel, BaseView, BasePresenter)
    ├── managers/           # Managers for settings, themes, workspace, etc.
    ├── models/             # Data models and field annotations
    └── widgets/            # Custom UI widgets (Toolbar, MDI area, dialogs)
examples/
└── basic_example/          # Example application demonstrating framework features
pyproject.toml              # Package configuration
```

## Key Concepts

### Model-View-Presenter (MVP)

OPAQUE is built on the MVP pattern to ensure a clean separation of concerns.

-   **Model**: Manages the application's data and business logic. It knows nothing about the UI. In OPAQUE, models inherit from `BaseModel` and use `Field` annotations to define their properties.
-   **View**: Displays the data from the model and sends user actions to the presenter. It is passive and does not contain any application logic. Views inherit from `BaseView`.
-   **Presenter**: Acts as the middleman between the Model and the View. It retrieves data from the model, formats it for display in the view, and processes user input. Presenters inherit from `BasePresenter`.

### Feature Registration

Features are self-contained components of your application, each following the MVP pattern. You register a feature by creating an instance of its presenter and passing it to the `register_feature` method of your main application class.

### Settings and State Management

-   **Settings**: User-configurable options that persist across sessions. Defined in a model using `Field(settings=True)`.
-   **Workspace State**: Data that captures the current state of a feature, like open files or current values. Defined using `Field(workspace=True)`.

Settings are automatically handled by the `SettingsManager` and displayed in a unified settings dialog.

## Step-by-Step Guide: Creating a Feature

This guide walks you through creating a "Text Editor" feature.

### Step 1: Define the Model

The model defines the data and state for the feature.

`features/text_editor/model.py`:
```python
from opaque.core.model import BaseModel
from opaque.models.annotations import BoolField, IntField, StringField
from PySide6.QtGui import QIcon

class TextEditorModel(BaseModel):
    FEATURE_NAME = "Text Editor"

    # Settings
    word_wrap = BoolField(default=True, description="Enable word wrap", settings=True)
    font_size = IntField(default=12, min_value=8, max_value=72, description="Font size", settings=True)

    # Workspace State
    content = StringField(default="", workspace=True)
    file_path = StringField(default="", workspace=True)

    def feature_name(self) -> str:
        return self.FEATURE_NAME

    def feature_icon(self) -> QIcon:
        return QIcon.fromTheme("accessories-text-editor")
```

### Step 2: Create the View

The view defines the UI components for the feature.

`features/text_editor/view.py`:
```python
from opaque.core.view import BaseView
from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget, QToolBar, QAction
from PySide6.QtGui import QIcon

class TextEditorView(BaseView):
    def __init__(self, feature_id: str):
        super().__init__(feature_id)
        self.setWindowTitle("Text Editor")

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)

        self.toolbar = QToolBar()
        self.open_action = QAction(QIcon.fromTheme("document-open"), "Open", self)
        self.save_action = QAction(QIcon.fromTheme("document-save"), "Save", self)
        self.toolbar.addAction(self.open_action)
        self.toolbar.addAction(self.save_action)
        layout.addWidget(self.toolbar)

        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)

        self.set_content(main_widget)
```

### Step 3: Implement the Presenter

The presenter connects the model and the view, handling the logic.

`features/text_editor/presenter.py`:
```python
from opaque.core.presenter import BasePresenter
from .model import TextEditorModel
from .view import TextEditorView
from PySide6.QtWidgets import QFileDialog

class TextEditorPresenter(BasePresenter):
    def __init__(self, feature_id: str):
        model = TextEditorModel(feature_id)
        view = TextEditorView(feature_id)
        super().__init__(feature_id, model, view)

    def bind_events(self):
        self.view.open_action.triggered.connect(self._open_file)
        self.view.save_action.triggered.connect(self._save_file)
        self.view.text_edit.textChanged.connect(self._on_text_changed)

    def update(self, property_name: str, value: any):
        if property_name == "content":
            self.view.text_edit.setPlainText(value)
        elif property_name == "font_size":
            font = self.view.text_edit.font()
            font.setPointSize(value)
            self.view.text_edit.setFont(font)

    def _on_text_changed(self):
        self.model.content = self.view.text_edit.toPlainText()

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(self.view, "Open File")
        if path:
            with open(path, 'r') as f:
                self.model.content = f.read()
            self.model.file_path = path

    def _save_file(self):
        path = self.model.file_path
        if not path:
            path, _ = QFileDialog.getSaveFileName(self.view, "Save File")
        
        if path:
            with open(path, 'w') as f:
                f.write(self.model.content)
            self.model.file_path = path
```

### Step 4: Register the Feature

Finally, register the feature in your main application.

`main.py`:
```python
# ... (imports and MyApplication class definition)
    def _register_features(self):
        text_editor_presenter = TextEditorPresenter(feature_id="text_editor_1")
        self.register_feature(text_editor_presenter)
```

## What You Get Automatically

✅ **Toolbar Integration**: Your feature appears as a button in the main toolbar.  
✅ **MDI Management**: Your window can be docked, floated, and arranged.  
✅ **Settings Dialog**: Your feature's settings appear automatically.  
✅ **Persistence**: Settings and workspace state are saved and loaded.  
✅ **Theme Support**: Your feature inherits the application theme.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## License

MIT License - See the LICENSE file for details.
