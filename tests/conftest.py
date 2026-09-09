# This Python file uses the following encoding: utf-8
"""
Shared pytest fixtures for the OPAQUE framework tests.

The Qt platform is forced to "offscreen" so the suite runs the same way on a
developer machine and on a build agent with no display.

Widget tests must never read the developer's own desktop palette. The two
palette fixtures below give a fixed light palette and a fixed dark palette, so
a contrast assertion gives the same answer on every machine.
"""

import os

# This must run before any PySide6 module creates a QGuiApplication.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QLabel

# The import order below matters. Importing opaque.view.view before
# opaque.view.application raises a circular import error.
from opaque.models.configuration import DefaultApplicationConfiguration
from opaque.view.application import BaseApplication
from opaque.models.model import BaseModel
from opaque.view.view import BaseView
from opaque.presenters.presenter import BasePresenter


def _build_palette(values: dict) -> QPalette:
    """Build a QPalette from a mapping of colour role to hex string."""
    palette = QPalette()
    for role, hex_value in values.items():
        palette.setColor(role, QColor(hex_value))
    return palette


_LIGHT_ROLES = {
    QPalette.ColorRole.Window: "#f5f5f5",
    QPalette.ColorRole.WindowText: "#1a1a1a",
    QPalette.ColorRole.Base: "#ffffff",
    QPalette.ColorRole.Text: "#1a1a1a",
    QPalette.ColorRole.Mid: "#b0b0b0",
    QPalette.ColorRole.Button: "#efefef",
    QPalette.ColorRole.ButtonText: "#1a1a1a",
    QPalette.ColorRole.Highlight: "#0b6ba8",
    QPalette.ColorRole.HighlightedText: "#ffffff",
}

_DARK_ROLES = {
    QPalette.ColorRole.Window: "#2b2b2b",
    QPalette.ColorRole.WindowText: "#e0e0e0",
    QPalette.ColorRole.Base: "#1e1e1e",
    QPalette.ColorRole.Text: "#e0e0e0",
    QPalette.ColorRole.Mid: "#5a5a5a",
    QPalette.ColorRole.Button: "#3a3a3a",
    QPalette.ColorRole.ButtonText: "#e0e0e0",
    QPalette.ColorRole.Highlight: "#a8c7e0",
    QPalette.ColorRole.HighlightedText: "#08324f",
}


@pytest.fixture
def light_palette_app(qapp):
    """Apply a fixed light palette for the duration of one test."""
    original = qapp.palette()
    qapp.setPalette(_build_palette(_LIGHT_ROLES))
    yield qapp
    qapp.setPalette(original)


@pytest.fixture
def dark_palette_app(qapp):
    """Apply a fixed dark palette for the duration of one test."""
    original = qapp.palette()
    qapp.setPalette(_build_palette(_DARK_ROLES))
    yield qapp
    qapp.setPalette(original)


class TestConfiguration(DefaultApplicationConfiguration):
    """The smallest configuration BaseApplication will accept."""

    def get_application_name(self) -> str:
        return "OpaqueShellTest"

    def get_application_title(self) -> str:
        return "Opaque Shell Test"

    def get_application_description(self) -> str:
        return "A configuration used only by the tests."

    def get_application_icon(self) -> QIcon:
        return QIcon()

    def get_application_organization(self) -> str:
        return "Opaque Tests"


class StubModel(BaseModel):
    """A feature model with no settings and no workspace data."""

    def __init__(self, app, name: str):
        super().__init__(app)
        self._name = name

    def feature_id(self) -> str:
        """
        Return this stub's chosen identity.

        Many tests share the one session scoped app_window fixture, so each
        needs its own identity to avoid colliding with another test's. A
        fixed class level FEATURE_ID cannot do that; the name chosen at
        construction is stable for the life of the instance, which is what
        feature_id() promises.
        """
        return self._name

    def feature_name(self) -> str:
        return self._name

    def feature_description(self) -> str:
        return "A feature used only by the tests."

    def feature_icon(self) -> QIcon:
        return QIcon()


class StubView(BaseView):
    """A feature window holding one label."""

    def __init__(self, app):
        super().__init__(app)
        self.setWidget(QLabel("stub"))


class StubPresenter(BasePresenter):
    """A presenter that records the calls the framework makes on it."""

    def __init__(self, model, view, app):
        self.cleanup_calls = 0
        super().__init__(model, view, app)

    def bind_events(self) -> None:
        pass

    def initialize(self) -> None:
        pass

    def cleanup(self) -> None:
        self.cleanup_calls += 1

    def update(self, *args, **kwargs) -> None:
        pass

    def on_view_show(self) -> None:
        pass

    def on_view_close(self) -> None:
        pass


@pytest.fixture(scope="session")
def app_window(qapp, tmp_path_factory):
    """
    Build one BaseApplication for the whole test session.

    Defined once here, not in a test module, and not re-imported by name into
    other modules either: pytest gives an imported fixture function its own,
    separate FixtureDef per importing module, so each import built its own
    second BaseApplication and collided with the first on every process wide
    singleton service name. One definition in conftest.py is the only way
    every test file that asks for app_window shares the same instance.
    """
    settings_file = tmp_path_factory.mktemp("shell") / "settings.json"
    configuration = TestConfiguration()
    configuration.settings_file_path = str(settings_file)
    window = BaseApplication(configuration)
    yield window
    window.close()


@pytest.fixture
def make_feature(app_window):
    """Return a factory that registers one feature under a unique name."""
    def _make(name: str) -> StubPresenter:
        model = StubModel(app_window, name)
        view = StubView(app_window)
        return StubPresenter(model, view, app_window)
    return _make
