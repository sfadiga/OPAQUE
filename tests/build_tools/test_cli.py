# This Python file uses the following encoding: utf-8
"""Tests for the build command line. No real build is ever run."""

import pytest

from opaque.build_tools.cli import config_from_args, create_parser, main


def _parse(*arguments):
    return create_parser().parse_args(list(arguments))


def test_the_default_backend_is_pyinstaller():
    arguments = _parse("build", "main.py")
    assert arguments.backend == "pyinstaller"


def test_the_backend_can_be_chosen():
    arguments = _parse("build", "main.py", "--backend", "nuitka")
    assert arguments.backend == "nuitka"


def test_an_unknown_backend_is_refused():
    with pytest.raises(SystemExit):
        _parse("build", "main.py", "--backend", "cython")


def test_the_name_defaults_to_the_entry_point_stem():
    config = config_from_args(_parse("build", "some/app.py"))
    assert config.name == "app"


def test_the_name_can_be_given():
    config = config_from_args(_parse("build", "app.py", "--name", "Bench"))
    assert config.name == "Bench"


def test_a_repeated_option_collects_every_value():
    config = config_from_args(_parse(
        "build", "app.py",
        "--hidden-import", "one",
        "--hidden-import", "two"))
    assert config.hidden_imports == ["one", "two"]


def test_the_flags_reach_the_configuration():
    config = config_from_args(_parse(
        "build", "app.py", "--onefile", "--console", "--debug"))
    assert config.onefile is True
    assert config.console is True
    assert config.debug is True


def test_the_defaults_are_the_configuration_defaults():
    config = config_from_args(_parse("build", "app.py"))
    assert config.onefile is False
    assert config.console is False
    assert config.jobs == 1


def test_a_bad_optimisation_level_is_reported_and_not_a_traceback(capsys):
    exit_code = main(["build", "app.py", "--optimization", "9"])

    assert exit_code != 0
    assert "optimization" in capsys.readouterr().out.lower()


def test_no_command_prints_the_help(capsys):
    exit_code = main([])

    assert exit_code == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_the_info_command_still_works():
    assert main(["info"]) == 0


def test_the_two_old_subcommands_are_gone():
    with pytest.raises(SystemExit):
        _parse("pyinstaller", "app.py")
