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
