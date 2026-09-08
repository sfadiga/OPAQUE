# This Python file uses the following encoding: utf-8
"""Tests for the built-in theme palettes."""

import pytest

from PySide6.QtGui import QPalette

from opaque.view.theme.contrast import (
    TEXT_CONTRAST_MINIMUM,
    contrast_ratio,
    relative_luminance,
)
from opaque.view.theme.palettes import build_dark_palette, build_light_palette

# Every role the token layer in tokens.py reads. A role left at the Qt
# default makes one token answer for a theme the user is not looking at.
TOKEN_ROLES = [
    QPalette.ColorRole.Window,
    QPalette.ColorRole.WindowText,
    QPalette.ColorRole.Base,
    QPalette.ColorRole.Text,
    QPalette.ColorRole.Mid,
    QPalette.ColorRole.Highlight,
    QPalette.ColorRole.HighlightedText,
]

# Each pair is a foreground and the background it is painted on. Every pair
# must pass the WCAG text minimum in both palettes.
TEXT_PAIRS = [
    (QPalette.ColorRole.Text, QPalette.ColorRole.Base),
    (QPalette.ColorRole.WindowText, QPalette.ColorRole.Window),
    (QPalette.ColorRole.ButtonText, QPalette.ColorRole.Button),
    (QPalette.ColorRole.HighlightedText, QPalette.ColorRole.Highlight),
    (QPalette.ColorRole.ToolTipText, QPalette.ColorRole.ToolTipBase),
]

BUILDERS = [build_light_palette, build_dark_palette]


@pytest.mark.parametrize("builder", BUILDERS)
@pytest.mark.parametrize("role", TOKEN_ROLES)
def test_the_palette_sets_every_role_the_tokens_read(builder, role):
    palette = builder()
    assert palette.isBrushSet(QPalette.ColorGroup.Active, role)


@pytest.mark.parametrize("builder", BUILDERS)
@pytest.mark.parametrize("foreground,background", TEXT_PAIRS)
def test_every_text_pair_passes_the_contrast_minimum(
        builder, foreground, background):
    palette = builder()
    ratio = contrast_ratio(
        palette.color(foreground).name(), palette.color(background).name())
    assert ratio >= TEXT_CONTRAST_MINIMUM


def test_the_light_palette_reads_as_a_light_theme():
    window = build_light_palette().color(QPalette.ColorRole.Window).name()
    assert relative_luminance(window) >= 0.18


def test_the_dark_palette_reads_as_a_dark_theme():
    window = build_dark_palette().color(QPalette.ColorRole.Window).name()
    assert relative_luminance(window) < 0.18


def test_a_builder_returns_a_new_palette_every_call():
    first = build_light_palette()
    second = build_light_palette()
    first.setColor(
        QPalette.ColorRole.Window, first.color(QPalette.ColorRole.Base))
    assert (first.color(QPalette.ColorRole.Window).name()
            != second.color(QPalette.ColorRole.Window).name())


@pytest.mark.parametrize("builder", BUILDERS)
def test_the_disabled_group_is_not_the_active_group(builder):
    palette = builder()
    active = palette.color(
        QPalette.ColorGroup.Active, QPalette.ColorRole.Text).name()
    disabled = palette.color(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text).name()
    assert active != disabled
