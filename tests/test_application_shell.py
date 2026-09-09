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
from PySide6.QtWidgets import QWidget

from opaque.view.application import BaseApplication


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
    # A bare key name is not a usable shortcut. Qt has no standard
    # Preferences or Quit shortcut on Windows, and before Qt 6.11 it
    # answered with the multimedia key names "Settings" and "Exit". Both
    # are non-empty, so the emptiness check above passed while the two
    # menu items had no shortcut a keyboard could produce.
    without_modifier = [text for text in shortcuts if "+" not in text]
    assert without_modifier == []


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


def test_toggling_tabbed_mode_disables_cascade_and_tile(app_window):
    app_window.tabbed_action.setChecked(True)
    assert not app_window.toolbar.cascade_button.isEnabled()
    assert not app_window.toolbar.tiled_button.isEnabled()

    app_window.tabbed_action.setChecked(False)
    assert app_window.toolbar.cascade_button.isEnabled()
    assert app_window.toolbar.tiled_button.isEnabled()


def test_a_theme_change_reaches_a_widget_that_paints_its_own_colours(
        app_window):
    calls = []

    class _PaintingWidget(QWidget):
        def apply_theme(self):
            calls.append(True)

    _PaintingWidget(app_window)

    app_window.theme_service.theme_changed.emit("Default")

    assert calls == [True]


def test_a_widget_without_apply_theme_does_not_break_the_walk(app_window):
    plain = QWidget(app_window)

    app_window.theme_service.theme_changed.emit("Default")

    # Nothing to assert on the widget itself. The test passes when the walk
    # completes, which proves the walk does not require the method.
    assert plain.parent() is app_window


def test_a_settings_change_from_the_service_reaches_the_presenter(
        app_window, monkeypatch):
    presenter = next(iter(app_window._registered_features.values()))
    calls = []
    monkeypatch.setattr(
        presenter, "apply_settings", lambda: calls.append(True))

    app_window.settings_service.settings_changed.emit(
        presenter.feature_id, {})

    assert calls == [True]


def test_a_settings_change_for_an_unknown_feature_is_ignored(app_window):
    # Nothing to assert but the absence of a failure: an unknown identity
    # must not raise inside a signal handler.
    app_window.settings_service.settings_changed.emit("no-such-feature", {})


def test_a_settings_change_reaches_the_notification_presenter(
        app_window, monkeypatch):
    from opaque.presenters.notification_presenter import (
        NOTIFICATION_SETTINGS_ID,
    )

    calls = []
    monkeypatch.setattr(
        app_window.notification_presenter, "apply_settings",
        lambda: calls.append(True))

    app_window.settings_service.settings_changed.emit(
        NOTIFICATION_SETTINGS_ID, {})

    assert calls == [True]


def test_the_application_object_carries_no_bolted_on_window(app_window):
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance()

    assert not hasattr(application, "main_window")


def test_the_shell_is_reachable_through_the_presenter(app_window):
    presenter = next(iter(app_window._registered_features.values()))
    assert presenter.context.shell is app_window


def test_the_shell_offers_one_context(app_window):
    from opaque.features.context import FeatureContext

    assert isinstance(app_window.context, FeatureContext)


def test_the_shell_context_carries_the_shell(app_window):
    assert app_window.context.shell is app_window


def test_the_shell_context_carries_the_configuration(app_window):
    assert app_window.context.configuration is app_window._configuration


def test_the_shell_can_host_a_feature_window(app_window, qtbot):
    from PySide6.QtWidgets import QWidget

    before = len(app_window.mdi_area.subWindowList())
    app_window.add_feature_window(QWidget())

    assert len(app_window.mdi_area.subWindowList()) == before + 1


def test_the_application_model_reads_the_icon_from_the_context(app_window):
    from PySide6.QtGui import QIcon

    presenter = app_window._registered_features["application"]
    assert isinstance(presenter.model.feature_icon(), QIcon)


def test_no_model_reaches_a_private_shell_attribute():
    import inspect

    from opaque.models import app_model

    assert "_configuration" not in inspect.getsource(app_model)
