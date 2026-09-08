# This Python file uses the following encoding: utf-8
"""Tests for the type scale."""

import pytest
from PySide6.QtGui import QFont

from opaque.view.theme.type_scale import TypeScale


@pytest.fixture
def scaled_app(qapp):
    """Give the application a known 10 point base font, then restore it."""
    original = qapp.font()
    base = QFont(original)
    base.setPointSizeF(10.0)
    qapp.setFont(base)
    yield qapp
    qapp.setFont(original)


def test_body_matches_the_application_font_size(scaled_app):
    assert TypeScale.body().pointSizeF() == pytest.approx(10.0)


def test_the_scale_grows_by_the_ratio(scaled_app):
    assert TypeScale.h2().pointSizeF() == pytest.approx(10.0 * 1.2)
    assert TypeScale.h1().pointSizeF() == pytest.approx(10.0 * 1.2 * 1.2)


def test_the_scale_is_ordered(scaled_app):
    sizes = [
        TypeScale.caption().pointSizeF(),
        TypeScale.body().pointSizeF(),
        TypeScale.h2().pointSizeF(),
        TypeScale.h1().pointSizeF(),
        TypeScale.display().pointSizeF(),
    ]
    assert sizes == sorted(sizes)


def test_nothing_drops_below_the_minimum(qapp):
    original = qapp.font()
    tiny = QFont(original)
    tiny.setPointSizeF(6.0)
    qapp.setFont(tiny)
    try:
        assert TypeScale.caption().pointSizeF() >= TypeScale.MINIMUM_POINT_SIZE
    finally:
        qapp.setFont(original)


def test_the_scale_follows_the_operating_system_font_scale(qapp):
    original = qapp.font()
    try:
        large = QFont(original)
        large.setPointSizeF(20.0)
        qapp.setFont(large)
        assert TypeScale.body().pointSizeF() == pytest.approx(20.0)
    finally:
        qapp.setFont(original)


def test_monospace_does_not_hardcode_a_family(scaled_app):
    mono = TypeScale.mono()
    assert mono.family() not in ("Consolas", "Courier")
    assert mono.pointSizeF() == pytest.approx(10.0)


def test_emphasis_raises_the_weight_without_changing_the_size(scaled_app):
    plain = TypeScale.body()
    strong = TypeScale.emphasis(plain)
    assert strong.pointSizeF() == pytest.approx(plain.pointSizeF())
    assert strong.weight() > plain.weight()
