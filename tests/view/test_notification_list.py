# This Python file uses the following encoding: utf-8
"""Tests for the notification list widget."""

import pytest

from opaque.services.notification_service import NotificationLevel, NotificationService
from opaque.services.service import ServiceLocator
from opaque.view.widgets.notification_widget import SimplifiedNotificationList


class _FakeNotificationService(NotificationService):
    """Records the calls the widget makes, so a test can check them.

    Subclasses the real service instead of duck typing it, because
    ServiceLocator.get(NotificationService) now checks isinstance().
    """

    def __init__(self):
        super().__init__()
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


def test_a_new_list_shows_every_level(qtbot, light_palette_app, fake_service):
    widget = SimplifiedNotificationList()
    qtbot.addWidget(widget)
    assert widget.level_filter() is None


def test_filtering_hides_the_other_levels(
        qtbot, light_palette_app, fake_service, make_notification):
    widget = SimplifiedNotificationList()
    qtbot.addWidget(widget)
    widget.add_notification(make_notification(NotificationLevel.ERROR))
    widget.add_notification(make_notification(NotificationLevel.DEBUG))

    widget.set_level_filter(NotificationLevel.ERROR)

    visible = [
        item for item in widget.items.values() if item.isVisibleTo(widget)
    ]
    assert len(visible) == 1
    assert visible[0].notification.level is NotificationLevel.ERROR


def test_clearing_the_filter_shows_everything_again(
        qtbot, light_palette_app, fake_service, make_notification):
    widget = SimplifiedNotificationList()
    qtbot.addWidget(widget)
    widget.add_notification(make_notification(NotificationLevel.ERROR))
    widget.add_notification(make_notification(NotificationLevel.DEBUG))

    widget.set_level_filter(NotificationLevel.ERROR)
    widget.set_level_filter(None)

    visible = [
        item for item in widget.items.values() if item.isVisibleTo(widget)
    ]
    assert len(visible) == 2


def test_a_notification_added_while_filtering_obeys_the_filter(
        qtbot, light_palette_app, fake_service, make_notification):
    widget = SimplifiedNotificationList()
    qtbot.addWidget(widget)
    widget.set_level_filter(NotificationLevel.ERROR)

    widget.add_notification(make_notification(NotificationLevel.DEBUG))

    item = list(widget.items.values())[0]
    assert not item.isVisibleTo(widget)


def test_the_list_item_repaints_after_a_theme_change(qtbot, make_notification,
                                                     light_palette_app):
    # light_palette_app restores the session palette on teardown; a raw
    # QApplication.setPalette left the dark palette behind for every
    # later test in the session.
    from opaque.view.theme import build_dark_palette
    from opaque.view.widgets.notification_widget import NotificationListItem

    item = NotificationListItem(make_notification())
    qtbot.addWidget(item)
    before = item.level_label.styleSheet()

    light_palette_app.setPalette(build_dark_palette())
    item.apply_theme()

    assert item.level_label.styleSheet() != before
