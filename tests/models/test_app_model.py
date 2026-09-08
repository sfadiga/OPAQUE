# This Python file uses the following encoding: utf-8
"""Tests for the application-wide settings model."""

from opaque.models.app_model import ApplicationModel
from opaque.services.theme_service import ThemeService


def test_the_theme_default_is_the_theme_service_default():
    """
    Defect C4. The old default was "light", which no branch of
    ThemeService.apply_theme recognises, so the theme was applied as nothing.
    """
    field = ApplicationModel.get_fields()["theme"]
    assert field.default == ThemeService.DEFAULT_THEME


def test_the_theme_default_is_applicable(qapp):
    service = ThemeService(qapp)
    service.initialize()
    try:
        field = ApplicationModel.get_fields()["theme"]
        assert service.is_valid_theme(field.default)
    finally:
        service.cleanup()


def test_the_language_field_still_offers_its_choices():
    field = ApplicationModel.get_fields()["language"]
    assert field.choices == ["en", "es", "fr"]
