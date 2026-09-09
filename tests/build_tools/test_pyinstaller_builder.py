# This Python file uses the following encoding: utf-8
"""Tests for the PyInstaller backend. No real build is ever run."""

import ast

import pytest

from opaque.build_tools.config import BuildConfig
from opaque.build_tools.pyinstaller_builder import PyInstallerBuilder


@pytest.fixture
def entry_point(tmp_path):
    path = tmp_path / "main.py"
    path.write_text("print('hello')\n", encoding="utf-8")
    return path


@pytest.fixture
def builder(tmp_path):
    return PyInstallerBuilder(work_dir=tmp_path)


def test_is_available_answers_without_raising(builder):
    assert builder.is_available() in (True, False)


def test_the_build_signature_takes_a_configuration():
    import inspect

    parameters = list(
        inspect.signature(PyInstallerBuilder.build).parameters)
    assert parameters == ["self", "entry_point", "config"]


def test_the_command_carries_the_name(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert "--name" in command
    assert "demo" in command


def test_one_file_is_asked_for_only_when_it_is_wanted(builder, entry_point):
    with_onefile = builder.build_command(
        entry_point, BuildConfig(name="demo", onefile=True))
    without = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert "--onefile" in with_onefile
    assert "--onefile" not in without


def test_a_windowed_build_asks_for_no_console(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert "--windowed" in command
    assert "--console" not in command


def test_a_console_build_asks_for_a_console(builder, entry_point):
    command = builder.build_command(
        entry_point, BuildConfig(name="demo", console=True))

    assert "--console" in command
    assert "--windowed" not in command


def test_every_excluded_module_reaches_the_command(builder, entry_point):
    command = builder.build_command(
        entry_point,
        BuildConfig(name="demo", exclude_modules=["tkinter", "numpy"]))

    text = " ".join(command)
    assert "tkinter" in text
    assert "numpy" in text


def test_every_hidden_import_reaches_the_command(builder, entry_point):
    command = builder.build_command(
        entry_point, BuildConfig(name="demo", hidden_imports=["my_plugin"]))

    assert "my_plugin" in " ".join(command)


def test_the_entry_point_is_the_last_argument(builder, entry_point):
    command = builder.build_command(entry_point, BuildConfig(name="demo"))

    assert command[-1] == str(entry_point)


@pytest.mark.parametrize("onefile", [True, False])
@pytest.mark.parametrize("icon", [None, "app.ico"])
def test_the_generated_spec_file_is_valid_python(
        builder, entry_point, onefile, icon):
    config = BuildConfig(name="demo", onefile=onefile, icon=icon)

    spec = builder.create_spec_file(entry_point, config)

    ast.parse(spec.read_text(encoding="utf-8"))


def test_the_spec_file_names_the_executable(builder, entry_point):
    spec = builder.create_spec_file(entry_point, BuildConfig(name="demo"))

    assert "demo" in spec.read_text(encoding="utf-8")


def test_a_missing_entry_point_is_refused(builder, tmp_path):
    from opaque.build_tools.builder import BuildError

    with pytest.raises(BuildError) as error:
        builder.build_command(tmp_path / "nothing.py", BuildConfig(name="d"))

    assert "nothing.py" in str(error.value)


def test_a_windows_path_survives_the_spec(builder, tmp_path):
    # `C:\new\app.py` must not come back as a newline and a bell.
    entry = tmp_path / "new" / "app.py"
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_text("print('hello')\n", encoding="utf-8")

    spec = builder.create_spec_file(entry, BuildConfig(name="demo"))

    literals = [
        node.value
        for node in ast.walk(ast.parse(spec.read_text(encoding="utf-8")))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    assert str(entry) in literals
