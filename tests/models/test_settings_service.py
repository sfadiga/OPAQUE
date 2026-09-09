# This Python file uses the following encoding: utf-8
"""Tests for SettingsService robustness against a stale settings file."""

import json
import os

import pytest

from opaque.models.abstract_model import AbstractModel
from opaque.models.annotations import Field, FloatField, IntField, StringField
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


class TypedSettingsModel(AbstractModel):
    """A model whose settings fields have real types."""

    count = IntField(default=1, description="Count", settings=True)
    ratio = FloatField(default=0.5, description="Ratio", settings=True)
    label = StringField(default="plain", description="Label", settings=True)
    internal = IntField(default=0, description="Internal")


def test_a_stored_string_arrives_as_the_declared_type(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"demo": {"count": "12", "ratio": "1.25"}}),
        encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        assert model.count == 12
        assert isinstance(model.count, int)
        assert model.ratio == 1.25
    finally:
        service.cleanup()


def test_a_stored_key_that_is_not_a_field_is_ignored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"demo": {"count": 3, "nonsense": 9}}), encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        assert model.count == 3
        assert not hasattr(model, "nonsense")
    finally:
        service.cleanup()


def test_a_field_that_is_not_a_setting_is_not_restored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"demo": {"internal": 99}}), encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        assert model.internal == 0
    finally:
        service.cleanup()


def test_update_feature_settings_ignores_a_key_that_is_not_a_setting(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        service.update_feature_settings("demo", {"internal": 42, "count": 8})
        assert model.count == 8
        assert model.internal == 0
    finally:
        service.cleanup()


def test_update_feature_settings_converts_the_value(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        service.update_feature_settings("demo", {"count": "5"})
        assert model.count == 5
        assert isinstance(model.count, int)
    finally:
        service.cleanup()


def test_load_all_settings_survives_a_value_the_field_refuses(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"demo": {"count": "not a number"}}), encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        service.load_all_settings()
        assert model.count == 1
    finally:
        service.cleanup()


def test_a_non_ascii_value_survives_export_and_import(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        service.update_feature_settings("demo", {"label": "café"})

        exported = tmp_path / "exported.json"
        assert service.export_settings(exported) is True

        other = SettingsService(tmp_path / "other.json")
        other.initialize()
        other_model = TypedSettingsModel()
        other.register_model("demo", other_model)
        assert other.import_settings(exported) is True
        assert other_model.label == "café"
        other.cleanup()
    finally:
        service.cleanup()


def test_the_file_is_read_once_however_many_models_register(tmp_path,
                                                            monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"a": {}, "b": {}}), encoding="utf-8")

    service = SettingsService(path)
    service.initialize()

    reads = []
    real = service.load_settings_file
    monkeypatch.setattr(
        service, "load_settings_file",
        lambda: (reads.append(True), real())[1])

    try:
        for name in ("a", "b", "c"):
            service.register_model(name, TypedSettingsModel())
        assert reads == []
    finally:
        service.cleanup()


def test_registering_a_model_still_fills_it_from_the_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"demo": {"count": 4}}), encoding="utf-8")

    service = SettingsService(path)
    service.initialize()
    model = TypedSettingsModel()
    try:
        service.register_model("demo", model)
        assert model.count == 4
    finally:
        service.cleanup()


def test_building_the_service_touches_no_disk(tmp_path):
    folder = tmp_path / "not_yet"
    SettingsService(folder / "settings.json")

    assert not folder.exists()


def test_initialize_creates_the_folder(tmp_path):
    folder = tmp_path / "later"
    service = SettingsService(folder / "settings.json")
    service.initialize()
    try:
        assert folder.exists()
    finally:
        service.cleanup()


def test_saving_every_feature_writes_the_file_once(tmp_path, monkeypatch):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    try:
        service.register_model("a", TypedSettingsModel())
        service.register_model("b", TypedSettingsModel())

        writes = []
        real = service.save_settings_file
        monkeypatch.setattr(
            service, "save_settings_file",
            lambda: (writes.append(True), real())[1])

        service.save_all_feature_settings()

        assert len(writes) == 1
    finally:
        service.cleanup()
