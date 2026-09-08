# This Python file uses the following encoding: utf-8
"""
Tests for the main application window.

ServiceLocator is a process wide singleton and refuses a second registration
of the same service, so exactly one BaseApplication is built for the whole
test session and every test shares it. Each test must therefore use its own
feature name and must not remove anything another test relies on.

The import order below matters. Importing opaque.view.view before
opaque.view.application raises a circular import error.
"""

import logging
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLabel, QWidget

from opaque.models.configuration import DefaultApplicationConfiguration
from opaque.view.application import BaseApplication
from opaque.models.model import BaseModel
from opaque.view.view import BaseView
from opaque.presenters.presenter import BasePresenter


class _TestConfiguration(DefaultApplicationConfiguration):
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


class _StubModel(BaseModel):
    """A feature model with no settings and no workspace data."""

    def __init__(self, app, name: str):
        super().__init__(app)
        self._name = name

    def feature_name(self) -> str:
        return self._name

    def feature_description(self) -> str:
        return "A feature used only by the tests."

    def feature_icon(self) -> QIcon:
        return QIcon()


class _StubView(BaseView):
    """A feature window holding one label."""

    def __init__(self, app):
        super().__init__(app)
        self.setWidget(QLabel("stub"))


class _StubPresenter(BasePresenter):
    """A presenter that records the calls the framework makes on it."""

    def __init__(self, model, view, app, feature_id):
        self.cleanup_calls = 0
        super().__init__(model, view, app, feature_id)

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
    """Build one BaseApplication for the whole test session."""
    settings_file = tmp_path_factory.mktemp("shell") / "settings.json"
    configuration = _TestConfiguration()
    configuration.settings_file_path = str(settings_file)
    window = BaseApplication(configuration)
    yield window
    window.close()


@pytest.fixture
def make_feature(app_window):
    """Return a factory that registers one feature under a unique name."""
    def _make(name: str) -> _StubPresenter:
        model = _StubModel(app_window, name)
        view = _StubView(app_window)
        return _StubPresenter(model, view, app_window, name)
    return _make


def test_a_registered_feature_is_in_the_registry(app_window, make_feature):
    presenter = make_feature("Registry Feature")
    app_window.register_feature(presenter)
    assert "Registry Feature" in app_window._registered_features


def test_a_closed_feature_window_stays_registered(app_window, make_feature):
    presenter = make_feature("Closing Feature")
    app_window.register_feature(presenter)

    presenter.view.window_closed.emit()

    assert "Closing Feature" in app_window._registered_features
    assert app_window._registered_features["Closing Feature"] is presenter


def test_registering_the_same_feature_twice_is_refused(
        app_window, make_feature):
    app_window.register_feature(make_feature("Twice Feature"))
    with pytest.raises(ValueError):
        app_window.register_feature(make_feature("Twice Feature"))


def test_the_title_has_no_empty_brackets_without_a_workspace():
    title = BaseApplication.build_window_title("My App", "1.0", None)
    assert title == "My App 1.0"
    assert "[" not in title


def test_an_empty_workspace_name_is_the_same_as_none():
    assert BaseApplication.build_window_title("My App", "1.0", "") == \
        BaseApplication.build_window_title("My App", "1.0", None)


def test_the_title_shows_the_workspace_when_there_is_one():
    title = BaseApplication.build_window_title("My App", "1.0", "bench.wks")
    assert title == "My App 1.0 [bench.wks]"


