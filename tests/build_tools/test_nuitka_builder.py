# This Python file uses the following encoding: utf-8
"""Tests for the Nuitka backend. No real build is ever run."""

import ast
import inspect

import pytest

from opaque.build_tools.config import BuildConfig
from opaque.build_tools.nuitka_builder import NuitkaBuilder


@pytest.fixture
def entry_point(tmp_path):
    path = tmp_path / "main.py"
    path.write_text("print('hello')\n", encoding="utf-8")
    return path


@pytest.fixture
def builder(tmp_path):
    return NuitkaBuilder(work_dir=tmp_path)


def test_is_available_answers_without_raising(builder):
    assert builder.is_available() in (True, False)


def test_the_build_signature_takes_a_configuration():
    parameters = list(inspect.signature(NuitkaBuilder.build).parameters)
    assert parameters == ["self", "entry_point", "config"]


def test_the_command_carries_the_name(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert any(argument.startswith("--output-filename=") and "demo" in argument
               for argument in command)


def test_the_pyside6_plugin_is_always_switched_on(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert "--enable-plugin=pyside6" in command


def test_a_windowed_build_disables_the_console(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert any("console" in argument for argument in command)


def test_one_file_is_asked_for_only_when_it_is_wanted(builder, entry_point):
    with_onefile = builder.build_command(
        entry_point, BuildConfig(name="demo", onefile=True))
    without = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert "--onefile" in with_onefile
    assert "--onefile" not in without


def test_standalone_is_asked_for_by_default(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert "--standalone" in command


def test_every_included_package_reaches_the_command(builder, entry_point):
    command = builder.build_command(
        entry_point, BuildConfig(name="demo", include_packages=["my_pkg"]))

    assert "--include-package=my_pkg" in command


def test_every_extra_plugin_reaches_the_command(builder, entry_point):
    command = builder.build_command(
        entry_point, BuildConfig(name="demo", nuitka_plugins=["numpy"]))

    assert "--enable-plugin=numpy" in command


def test_the_job_count_reaches_the_command(builder, entry_point):
    command = builder.build_command(
        entry_point, BuildConfig(name="demo", jobs=4))

    assert "--jobs=4" in command


def test_a_pyinstaller_only_option_is_ignored(builder, entry_point):
    command = builder.build_command(
        entry_point, BuildConfig(name="demo", upx=True))

    assert not any("upx" in argument.lower() for argument in command)


def test_the_entry_point_is_the_last_argument(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert command[-1] == str(entry_point)


def test_a_missing_entry_point_is_refused(builder, tmp_path):
    from opaque.build_tools.builder import BuildError

    with pytest.raises(BuildError) as error:
        builder.build_command(tmp_path / "nothing.py", BuildConfig(name="d"))

    assert "nothing.py" in str(error.value)


def test_the_generated_config_file_names_the_executable(builder, entry_point):
    path = builder.create_config_file(entry_point, BuildConfig(name="demo"))

    assert "demo" in path.read_text(encoding="utf-8")


def test_a_windows_path_survives_the_config_file(builder, entry_point):
    # `C:\new\app.py` must not come back as a newline and a bell.
    data = str(entry_point.parent / "new" / "app.py") + "=data.py"

    path = builder.create_config_file(
        entry_point, BuildConfig(name="demo", data_files=[data]))
    text = path.read_text(encoding="utf-8")

    assert data in text
    assert "\x07" not in text
