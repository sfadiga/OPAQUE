# This Python file uses the following encoding: utf-8
"""Tests for the notification list widget."""

import pytest

from opaque.services.service import ServiceLocator
from opaque.view.widgets.notification_widget import SimplifiedNotificationList


class _FakeNotificationService:
    """Records the calls the widget makes, so a test can check them."""

    def __init__(self):
        self.clear_calls = 0
        self.removed_ids = []

    def clear_notifications(self, level_filter=None):
        self.clear_calls += 1

    def remove_notification(self, notification_id):
        self.removed_ids.append(notification_id)


@pytest.fixture
def fake_service():
    """Put a recording service in the locator for the length of one test."""
    previous = ServiceLocator._services.get("notification")
    service = _FakeNotificationService()
    ServiceLocator._services["notification"] = service
    yield service
    if previous is None:
        ServiceLocator._services.pop("notification", None)
    else:
        ServiceLocator._services["notification"] = previous


def _list_with_one_item(qtbot, make_notification):
    widget = SimplifiedNotificationList()
    qtbot.addWidget(widget)
    widget.add_notification(make_notification())
    return widget


def test_clear_all_does_not_ask_when_the_list_is_empty(
        qtbot, light_palette_app, fake_service):
    widget = SimplifiedNotificationList()
    qtbot.addWidget(widget)
    asked = []
    widget._confirm_clear_all = lambda: asked.append(True) or True

    widget._clear_all()

    assert asked == []
    assert fake_service.clear_calls == 0


def test_clear_all_asks_before_removing_items(
        qtbot, light_palette_app, fake_service, make_notification):
    widget = _list_with_one_item(qtbot, make_notification)
    asked = []
    widget._confirm_clear_all = lambda: asked.append(True) or True

    widget._clear_all()

    assert asked == [True]


def test_declining_the_confirmation_leaves_the_service_untouched(
        qtbot, light_palette_app, fake_service, make_notification):
    widget = _list_with_one_item(qtbot, make_notification)
    widget._confirm_clear_all = lambda: False

    widget._clear_all()

    assert fake_service.clear_calls == 0


def test_accepting_the_confirmation_calls_the_service(
        qtbot, light_palette_app, fake_service, make_notification):
    widget = _list_with_one_item(qtbot, make_notification)
    widget._confirm_clear_all = lambda: True

    widget._clear_all()

    assert fake_service.clear_calls == 1
