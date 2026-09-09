# This Python file uses the following encoding: utf-8
"""Tests for SettingsService robustness against a stale settings file."""

import json
import os

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


def test_a_corrupt_settings_file_is_kept_beside_the_new_one(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ this is not json", encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    try:
        assert service.get_all_settings() == {}
        kept = path.with_suffix(".json.corrupt")
        assert kept.exists()
        assert kept.read_text(encoding="utf-8") == "{ this is not json"
    finally:
        service.cleanup()


def test_a_corrupt_file_is_not_left_in_place_to_fail_again(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ broken", encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    try:
        service.update_feature_settings("demo", {})
        # The service wrote a fresh file, so the next start parses.
        json.loads(path.read_text(encoding="utf-8"))
    finally:
        service.cleanup()


def test_a_failed_write_leaves_the_previous_file_untouched(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"demo": {"mode": "slow"}}), encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    try:
        def _explode(*args, **kwargs):
            raise OSError("the disk is full")

        monkeypatch.setattr(
            "opaque.services.settings_service.json.dump", _explode)

        service.save_settings_file()

        # The old content is still there, and no half written file replaced it.
        assert json.loads(path.read_text(encoding="utf-8")) == {
            "demo": {"mode": "slow"}}
    finally:
        service.cleanup()


def test_a_save_leaves_no_temporary_file_behind(tmp_path):
    path = tmp_path / "settings.json"
    service = SettingsService(path)
    service.initialize()
    try:
        service.update_feature_settings("demo", {})
        names = sorted(entry.name for entry in tmp_path.iterdir())
        assert names == ["settings.json"]
    finally:
        service.cleanup()


def test_a_read_failure_does_not_empty_the_settings_already_held(tmp_path,
                                                                monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"demo": {"mode": "slow"}}), encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    try:
        assert service.get_all_settings() == {"demo": {"mode": "slow"}}

        def _explode(*args, **kwargs):
            raise OSError("the file is locked")

        monkeypatch.setattr(
            "opaque.services.settings_service.open", _explode, raising=False)

        service.load_settings_file()

        assert service.get_all_settings() == {"demo": {"mode": "slow"}}
    finally:
        service.cleanup()
