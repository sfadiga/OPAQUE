# This Python file uses the following encoding: utf-8
"""
Build the reference example application headless.

The example is the only worked example the review trusts, so it is the
contract a user copies. This test builds the window, checks that the
features registered, and closes it. It does not enter the event loop.

ServiceLocator is a process wide singleton that refuses a second
registration, and tests/test_application_shell.py already builds one
BaseApplication for the session. This test therefore clears the locator
first and puts it back afterwards.
"""

import sys
from pathlib import Path

import pytest

from opaque.services.service import ServiceLocator

EXAMPLE_DIR = Path(__file__).resolve().parent.parent / "examples" / "basic_example"


@pytest.fixture
def isolated_locator():
    """
    Give the test an empty service locator and restore the old one.

    This reaches into the private `_services` dict on purpose. The locator
    has no public reset API, and adding one belongs to the plan that makes
    service access typed. Do not replace this with an ad hoc public method.

    The teardown calls `cleanup_services()` before it restores, and the
    order is load bearing. Before the restore, `_services` holds only what
    this test registered, so `cleanup()` runs on those and nothing else.
    After the restore it would hold the session wide services that
    tests/test_application_shell.py still depends on, and cleaning those up
    would close a log handler that a live BaseApplication still expects to
    work.

    Without this, a failure part way through building the application would
    drop half-registered services with no `cleanup()`, and on Windows that
    can leave an open file handle behind.
    """
    saved = dict(ServiceLocator._services)
    ServiceLocator._services.clear()
    yield
    ServiceLocator.cleanup_services()
    ServiceLocator._services.update(saved)


def test_the_example_application_builds(qapp, isolated_locator, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(EXAMPLE_DIR))
    try:
        import importlib

        module = importlib.import_module("main")
        window = module.MyExampleApplication()
        try:
            registered = window._registered_features
            # Exact key membership, not a substring of a stringified list.
            # A substring match passed even when most features failed to
            # register, because one surviving key was enough.
            assert "Calculator" in registered, sorted(registered)
            # The example is the documentation, so its feature set is the
            # contract. Adding a feature to the example means updating this
            # set, and that is the point.
            expected = {
                "ApplicationPresenter",
                "Calculator",
                "Console",
                "Data Viewer",
                "Logging",
                "Notification Tester",
                "Tab Manager",
            }
            assert set(registered) == expected, sorted(registered)
        finally:
            window.close()
            window.deleteLater()
    finally:
        sys.path.remove(str(EXAMPLE_DIR))
        for name in [m for m in sys.modules if m in ("main", "features") or m.startswith("features.")]:
            del sys.modules[name]
