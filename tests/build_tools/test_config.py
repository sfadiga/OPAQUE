# This Python file uses the following encoding: utf-8
"""Tests for BuildConfig."""

import dataclasses

import pytest

from opaque.build_tools.config import BuildConfig


def test_a_name_is_required():
    with pytest.raises(TypeError):
        BuildConfig()


def test_the_defaults_build_a_windowed_one_folder_application():
    config = BuildConfig(name="demo")

    assert config.name == "demo"
    assert config.onefile is False
    assert config.console is False
    assert config.debug is False


def test_an_unknown_option_is_refused():
    with pytest.raises(TypeError):
        BuildConfig(name="demo", onfile=True)


def test_the_configuration_cannot_be_changed_after_it_is_built():
    config = BuildConfig(name="demo")

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.name = "other"


def test_every_list_option_defaults_to_an_empty_list():
    config = BuildConfig(name="demo")

    assert config.hidden_imports == []
    assert config.exclude_modules == []
    assert config.data_files == []
    assert config.include_packages == []
    assert config.nuitka_plugins == []


def test_two_configurations_do_not_share_a_list():
    first = BuildConfig(name="one")
    second = BuildConfig(name="two")

    first.hidden_imports.append("something")

    assert second.hidden_imports == []


def test_the_version_information_defaults_to_nothing():
    assert BuildConfig(name="demo").version_info is None


def test_a_field_carries_its_own_help_text():
    for field in dataclasses.fields(BuildConfig):
        assert field.metadata.get("help"), f"{field.name} has no help text"


def test_a_field_says_which_backends_use_it():
    allowed = {"both", "pyinstaller", "nuitka"}
    for field in dataclasses.fields(BuildConfig):
        assert field.metadata.get("backend") in allowed, field.name


def test_the_optimisation_level_is_checked():
    with pytest.raises(ValueError):
        BuildConfig(name="demo", optimization=9)


def test_the_job_count_is_checked():
    with pytest.raises(ValueError):
        BuildConfig(name="demo", jobs=0)


def test_an_empty_name_is_refused():
    with pytest.raises(ValueError):
        BuildConfig(name="")
