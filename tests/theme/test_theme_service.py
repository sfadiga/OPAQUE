# This Python file uses the following encoding: utf-8
"""Tests for the theme service signal and validation."""

import pytest

from opaque.services.theme_service import ThemeService


@pytest.fixture
def theme_service(qapp):
    service = ThemeService(qapp)
    service.initialize()
    yield service
    service.cleanup()


def test_default_theme_is_a_valid_theme_name(theme_service):
    assert theme_service.is_valid_theme(ThemeService.DEFAULT_THEME)


def test_an_unknown_theme_name_is_rejected(theme_service):
    assert theme_service.is_valid_theme("light") is False


def test_apply_theme_reports_success_for_a_known_theme(theme_service):
    assert theme_service.apply_theme("Default") is True


def test_apply_theme_reports_failure_for_an_unknown_theme(theme_service):
    assert theme_service.apply_theme("light") is False


def test_apply_theme_emits_theme_changed_on_success(theme_service, qtbot):
    with qtbot.waitSignal(theme_service.theme_changed, timeout=1000) as blocker:
        theme_service.apply_theme("Default")
    assert blocker.args == ["Default"]


def test_apply_theme_does_not_emit_for_an_unknown_theme(theme_service, qtbot):
    with qtbot.assertNotEmitted(theme_service.theme_changed):
        theme_service.apply_theme("light")


def test_current_theme_tracks_the_last_applied_theme(theme_service):
    theme_service.apply_theme("Default")
    assert theme_service.current_theme() == "Default"
