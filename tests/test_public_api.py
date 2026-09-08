# This Python file uses the following encoding: utf-8
"""
Tests for the public API surface.

A user, and every AI agent, learns a framework from its exports first. An
empty `__init__.py` sends them guessing at deep module paths, and the
codebase itself guessed wrong three times (`opaque.core`).
"""

from pathlib import Path

import opaque

EXPECTED = [
    "BaseApplication",
    "BaseModel",
    "BasePresenter",
    "BaseService",
    "BaseView",
    "BoolField",
    "ChoiceField",
    "DefaultApplicationConfiguration",
    "Field",
    "FloatField",
    "IntField",
    "ListField",
    "ServiceLocator",
    "StringField",
    "UIType",
]


def test_every_promised_name_is_exported():
    missing = [name for name in EXPECTED if name not in opaque.__all__]
    assert missing == []


def test_every_exported_name_resolves():
    """An `__all__` entry that does not resolve is worse than no entry."""
    unresolved = [name for name in opaque.__all__ if not hasattr(opaque, name)]
    assert unresolved == []


def test_the_package_states_its_version():
    assert isinstance(opaque.__version__, str)
    assert opaque.__version__.count(".") >= 2


def test_the_package_ships_a_py_typed_marker():
    marker = Path(opaque.__file__).parent / "py.typed"
    assert marker.is_file()
