#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example demonstrating how to extend global settings in OPAQUE Framework.

This shows how developers can add custom global settings to their application
beyond the default theme and language settings.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PySide6.QtWidgets import QApplication
from opaque import BaseApplication, GlobalSettings, BoolField, IntField, StringField


class MyGlobalSettings(GlobalSettings):
    """
    Extended global settings with custom application-wide settings.

    Inherits theme and language from GlobalSettings, and adds:
    - auto_save: Enable auto-save functionality
    - auto_save_interval: How often to auto-save (in minutes)
    - default_project_path: Default path for new projects
    - show_welcome_screen: Show welcome screen on startup
    """

    # Custom global settings
    auto_save = BoolField(
        default=True,
        description="Enable automatic saving of workspace"
    )

    auto_save_interval = IntField(
        default=5,
        min_value=1,
        max_value=60,
        description="Auto-save interval (minutes)"
    )

    default_project_path = StringField(
        default="~/Documents/Projects",
        description="Default path for new projects"
    )

    show_welcome_screen = BoolField(
        default=True,
        description="Show welcome screen on startup"
    )


class CustomGlobalSettingsApp(BaseApplication):
    """
    Example application demonstrating custom global settings.
    """

    def application_name(self) -> str:
        return "CustomSettingsExample"

    def organization_name(self) -> str:
        return "OPAQUEExamples"

    def application_title(self) -> str:
        return "OPAQUE - Custom Global Settings Example"

    def register_features(self) -> None:
        # No features in this minimal example
        # In a real app, you would register your feature windows here
        pass

    def global_settings_model(self):
        """
        Override to return our custom global settings model.
        """
        return MyGlobalSettings

    def __init__(self):
        super().__init__()

        # Now we can access our custom global settings
        if hasattr(self, 'global_settings'):
            print(f"Auto-save enabled: {self.global_settings.auto_save}")
            print(
                f"Auto-save interval: {self.global_settings.auto_save_interval} minutes")
            print(
                f"Default project path: {self.global_settings.default_project_path}")
            print(
                f"Show welcome screen: {self.global_settings.show_welcome_screen}")

            # Example: Use the settings to configure application behavior
            if self.global_settings.show_welcome_screen:
                self._show_welcome_message()

    def _show_welcome_message(self):
        """Example of using a global setting to control behavior"""
        print("Welcome to the Custom Global Settings Example!")
        # In a real app, this might show a welcome dialog


if __name__ == "__main__":
    app = QApplication(sys.argv)

    main_window = CustomGlobalSettingsApp()
    main_window.show()

    # Open settings dialog to see the custom global settings
    print("\nOpening settings dialog to show custom global settings...")
    main_window.show_settings_dialog()

    sys.exit(app.exec())
