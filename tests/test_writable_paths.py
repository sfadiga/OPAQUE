# This Python file uses the following encoding: utf-8
"""No service may write into the working directory."""

from pathlib import Path

from opaque.services.logger_service import LoggerService
from opaque.services.single_instance_service import SingleInstanceService


def test_the_lock_file_is_not_in_the_working_directory(qapp):
    service = SingleInstanceService(app_name="paths")
    path = Path(service.lock_file_path)

    assert path.is_absolute()
    assert path.parent != Path.cwd()


def test_the_lock_file_carries_the_application_name(qapp):
    service = SingleInstanceService(app_name="paths")
    assert "paths" in Path(service.lock_file_path).name


def test_two_services_with_one_name_choose_one_lock(qapp):
    first = SingleInstanceService(app_name="paths")
    second = SingleInstanceService(app_name="paths")
    assert first.lock_file_path == second.lock_file_path


def test_the_log_directory_is_not_in_the_working_directory(qapp):
    service = LoggerService(application_name="paths")
    path = Path(service.get_configuration()["log_directory"])

    assert path.is_absolute()
    assert path.parent != Path.cwd()


def test_an_explicit_log_directory_is_still_honoured(tmp_path, qapp):
    service = LoggerService(
        log_directory=str(tmp_path / "here"), application_name="paths")
    assert str(tmp_path / "here") in service.get_configuration()[
        "log_directory"]
