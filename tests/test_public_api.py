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


def test_the_version_falls_back_when_the_metadata_is_missing():
    """
    A source checkout with no install has no distribution metadata. The
    fallback has to keep the shape every other reader of `__version__`
    expects, which is why it is a version string and not an empty one.

    This runs in a child interpreter on purpose. Reloading `opaque` in
    this process would rebind every exported class, and the service
    locator and the Qt metaclasses in this suite hold references to the
    originals.
    """
    import subprocess
    import sys
    import textwrap

    code = textwrap.dedent(
        """
        import importlib.metadata as metadata

        def _missing(_name):
            raise metadata.PackageNotFoundError

        metadata.version = _missing

        import opaque

        print(opaque.__version__)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "0.0.0+unknown"
    assert result.stdout.strip().count(".") >= 2
