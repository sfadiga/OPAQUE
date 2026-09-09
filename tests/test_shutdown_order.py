# This Python file uses the following encoding: utf-8
"""The shutdown order must let a presenter finish its work."""

import pytest

from PySide6.QtGui import QCloseEvent

from opaque.services.service import ServiceLocator
from tests.test_application_shell import app_window  # noqa: F401


@pytest.fixture(autouse=True)
def _restore_the_locator_after_a_real_shutdown():
    """
    Every test below calls the real closeEvent(), which really tears every
    registered service down. app_window is session scoped and shared with
    the rest of the suite, so a service this test tore down must be alive
    again once the test is over, or the next test to touch the locator (in
    this file or any file collected after it) finds it empty.
    """
    saved = dict(ServiceLocator._services)
    yield
    for service in saved.values():
        if not service.is_initialized:
            service.initialize()
    ServiceLocator._services.clear()
    ServiceLocator._services.update(saved)


def test_a_presenter_is_cleaned_up_before_the_services(app_window):
    order = []

    class _Recorder:
        def cleanup(self):
            order.append("presenter")

    app_window._registered_features["recorder"] = _Recorder()

    settings = ServiceLocator.get_service("settings")
    real_cleanup = settings.cleanup

    def _tracked_cleanup():
        order.append("service")
        real_cleanup()

    settings.cleanup = _tracked_cleanup

    app_window.closeEvent(QCloseEvent())

    assert order.index("presenter") < order.index("service")


def test_a_presenter_can_still_reach_a_service_while_closing(app_window):
    seen = []

    class _Saver:
        def cleanup(self):
            seen.append(ServiceLocator.get_service("settings"))

    app_window._registered_features["saver"] = _Saver()

    app_window.closeEvent(QCloseEvent())

    assert seen and seen[0] is not None


def test_a_presenter_that_raises_does_not_stop_the_shutdown(app_window):
    seen = []

    class _Broken:
        def cleanup(self):
            raise RuntimeError("no")

    class _Good:
        def cleanup(self):
            seen.append(True)

    app_window._registered_features["broken"] = _Broken()
    app_window._registered_features["good"] = _Good()

    app_window.closeEvent(QCloseEvent())

    assert seen == [True]
