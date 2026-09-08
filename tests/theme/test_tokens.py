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


from opaque.view.theme.contrast import TEXT_CONTRAST_MINIMUM, contrast_ratio
from opaque.view.theme.tokens import muted_on_surface


def test_muted_text_still_passes_contrast_on_a_light_surface(light_palette_app):
    ratio = contrast_ratio(muted_on_surface(), surface())
    assert ratio >= TEXT_CONTRAST_MINIMUM


def test_muted_text_still_passes_contrast_on_a_dark_surface(dark_palette_app):
    ratio = contrast_ratio(muted_on_surface(), surface())
    assert ratio >= TEXT_CONTRAST_MINIMUM


def test_muted_text_is_dimmer_than_primary_text(light_palette_app):
    primary = contrast_ratio(on_surface(), surface())
    muted = contrast_ratio(muted_on_surface(), surface())
    assert muted < primary


def test_plain_grey_would_have_failed(light_palette_app):
    # Proof that the old hardcoded value was the defect, not the idea.
    assert contrast_ratio("#808080", surface()) < TEXT_CONTRAST_MINIMUM
