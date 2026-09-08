# This Python file uses the following encoding: utf-8
"""Tests for the palette-derived colour tokens."""

from opaque.view.theme.tokens import (
    interactive,
    is_dark_theme,
    on_interactive,
    on_surface,
    outline,
    surface,
)


def test_light_palette_is_not_reported_as_dark(light_palette_app):
    assert is_dark_theme() is False


def test_dark_palette_is_reported_as_dark(dark_palette_app):
    assert is_dark_theme() is True


def test_surface_comes_from_the_palette_base_role(light_palette_app):
    assert surface() == "#ffffff"


def test_on_surface_comes_from_the_palette_text_role(light_palette_app):
    assert on_surface() == "#1a1a1a"


def test_outline_comes_from_the_palette_mid_role(light_palette_app):
    assert outline() == "#b0b0b0"


def test_interactive_pair_comes_from_the_highlight_roles(light_palette_app):
    assert interactive() == "#0b6ba8"
    assert on_interactive() == "#ffffff"


def test_surface_follows_the_dark_palette(dark_palette_app):
    assert surface() == "#1e1e1e"
    assert on_surface() == "#e0e0e0"
