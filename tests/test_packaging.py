# This Python file uses the following encoding: utf-8
"""
Tests for the project metadata.

The metadata is a promise to a user who runs `pip install opaque-framework`.
A promise nothing checks is how this project came to claim Python 3.8 support
while one module needed 3.12.
"""

import tomllib
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


@pytest.fixture(scope="module")
def metadata() -> dict:
    with open(PYPROJECT, "rb") as handle:
        return tomllib.load(handle)


def test_the_python_floor_is_3_11(metadata):
    """Decision D3. One floor, stated once."""
    assert metadata["project"]["requires-python"] == ">=3.11"


def test_no_classifier_promises_a_python_below_the_floor(metadata):
    classifiers = metadata["project"]["classifiers"]
    unsupported = [
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ]
    assert [c for c in classifiers if c in unsupported] == []


def test_the_project_urls_are_real(metadata):
    for name, url in metadata["project"]["urls"].items():
        assert "yourusername" not in url, f"{name} is still a placeholder"


def test_the_package_data_names_no_ghost_package(metadata):
    """
    `core/py.typed` was packaged for a package `opaque.core` that never
    existed. It is the same ghost the example services import.
    """
    package_data = metadata["tool"]["setuptools"]["package-data"]["opaque"]
    assert "core/py.typed" not in package_data


def test_pytest_finds_the_sources_on_a_fresh_clone(metadata):
    """Bare `pytest` must work before an editable install."""
    assert metadata["tool"]["pytest"]["ini_options"]["pythonpath"] == ["src"]


def test_the_pinned_interpreter_matches_the_declared_floor(metadata):
    """
    `.python-version` tells uv which interpreter to provision, and
    `requires-python` tells a user which ones are supported. Nothing
    connected the two, so they could drift without a failure.
    """
    pinned = (PYPROJECT.parent / ".python-version").read_text(
        encoding="utf-8"
    ).strip()
    assert metadata["project"]["requires-python"] == f">={pinned}"
