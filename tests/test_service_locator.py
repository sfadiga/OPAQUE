# This Python file uses the following encoding: utf-8
"""Tests for the service locator contract."""

import pytest

from opaque.services.console_service import ConsoleService
from opaque.services.logger_service import LoggerService
from opaque.services.notification_service import NotificationService
from opaque.services.service import BaseService, ServiceLocator
from opaque.services.settings_service import SettingsService
from opaque.services.single_instance_service import SingleInstanceService
from opaque.services.theme_service import ThemeService
from opaque.services.version_service import VersionManager
from opaque.services.workspace_service import WorkspaceService

SERVICE_CLASSES = [
    ConsoleService,
    LoggerService,
    NotificationService,
    SettingsService,
    SingleInstanceService,
    ThemeService,
    VersionManager,
    WorkspaceService,
]

EXPECTED_NAMES = {
    ConsoleService: "console",
    LoggerService: "logger",
    NotificationService: "notification",
    SettingsService: "settings",
    SingleInstanceService: "single_instance",
    ThemeService: "themes",
    VersionManager: "version",
    WorkspaceService: "workspace",
}


@pytest.fixture(autouse=True)
def empty_locator():
    """Give every test an empty locator and put nothing back."""
    ServiceLocator.cleanup_services()
    yield
    ServiceLocator.cleanup_services()


@pytest.mark.parametrize("service_class", SERVICE_CLASSES)
def test_every_service_declares_a_name(service_class):
    assert service_class.SERVICE_NAME != ""


@pytest.mark.parametrize("service_class", SERVICE_CLASSES)
def test_the_declared_name_is_the_registered_name(service_class):
    assert service_class.SERVICE_NAME == EXPECTED_NAMES[service_class]


def test_the_base_class_declares_no_name():
    assert BaseService.SERVICE_NAME == ""


def test_an_instance_reports_the_declared_name(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    assert service.name == "settings"


def test_get_returns_the_registered_service(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    ServiceLocator.register_service(service)

    assert ServiceLocator.get(SettingsService) is service


def test_get_answers_with_the_type_that_was_asked_for(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    ServiceLocator.register_service(service)

    found = ServiceLocator.get(SettingsService)
    assert isinstance(found, SettingsService)


def test_get_raises_when_the_service_is_missing():
    with pytest.raises(LookupError) as error:
        ServiceLocator.get(SettingsService)

    message = str(error.value)
    assert "SettingsService" in message
    assert "settings" in message


def test_the_missing_service_message_lists_what_is_registered(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    ServiceLocator.register_service(service)

    with pytest.raises(LookupError) as error:
        ServiceLocator.get(NotificationService)

    assert "settings" in str(error.value)


def test_get_optional_answers_none_when_the_service_is_missing():
    assert ServiceLocator.get_optional(ConsoleService) is None


def test_get_optional_returns_the_registered_service(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    ServiceLocator.register_service(service)

    assert ServiceLocator.get_optional(SettingsService) is service


def test_get_raises_when_another_class_holds_the_name(tmp_path):
    class _Impostor(BaseService):
        SERVICE_NAME = "settings"

        def initialize(self) -> None:
            super().initialize()

        def cleanup(self) -> None:
            super().cleanup()

    impostor = _Impostor()
    impostor.initialize()
    ServiceLocator.register_service(impostor)

    with pytest.raises(TypeError) as error:
        ServiceLocator.get(SettingsService)

    assert "_Impostor" in str(error.value)


def test_a_service_whose_name_does_not_match_its_class_is_refused(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    service._name = "something_else"

    with pytest.raises(ValueError) as error:
        ServiceLocator.register_service(service)

    assert "something_else" in str(error.value)


def test_the_string_lookup_is_gone():
    assert not hasattr(ServiceLocator, "get_service")
