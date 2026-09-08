# This Python file uses the following encoding: utf-8
"""
Import every module in the package.

This is the cheapest test in the suite and it is the one that was missing.
A module that only a console script imports, or that only an example
imports, was never executed by anything, so a syntax error and a ghost
import both survived a release.

Discovery walks the file system. It does not use `pkgutil.walk_packages`.
Three directories of this package -- `models`, `presenters` and `services`
-- have no `__init__.py`, so they are implicit namespace packages. A
`pkgutil` walk cannot see into them. It found 30 modules out of 52, and
every module it missed was in the model, presenter or service layer. A
test that cannot see the service layer does not do the job this test
exists to do.

`build_tools/templates` is excluded on purpose. Those files are source
templates for a generated application. They are not modules of this
package, and they are not expected to import.
"""

import importlib
from pathlib import Path

import pytest

import opaque

PACKAGE_ROOT = Path(opaque.__file__).resolve().parent
EXCLUDED_PARTS = ("build_tools", "templates")


def _module_names() -> list[str]:
    names = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        relative = path.relative_to(PACKAGE_ROOT)
        if "__pycache__" in relative.parts:
            continue
        if relative.parts[: len(EXCLUDED_PARTS)] == EXCLUDED_PARTS:
            continue
        parts = list(relative.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        if not parts:
            # `opaque/__init__.py` itself. Importing it is how we got here.
            continue
        names.append(".".join(["opaque"] + parts))
    return sorted(set(names))


MODULES = _module_names()


def test_the_walk_found_the_whole_package():
    """
    50 is a floor, not the exact count. It has to be high enough that a
    whole directory going missing from discovery fails this test.
    """
    assert len(MODULES) >= 50


def test_the_walk_reaches_the_namespace_packages():
    """The `pkgutil` walk this replaced could not see any of these three."""
    for name in (
        "opaque.models.abstract_model",
        "opaque.presenters.presenter",
        "opaque.services.service",
    ):
        assert name in MODULES


@pytest.mark.parametrize("module_name", MODULES)
def test_module_imports(module_name):
    importlib.import_module(module_name)
