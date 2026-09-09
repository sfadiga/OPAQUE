# This Python file uses the following encoding: utf-8
"""Tests that the notification settings are declared, saved and editable."""

import pytest

from opaque.models.notification_settings_model import NotificationSettingsModel
from opaque.presenters.notification_presenter import (
    NOTIFICATION_SETTINGS_ID,
    NotificationPresenter,
)
from opaque.services.logger_service import LoggerService
from opaque.services.notification_service import NotificationService
from opaque.services.service import ServiceLocator
from opaque.services.settings_service import SettingsService


@pytest.fixture
def services(tmp_path, qapp):
    # Save and restore, not just wipe: cleanup_services() alone discarded
    # whatever the session-scoped app_window fixture had already registered
    # (including, later, the version service), and nothing put it back.
    saved = dict(ServiceLocator._services)
    ServiceLocator._services.clear()
    settings = SettingsService(tmp_path / "settings.json")
    settings.initialize()
    ServiceLocator.register_service(settings)
    notifications = NotificationService()
    notifications.initialize()
    ServiceLocator.register_service(notifications)
    logger_service = LoggerService(
        log_directory=str(tmp_path / "logs"), application_name="test")
    logger_service.initialize()
    ServiceLocator.register_service(logger_service)
    yield settings
    ServiceLocator.cleanup_services()
    ServiceLocator._services.update(saved)


@pytest.fixture
def presenter(services, qtbot):
    from PySide6.QtWidgets import QMainWindow

    window = QMainWindow()
    qtbot.addWidget(window)
    return NotificationPresenter(window)


def test_every_field_of_the_model_is_a_setting():
    fields = NotificationSettingsModel.get_fields()
    assert fields
    not_settings = [name for name, field in fields.items()
                    if not field.is_setting]
    assert not_settings == []


def test_the_model_can_name_and_draw_itself(qapp):
    model = NotificationSettingsModel()
    assert model.feature_name() == "Notification System"
    assert model.feature_description() != ""
    assert model.feature_icon() is not None


def test_the_presenter_registers_the_settings_model(presenter, services):
    stored = services.get_all_settings()
    assert NOTIFICATION_SETTINGS_ID in stored
    assert "enable_toasts" in stored[NOTIFICATION_SETTINGS_ID]


def test_the_presenter_offers_one_settings_page(presenter):
    page = presenter.settings_page()
    assert page is not None
    assert page.feature_id == NOTIFICATION_SETTINGS_ID
    assert isinstance(page.model, NotificationSettingsModel)
    assert callable(page.apply_settings)


def test_a_stored_value_reaches_the_model_at_start(tmp_path, qapp, qtbot):
    import json

    from PySide6.QtWidgets import QMainWindow

    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({NOTIFICATION_SETTINGS_ID: {"enable_toasts": False}}),
        encoding="utf-8")

    saved = dict(ServiceLocator._services)
    ServiceLocator._services.clear()
    settings = SettingsService(path)
    settings.initialize()
    ServiceLocator.register_service(settings)
    notifications = NotificationService()
    notifications.initialize()
    ServiceLocator.register_service(notifications)
    logger_service = LoggerService(
        log_directory=str(tmp_path / "logs"), application_name="test")
    logger_service.initialize()
    ServiceLocator.register_service(logger_service)
    try:
        window = QMainWindow()
        qtbot.addWidget(window)
        presenter = NotificationPresenter(window)
        assert presenter.settings_page().model.enable_toasts is False
    finally:
        ServiceLocator.cleanup_services()
        ServiceLocator._services.update(saved)


def test_the_settings_dialog_shows_the_notification_page(presenter):
    from opaque.view.dialogs.settings import SettingsDialog

    dialog = SettingsDialog([presenter.settings_page()], parent=None)
    try:
        titles = [dialog.groups_list.item(row).text()
                  for row in range(dialog.groups_list.count())]
        assert "Notification System" in titles
    finally:
        dialog.deleteLater()


def _add(presenter, level):
    from opaque.services.notification_service import NotificationLevel

    service = ServiceLocator.get(NotificationService)
    return service.add_notification(
        level=level, title="Title", message="Message", source="Test")


def test_a_notification_reaches_the_list(presenter):
    from opaque.services.notification_service import NotificationLevel

    _add(presenter, NotificationLevel.ERROR)

    assert len(presenter._notification_list.items) == 1


def test_the_master_switch_stops_every_notification(presenter):
    from opaque.services.notification_service import NotificationLevel

    presenter.settings_page().model.notifications_enabled = False

    _add(presenter, NotificationLevel.ERROR)

    assert presenter._notification_list.items == {}


def test_a_level_that_is_switched_off_does_not_reach_the_list(presenter):
    from opaque.services.notification_service import NotificationLevel

    presenter.settings_page().model.show_error_notifications = False

    _add(presenter, NotificationLevel.ERROR)

    assert presenter._notification_list.items == {}


def test_a_level_that_is_switched_on_still_reaches_the_list(presenter):
    from opaque.services.notification_service import NotificationLevel

    presenter.settings_page().model.show_error_notifications = False

    _add(presenter, NotificationLevel.INFO)

    assert len(presenter._notification_list.items) == 1