def test_the_minimum_size_is_applied_as_a_minimum(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    BaseApplication.apply_size_limits(widget, (640, 480), None)
    assert widget.minimumWidth() == 640
    assert widget.minimumHeight() == 480


def test_the_maximum_size_is_applied_as_a_maximum(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    BaseApplication.apply_size_limits(widget, None, (1920, 1080))
    assert widget.maximumWidth() == 1920
    assert widget.maximumHeight() == 1080
    # The bug this replaces set the maximum as a minimum.
    assert widget.minimumWidth() != 1920


def test_the_file_menu_actions_have_shortcuts(app_window):
    shortcuts = [
        action.shortcut().toString()
        for action in app_window.file_menu.actions()
        if not action.isSeparator()
    ]
    assert "" not in shortcuts
    assert len(shortcuts) == 4


_UI_MODULES = [
    "src/opaque/view/application.py",
    "src/opaque/presenters/presenter.py",
    "src/opaque/presenters/notification_presenter.py",
    "src/opaque/presenters/console_presenter.py",
    "src/opaque/view/widgets/closeable_tab_widget.py",
    "src/opaque/services/settings_service.py",
    "src/opaque/services/single_instance_service.py",
    "src/opaque/services/theme_service.py",
    "src/opaque/services/workspace_service.py",
    "src/opaque/models/console_model.py",
]


def test_the_shell_modules_have_a_logger():
    import opaque.presenters.notification_presenter as notification_module
    import opaque.view.application as application_module

    assert isinstance(application_module.logger, logging.Logger)
    assert isinstance(notification_module.logger, logging.Logger)


def test_no_ui_module_reports_an_error_with_print():
    root = Path(__file__).resolve().parents[1]
    offenders = []
    for relative in _UI_MODULES:
        source = (root / relative).read_text(encoding="utf-8")
        for number, line in enumerate(source.splitlines(), 1):
            if line.strip().startswith("print("):
                offenders.append(f"{relative}:{number}")
    assert offenders == []


def test_load_workspace_does_not_ask_when_a_path_is_given(
        app_window, monkeypatch, tmp_path):
    given = str(tmp_path / "given.wks")
    asked = []
    loaded = []
    monkeypatch.setattr(
        app_window, "_ask_for_workspace_path",
        lambda for_load: asked.append(for_load) or "")
    monkeypatch.setattr(
        app_window.workspace_service, "load_workspace",
        lambda path: loaded.append(path) or "given")

    app_window.load_workspace(given)

    assert asked == []
    assert loaded == [given]


def test_load_workspace_asks_when_no_path_is_given(app_window, monkeypatch):
    asked = []
    loaded = []
    monkeypatch.setattr(
        app_window, "_ask_for_workspace_path",
        lambda for_load: asked.append(for_load) or "chosen.wks")
    monkeypatch.setattr(
        app_window.workspace_service, "load_workspace",
        lambda path: loaded.append(path) or "chosen")

    app_window.load_workspace()

    assert asked == [True]
    assert loaded == ["chosen.wks"]


def test_load_workspace_does_nothing_when_the_user_cancels(
        app_window, monkeypatch):
    loaded = []
    monkeypatch.setattr(
        app_window, "_ask_for_workspace_path", lambda for_load: "")
    monkeypatch.setattr(
        app_window.workspace_service, "load_workspace",
        lambda path: loaded.append(path))

    app_window.load_workspace()

    assert loaded == []


def test_a_dropped_file_with_the_configured_extension_is_accepted():
    urls = [QUrl.fromLocalFile("C:/work/bench.wks")]
    path = BaseApplication.workspace_path_from_urls(urls, ".wks")
    assert path is not None
    assert path.endswith("bench.wks")


def test_a_dropped_file_with_another_extension_is_refused():
    urls = [QUrl.fromLocalFile("C:/work/bench.lab")]
    assert BaseApplication.workspace_path_from_urls(urls, ".wks") is None


def test_two_dropped_files_are_refused():
    urls = [
        QUrl.fromLocalFile("C:/work/one.wks"),
        QUrl.fromLocalFile("C:/work/two.wks"),
    ]
    assert BaseApplication.workspace_path_from_urls(urls, ".wks") is None


def test_the_extension_check_ignores_case():
    urls = [QUrl.fromLocalFile("C:/work/BENCH.WKS")]
    assert BaseApplication.workspace_path_from_urls(urls, ".wks") is not None


def test_a_theme_change_reaches_the_toolbar(app_window, monkeypatch):
    calls = []
    monkeypatch.setattr(
        app_window.toolbar, "update_theme", lambda: calls.append(True))

    app_window.theme_service.theme_changed.emit("Default")

    assert calls == [True]


def test_the_notification_dock_visibility_reaches_the_toolbar(
        app_window, monkeypatch):
    seen = []
    monkeypatch.setattr(
        app_window.toolbar, "set_notifications_visible", seen.append)

    dock = app_window.notification_presenter.get_notification_widget()
    dock.visibilityChanged.emit(True)

    assert seen == [True]


def test_the_notification_count_reaches_the_toolbar(app_window, monkeypatch):
    seen = []
    monkeypatch.setattr(
        app_window.toolbar, "set_notification_count", seen.append)

    model = app_window.notification_presenter.get_notification_model()
    model.notification_count_changed.emit(7)

    assert seen == [7]


def test_the_help_menu_has_a_keyboard_map_action(app_window):
    labels = [
        action.text().replace("&", "")
        for action in app_window.help_menu.actions()
        if not action.isSeparator()
    ]
    assert "Keyboard Shortcuts" in labels


def test_the_keyboard_map_uses_the_help_key(app_window):
    action = next(
        action for action in app_window.help_menu.actions()
        if action.text().replace("&", "") == "Keyboard Shortcuts"
    )
    assert action.shortcut().toString() == "F1"


def test_the_keyboard_map_lists_the_file_menu_keys(app_window, qtbot):
    dialog = app_window.build_keyboard_map_dialog()
    qtbot.addWidget(dialog)
    labels = [
        dialog.table.item(row, 0).text()
        for row in range(dialog.table.rowCount())
    ]
    assert "Save Workspace" in labels
    assert "Keyboard Shortcuts" in labels


def test_the_mdi_area_starts_in_the_sub_window_mode(app_window):
    assert not app_window.mdi_area.is_tabbed()


def test_the_mdi_area_can_switch_to_tabs(app_window):
    app_window.mdi_area.set_tabbed(True)
    assert app_window.mdi_area.is_tabbed()
    app_window.mdi_area.set_tabbed(False)
    assert not app_window.mdi_area.is_tabbed()


def test_the_view_menu_offers_the_tabbed_mode(app_window):
    labels = [
        action.text().replace("&", "")
        for action in app_window.view_menu.actions()
        if not action.isSeparator()
    ]
    assert "Tabbed Windows" in labels


def test_the_tabbed_action_is_checkable_and_follows_the_area(app_window):
    action = next(
        action for action in app_window.view_menu.actions()
        if action.text().replace("&", "") == "Tabbed Windows"
    )
    assert action.isCheckable()

    action.setChecked(True)
    assert app_window.mdi_area.is_tabbed()

    action.setChecked(False)
    assert not app_window.mdi_area.is_tabbed()
