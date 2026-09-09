#!/usr/bin/env python3
# This Python file uses the following encoding: utf-8
"""
Basic OPAQUE Framework Application Template

The smallest application that runs. Copy this file, rename
TemplateApplication and TemplateModel, and add your own features with
self.register(YourModel, YourView, YourPresenter).

Build it into an executable with:
    opaque-build build main.py --name MyApplication

@copyright 2025 Your Name
Licensed under MIT License
"""

import sys
from typing import Any

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QLabel

from opaque.features.context import FeatureContext
from opaque.models.configuration import DefaultApplicationConfiguration
from opaque.models.model import BaseModel
from opaque.presenters.presenter import BasePresenter
from opaque.shell import BaseApplication
from opaque.view.view import BaseView


class TemplateConfiguration(DefaultApplicationConfiguration):
    """The five accessors below are abstract. Every application must write them."""

    def get_application_name(self) -> str:
        return "MyApplication"

    def get_application_title(self) -> str:
        return "My Application"

    def get_application_description(self) -> str:
        return "An OPAQUE framework application."

    def get_application_organization(self) -> str:
        return "My Organization"

    def get_application_icon(self) -> QIcon:
        return QIcon()


class TemplateModel(BaseModel):
    """The state of the one feature this template ships."""

    FEATURE_ID = "template"

    def feature_name(self) -> str:
        return "Welcome"


class TemplateView(BaseView):
    """The window of the one feature this template ships."""

    def __init__(self, context: FeatureContext, parent=None) -> None:
        super().__init__(context, parent)

    def setup_ui(self) -> None:
        self.label = QLabel(self.tr("Your application starts here."))
        self.setWidget(self.label)


class TemplatePresenter(BasePresenter):
    """The presenter of the one feature this template ships."""

    def bind_events(self) -> None:
        """Connect the view to this presenter. Nothing to connect yet."""

    def update(
            self,
            field_name: str,
            new_value: Any,
            old_value: Any = None,
            model: Any = None,
    ) -> None:
        """Called when a model field changes. Nothing to show yet."""

    def on_view_show(self) -> None:
        """Called when the window is shown."""


class TemplateApplication(BaseApplication):
    """The application shell."""

    def __init__(self) -> None:
        super().__init__(TemplateConfiguration())
        self.register(TemplateModel, TemplateView, TemplatePresenter)


def main() -> int:
    """Start the application."""
    application = QApplication(sys.argv)
    window = TemplateApplication()

    if not window.try_acquire_lock():
        window.show_already_running_message()
        return 1

    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
