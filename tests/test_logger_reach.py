# This Python file uses the following encoding: utf-8
"""The framework's own log records must reach the application log file."""

import logging
from pathlib import Path

import pytest

from opaque.services.logger_service import LoggerService


@pytest.fixture
def service(tmp_path):
    logger_service = LoggerService(
        log_directory=str(tmp_path / "logs"), application_name="reach")
    logger_service.initialize()
    yield logger_service
    logger_service.cleanup()


def _log_text(service) -> str:
    path = service.get_log_file_path()
    assert path is not None
    for handler in logging.getLogger(LoggerService.LOGGER_NAME).handlers:
        handler.flush()
    return Path(path).read_text(encoding="utf-8")


def test_a_record_from_a_framework_module_reaches_the_file(service):
    logging.getLogger("opaque.services.settings_service").warning(
        "the settings file is gone")

    assert "the settings file is gone" in _log_text(service)


def test_a_record_from_a_deep_module_reaches_the_file(service):
    logging.getLogger("opaque.view.widgets.toolbar").error("no icon")

    assert "no icon" in _log_text(service)


def test_the_service_own_log_call_still_reaches_the_file(service):
    service.log("INFO", "started", source="Test")

    assert "started" in _log_text(service)


def test_a_record_from_another_library_does_not_reach_the_file(service):
    logging.getLogger("some_other_library").error("not ours")

    assert "not ours" not in _log_text(service)


def test_the_framework_logger_does_not_also_print_through_the_root(service):
    assert logging.getLogger(LoggerService.LOGGER_NAME).propagate is False
