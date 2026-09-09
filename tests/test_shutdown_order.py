# This Python file uses the following encoding: utf-8
"""The shutdown order must let a presenter finish its work."""

import pytest

from PySide6.QtGui import QCloseEvent

from opaque.services.service import ServiceLocator


@pytest.fixture(autouse=True)
def _restore_the_locator_after_a_real_shutdown(app_window):
    """
    Heal app_window's own services before this test, and again after it.

    Every test below calls the real closeEvent(), which really tears every
    registered service down, and app_window is session scoped and shared
    with the rest of the suite, so a service this test tore down must be
    alive again once the test is over. The same repair also has to run
    before the test: a fixture elsewhere in the suite
    (tests/test_notification_settings.py's "services" fixture) clears the
    process wide ServiceLocator without saving or restoring what it
    removed, which tears down app_window's real services too if that file's
    tests happen to run first. Reading them back off app_window's own
    attributes and re-initialising them is what makes this file's outcome
    independent of what ran before it.
    """
    def _heal():
        for service in (
            app_window.single_instance_service,
            app_window.workspace_service,
            app_window.settings_service,
            app_window.logger_service,
        ):
            if not service.is_initialized:
                service.initialize()
            if ServiceLocator.get_service(service.name) is not service:
                ServiceLocator._services[service.name] = service

    _heal()
    yield
    _heal()


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
