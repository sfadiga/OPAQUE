# This Python file uses the following encoding: utf-8
"""Tests for the optional theme providers."""

import pytest

from opaque.services.theme_provider import ThemeProvider
from opaque.services.theme_providers import (
    QDarkStyleProvider,
    QtMaterialProvider,
    QtThemesProvider,
    discover_providers,
)
from opaque.view.theme.tokens import is_dark_theme

PROVIDER_CLASSES = [QtThemesProvider, QtMaterialProvider, QDarkStyleProvider]


@pytest.fixture
def clean_app(qapp):
    """Give the test the application, and undo whatever it applied."""
    original_palette = qapp.palette()
    original_sheet = qapp.styleSheet()
    yield qapp
    qapp.setStyleSheet(original_sheet)
    qapp.setPalette(original_palette)


@pytest.mark.parametrize("provider_class", PROVIDER_CLASSES)
def test_every_provider_satisfies_the_protocol(provider_class):
    assert isinstance(provider_class(), ThemeProvider)


@pytest.mark.parametrize("provider_class", PROVIDER_CLASSES)
def test_a_provider_with_a_missing_package_lists_nothing(
        provider_class, monkeypatch):
    monkeypatch.setattr(
        "opaque.services.theme_providers._package_present", lambda name: False)
    assert provider_class().names() == []


@pytest.mark.parametrize("provider_class", PROVIDER_CLASSES)
def test_a_provider_with_a_missing_package_applies_nothing(
        provider_class, monkeypatch, clean_app):
    monkeypatch.setattr(
        "opaque.services.theme_providers._package_present", lambda name: False)
    assert provider_class().apply("anything", clean_app) is False


@pytest.mark.parametrize("provider_class", PROVIDER_CLASSES)
def test_a_provider_refuses_a_name_it_does_not_offer(
        provider_class, clean_app):
    assert provider_class().apply("No Such Theme", clean_app) is False


@pytest.mark.parametrize("provider_class", PROVIDER_CLASSES)
def test_every_name_a_provider_offers_can_be_applied(
        provider_class, clean_app):
    provider = provider_class()
    names = provider.names()
    if not names:
        pytest.skip("the package behind this provider is not installed")
    for name in names:
        assert provider.apply(name, clean_app) is True


def test_discover_providers_returns_only_providers_that_offer_names():
    for provider in discover_providers():
        assert provider.names() != []


def test_a_dark_style_sheet_leaves_the_token_layer_reporting_dark(clean_app):
    provider = QDarkStyleProvider()
    if "QDarkStyle" not in provider.names():
        pytest.skip("QDarkStyle is not installed")
    assert provider.apply("QDarkStyle", clean_app) is True
    assert is_dark_theme() is True


def test_a_light_style_sheet_leaves_the_token_layer_reporting_light(clean_app):
    provider = QDarkStyleProvider()
    if "QLightStyle" not in provider.names():
        pytest.skip("QDarkStyle is not installed")
    assert provider.apply("QLightStyle", clean_app) is True
    assert is_dark_theme() is False


def test_a_dark_material_theme_leaves_the_token_layer_reporting_dark(
        clean_app):
    provider = QtMaterialProvider()
    dark_names = [name for name in provider.names() if name.startswith("dark")]
    if not dark_names:
        pytest.skip("qt-material is not installed")
    assert provider.apply(dark_names[0], clean_app) is True
    assert is_dark_theme() is True


def test_a_light_material_theme_leaves_the_token_layer_reporting_light(
        clean_app):
    provider = QtMaterialProvider()
    light_names = [
        name for name in provider.names() if name.startswith("light")]
    if not light_names:
        pytest.skip("qt-material is not installed")
    assert provider.apply(light_names[0], clean_app) is True
    assert is_dark_theme() is False


def test_the_qt_themes_names_keep_the_historic_prefix(clean_app):
    names = QtThemesProvider().names()
    if not names:
        pytest.skip("qt-themes is not installed")
    for name in names:
        assert name.startswith("qt-themes: ")
