# This Python file uses the following encoding: utf-8
"""Tests for the theme service signal, validation and provider registry."""

import pytest

from PySide6.QtGui import QColor, QPalette

from opaque.services.theme_provider import ThemeProvider
from opaque.services.theme_service import ThemeService
from opaque.view.theme.tokens import is_dark_theme


class _FakeProvider:
    """A provider that lists two names and records what it was asked to apply."""

    def __init__(self, succeed: bool = True) -> None:
        self.succeed = succeed
        self.applied: list = []

    def names(self):
        return ["Fake One", "Fake Two"]

    def apply(self, name, app):
        self.applied.append(name)
        return self.succeed


@pytest.fixture
def theme_service(qapp):
    # A theme applies to the whole QApplication, and the QApplication lives
    # for the whole test session. Save what was there and put it back, or one
    # test decides the colours another test measures.
    original_palette = qapp.palette()
    original_sheet = qapp.styleSheet()
    service = ThemeService(qapp)
    service.initialize()
    yield service
    service.cleanup()
    qapp.setPalette(original_palette)
    qapp.setStyleSheet(original_sheet)


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


def test_the_three_built_in_themes_are_always_available(theme_service):
    names = theme_service.get_available_themes()
    assert "Default" in names
    assert "Light" in names
    assert "Dark" in names


def test_the_dark_theme_makes_the_token_layer_report_dark(theme_service):
    assert theme_service.apply_theme("Dark") is True
    assert is_dark_theme() is True


def test_the_light_theme_makes_the_token_layer_report_light(theme_service):
    assert theme_service.apply_theme("Light") is True
    assert is_dark_theme() is False


def test_a_built_in_theme_clears_a_style_sheet_left_by_another_theme(
        theme_service, qapp):
    qapp.setStyleSheet("QWidget { color: #ff00ff; }")
    theme_service.apply_theme("Light")
    assert qapp.styleSheet() == ""


def test_the_default_theme_restores_the_palette_from_construction(qapp):
    original_palette = qapp.palette()
    original_sheet = qapp.styleSheet()
    marker = QPalette(original_palette)
    marker.setColor(QPalette.ColorRole.Window, QColor("#123456"))
    qapp.setPalette(marker)

    service = ThemeService(qapp)
    service.initialize()
    try:
        service.apply_theme("Dark")
        assert qapp.palette().color(
            QPalette.ColorRole.Window).name() != "#123456"

        service.apply_theme("Default")
        assert qapp.palette().color(
            QPalette.ColorRole.Window).name() == "#123456"
    finally:
        service.cleanup()
        qapp.setPalette(original_palette)
        qapp.setStyleSheet(original_sheet)


def test_a_registered_provider_adds_its_names(theme_service):
    theme_service.register_provider(_FakeProvider())
    assert theme_service.is_valid_theme("Fake One") is True
    assert "Fake Two" in theme_service.get_available_themes()


def test_a_provider_name_is_applied_by_that_provider(theme_service):
    provider = _FakeProvider()
    theme_service.register_provider(provider)
    assert theme_service.apply_theme("Fake One") is True
    assert provider.applied == ["Fake One"]
    assert theme_service.current_theme() == "Fake One"


def test_a_provider_that_fails_leaves_the_current_theme_alone(theme_service):
    theme_service.apply_theme("Light")
    theme_service.register_provider(_FakeProvider(succeed=False))
    assert theme_service.apply_theme("Fake One") is False
    assert theme_service.current_theme() == "Light"


def test_a_provider_that_fails_does_not_emit_theme_changed(
        theme_service, qtbot):
    theme_service.register_provider(_FakeProvider(succeed=False))
    with qtbot.assertNotEmitted(theme_service.theme_changed):
        theme_service.apply_theme("Fake One")


def test_a_plain_object_with_the_two_methods_is_a_theme_provider():
    assert isinstance(_FakeProvider(), ThemeProvider)


def test_the_service_module_names_no_third_party_theme_package():
    import inspect

    from opaque.services import theme_service as module

    source = inspect.getsource(module)
    for package in ("qt_themes", "qdarkstyle", "qt_material"):
        assert package not in source
