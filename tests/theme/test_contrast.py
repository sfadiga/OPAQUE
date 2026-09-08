# This Python file uses the following encoding: utf-8
"""Tests for the pure WCAG contrast maths."""

import pytest

from opaque.view.theme.contrast import (
    contrast_ratio,
    readable_foreground,
    relative_luminance,
)


def test_black_has_zero_luminance():
    assert relative_luminance("#000000") == pytest.approx(0.0)


def test_white_has_full_luminance():
    assert relative_luminance("#ffffff") == pytest.approx(1.0)


def test_black_on_white_is_the_maximum_ratio():
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0, abs=0.01)


def test_the_ratio_does_not_depend_on_argument_order():
    assert contrast_ratio("#000000", "#ffffff") == contrast_ratio("#ffffff", "#000000")


def test_a_colour_against_itself_is_one_to_one():
    assert contrast_ratio("#3c78a0", "#3c78a0") == pytest.approx(1.0)


def test_mid_grey_on_white_fails_the_text_threshold():
    # This is the exact defect the audit found at notification_widget.py:162.
    assert contrast_ratio("#808080", "#ffffff") < 4.5


def test_readable_foreground_picks_black_on_a_light_background():
    assert readable_foreground("#ffd54f") == "#000000"


def test_readable_foreground_picks_white_on_a_dark_background():
    assert readable_foreground("#0b6ba8") == "#ffffff"
