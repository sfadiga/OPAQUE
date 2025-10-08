"""
OPAQUE - Opinionated Python Application with Qt UI for Engineering
A flexible MDI application framework for PySide6

@copyright 2025 Sandro Fadiga
@license MIT License
"""

# Force qtpy to use PySide6 (must be before any Qt imports)
import os
os.environ['QT_API'] = 'pyside6'

__version__ = "1.0.0"
__author__ = "Sandro Fadiga"

# Core UI components
from .ui.core.base_application import BaseApplication
from .ui.core.base_feature_window import BaseFeatureWindow
from .ui.core.base_float_window import BaseFloatWindow
from .ui.core.main_toolbar import MainToolbar

# Models
from .models.base.base_model import BaseModel
from .models.base.field_descriptors import (
    BoolField,
    IntField,
    FloatField,
    StringField,
    ListField,
    DictField
)

# Settings
from .settings.global_settings import GlobalSettings

# Persistence managers
from .persistence.managers.settings_manager import SettingsManager
from .persistence.managers.workspace_manager import WorkspaceManager

# Dialogs
from .ui.dialogs.settings_dialog import SettingsDialog

# Layouts
from .ui.layouts.flow_layout import FlowLayout

__all__ = [
    # Version info
    "__version__",
    "__author__",
    
    # Core UI
    "BaseApplication",
    "BaseFeatureWindow",
    "BaseFloatWindow",
    "MainToolbar",
    
    # Models
    "BaseModel",
    "BoolField",
    "IntField",
    "FloatField",
    "StringField",
    "ListField",
    "DictField",
    
    # Settings
    "GlobalSettings",
    
    # Persistence
    "SettingsManager",
    "WorkspaceManager",
    
    # Dialogs
    "SettingsDialog",
    
    # Layouts
    "FlowLayout",
]
