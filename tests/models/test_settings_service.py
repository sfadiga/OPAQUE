# This Python file uses the following encoding: utf-8
"""Tests for SettingsService robustness against a stale settings file."""

import json

import pytest

from opaque.models.abstract_model import AbstractModel
from opaque.models.annotations import Field
from opaque.services.settings_service import SettingsService


class ChoiceModel(AbstractModel):
    """A model whose field only accepts two values."""

    mode = Field(
        default="fast",
        description="Mode",
        choices=["fast", "slow"],
        settings=True,
    )


@pytest.fixture
def settings_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"demo": {"mode": "gone"}}), encoding="utf-8")
    return path


def test_a_value_outside_choices_does_not_raise(settings_file):
    """
    Defect C4, second half. ModelMeta's setter raises ValueError for a value
    outside choices, and register_model called setattr with no guard. A
    settings file holding an old value stopped the application from starting.
    """
    service = SettingsService(settings_file)
    service.initialize()
    model = ChoiceModel()
    try:
        service.register_model("demo", model)
    finally:
        service.cleanup()


def test_the_field_keeps_its_default_when_the_stored_value_is_rejected(settings_file):
    service = SettingsService(settings_file)
    service.initialize()
    model = ChoiceModel()
    try:
        service.register_model("demo", model)
        assert model.mode == "fast"
    finally:
        service.cleanup()


def test_a_valid_stored_value_is_still_applied(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"demo": {"mode": "slow"}}), encoding="utf-8")
    service = SettingsService(path)
    service.initialize()
    model = ChoiceModel()
    try:
        service.register_model("demo", model)
        assert model.mode == "slow"
    finally:
        service.cleanup()
