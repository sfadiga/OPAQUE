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
