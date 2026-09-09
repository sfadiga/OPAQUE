# This Python file uses the following encoding: utf-8
"""Tests for the workspace service lifecycle."""

import pytest

from opaque.services.workspace_service import WorkspaceService


@pytest.fixture
def service():
    workspace = WorkspaceService()
    workspace.initialize()
    return workspace


def test_the_service_reports_itself_ready_after_initialize(service):
    assert service.is_initialized is True


def test_the_service_reports_itself_not_ready_after_cleanup(service):
    service.cleanup()
    assert service.is_initialized is False


def test_cleanup_forgets_every_registered_feature(service):
    class _Presenter:
        feature_id = "demo"

    service.register_feature(_Presenter())
    service.cleanup()

    assert service.save_workspace("unused.json") is None
