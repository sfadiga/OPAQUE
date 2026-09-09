# This Python file uses the following encoding: utf-8
"""The build guide must describe the real build options."""

import dataclasses
from pathlib import Path

import pytest

from opaque.build_tools.config import BuildConfig

GUIDE = Path("docs/BUILD_GUIDE.md")
FIELDS = list(dataclasses.fields(BuildConfig))


@pytest.fixture(scope="module")
def guide_text():
    return GUIDE.read_text(encoding="utf-8")


@pytest.mark.parametrize("field", FIELDS, ids=lambda entry: entry.name)
def test_every_option_is_documented(field, guide_text):
    assert field.name in guide_text


@pytest.mark.parametrize("field", FIELDS, ids=lambda entry: entry.name)
def test_every_option_says_which_backend_uses_it(field, guide_text):
    # The row for the field must be on one line with its backend mark. A
    # bare substring search would also match the usage example
    # (`--name MyApplication` contains "name"), so look at table rows only.
    for line in guide_text.splitlines():
        if line.startswith("|") and f"`{field.name}`" in line:
            assert field.metadata["backend"] in line
            return
    pytest.fail(f"{field.name} has no row")


def test_the_guide_names_the_one_build_command(guide_text):
    assert "opaque-build build" in guide_text


def test_the_guide_names_the_backend_flag(guide_text):
    assert "--backend" in guide_text


def test_the_guide_names_no_removed_subcommand(guide_text):
    assert "opaque-build pyinstaller" not in guide_text
    assert "opaque-build nuitka" not in guide_text


def test_the_guide_names_no_ghost_function(guide_text):
    for ghost in ("build_executable", "opaque.core"):
        assert ghost not in guide_text
