# This Python file uses the following encoding: utf-8
"""Tests that the notification settings are declared, saved and editable."""

import pytest

from opaque.models.notification_settings_model import NotificationSettingsModel
from opaque.presenters.notification_presenter import (
    NOTIFICATION_SETTINGS_ID,
    NotificationPresenter,
)
from opaque.services.notification_service import NotificationService
from opaque.services.service import ServiceLocator
from opaque.services.settings_service import SettingsService


@pytest.fixture
def services(tmp_path, qapp):
    ServiceLocator.cleanup_services()
    settings = SettingsService(tmp_path / "settings.json")
    settings.initialize()
    ServiceLocator.register_service(settings)
    notifications = NotificationService()
    notifications.initialize()
    ServiceLocator.register_service(notifications)
    yield settings
    ServiceLocator.cleanup_services()


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

    ServiceLocator.cleanup_services()
    settings = SettingsService(path)
    settings.initialize()
    ServiceLocator.register_service(settings)
    notifications = NotificationService()
    notifications.initialize()
    ServiceLocator.register_service(notifications)
    try:
        window = QMainWindow()
        qtbot.addWidget(window)
        presenter = NotificationPresenter(window)
        assert presenter.settings_page().model.enable_toasts is False
    finally:
        ServiceLocator.cleanup_services()


def test_the_settings_dialog_shows_the_notification_page(presenter):
    from opaque.view.dialogs.settings import SettingsDialog

    dialog = SettingsDialog([presenter.settings_page()], parent=None)
    try:
        titles = [dialog.groups_list.item(row).text()
                  for row in range(dialog.groups_list.count())]
        assert "Notification System" in titles
    finally:
        dialog.deleteLater()