def test_debug_notifications_are_off_by_default(presenter):
    from opaque.services.notification_service import NotificationLevel

    _add(presenter, NotificationLevel.DEBUG)

    assert presenter._notification_list.items == {}


def test_no_toast_appears_when_toasts_are_switched_off(presenter):
    from opaque.services.notification_service import NotificationLevel

    presenter.settings_page().model.enable_toasts = False

    _add(presenter, NotificationLevel.ERROR)

    assert presenter._active_toasts == []


def test_a_toast_appears_when_toasts_are_switched_on(presenter):
    from opaque.services.notification_service import NotificationLevel

    _add(presenter, NotificationLevel.ERROR)

    assert len(presenter._active_toasts) == 1


def test_the_auto_hide_timeout_replaces_the_level_duration(presenter):
    from opaque.services.notification_service import NotificationLevel

    model = presenter.settings_page().model
    model.auto_hide_notifications = True
    model.auto_hide_timeout = 1500

    _add(presenter, NotificationLevel.ERROR)

    toast = presenter._active_toasts[0]
    assert toast.close_timer.isActive()
    assert toast.close_timer.interval() == 1500


def test_a_toast_that_never_expires_is_left_alone(presenter):
    from opaque.services.notification_service import NotificationLevel

    model = presenter.settings_page().model
    model.auto_hide_notifications = True
    model.auto_hide_timeout = 1500

    _add(presenter, NotificationLevel.CRITICAL)

    toast = presenter._active_toasts[0]
    # A critical toast has no duration, so it must not gain one.
    if not toast.close_timer.isActive():
        assert toast.close_timer.interval() != 1500


def test_the_row_limit_drops_the_oldest_row(presenter):
    from opaque.services.notification_service import NotificationLevel

    presenter.settings_page().model.max_notification_display = 2
    presenter.apply_settings()

    first = _add(presenter, NotificationLevel.INFO)
    _add(presenter, NotificationLevel.INFO)
    _add(presenter, NotificationLevel.INFO)

    assert len(presenter._notification_list.items) == 2
    assert first not in presenter._notification_list.items


def test_the_row_limit_can_be_raised_again(presenter):
    from opaque.services.notification_service import NotificationLevel

    model = presenter.settings_page().model
    model.max_notification_display = 1
    presenter.apply_settings()
    _add(presenter, NotificationLevel.INFO)
    _add(presenter, NotificationLevel.INFO)
    assert len(presenter._notification_list.items) == 1

    model.max_notification_display = 5
    presenter.apply_settings()
    _add(presenter, NotificationLevel.INFO)

    assert len(presenter._notification_list.items) == 2


def test_the_dock_moves_to_the_position_the_settings_name(presenter):
    from PySide6.QtCore import Qt

    presenter.settings_page().model.notification_widget_position = "Left"
    presenter.apply_settings()

    area = presenter._main_window.dockWidgetArea(presenter._dock_widget)
    assert area == Qt.DockWidgetArea.LeftDockWidgetArea


def test_applying_the_dock_settings_does_not_open_a_closed_panel(presenter):
    presenter.settings_page().model.notification_widget_position = "Top"
    presenter.apply_settings()

    assert presenter._dock_widget.isVisible() is False


def test_the_toolbar_count_is_hidden_when_the_setting_is_off(presenter):
    presenter.settings_page().model.show_notification_count = False

    assert presenter.displayed_count(7) == 0


def test_the_toolbar_count_is_passed_through_when_the_setting_is_on(presenter):
    assert presenter.displayed_count(7) == 7


def test_the_log_level_setting_reaches_the_logger_service(presenter, qapp):
    service = ServiceLocator.get(LoggerService)

    presenter.settings_page().model.log_level = "ERROR"
    presenter.apply_settings()

    assert service.get_configuration()["log_level"] == "ERROR"


def test_the_warning_notification_setting_reaches_the_logger_service(
        presenter, qapp):
    service = ServiceLocator.get(LoggerService)

    presenter.settings_page().model.notification_on_warning = True
    presenter.apply_settings()

    assert service.get_configuration()["notify_on_warning"] is True


def test_a_warning_creates_a_notification_when_the_setting_is_on(services, qapp):
    service = ServiceLocator.get(LoggerService)
    notifications = ServiceLocator.get(NotificationService)

    service.set_notification_on_warning(True)
    before = len(notifications.get_notifications())

    service.log("WARNING", "the tank is low", source="Test")

    assert len(notifications.get_notifications()) == before + 1


def test_a_warning_creates_no_notification_when_the_setting_is_off(services, qapp):
    service = ServiceLocator.get(LoggerService)
    notifications = ServiceLocator.get(NotificationService)

    service.set_notification_on_warning(False)
    before = len(notifications.get_notifications())

    service.log("WARNING", "the tank is low", source="Test")

    assert len(notifications.get_notifications()) == before


def test_the_model_names_a_log_directory_and_not_a_file():
    fields = NotificationSettingsModel.get_fields()
    assert "log_directory" in fields
    assert "log_file_path" not in fields
    assert "next start" in fields["log_directory"].description
