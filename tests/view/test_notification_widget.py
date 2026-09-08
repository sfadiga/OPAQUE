# This Python file uses the following encoding: utf-8
"""Tests for the toast widget and the notification list item."""

from opaque.services.notification_service import NotificationLevel
from opaque.view.theme import StatusRole, status_colors
from opaque.view.widgets.notification_widget import (
    NotificationListItem,
    ToastWidget,
    status_role_for_level,
)


def test_each_level_maps_to_a_status_role():
    assert status_role_for_level(NotificationLevel.DEBUG) is StatusRole.NEUTRAL
    assert status_role_for_level(NotificationLevel.INFO) is StatusRole.INFO
    assert status_role_for_level(NotificationLevel.WARNING) is StatusRole.WARNING


def test_critical_and_error_share_the_error_role():
    assert status_role_for_level(NotificationLevel.ERROR) is StatusRole.ERROR
    assert status_role_for_level(NotificationLevel.CRITICAL) is StatusRole.ERROR


def test_the_toast_does_not_use_a_bootstrap_colour(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification(NotificationLevel.ERROR))
    qtbot.addWidget(toast)
    sheet = toast.container.styleSheet()
    assert "#dc3545" not in sheet
    assert "#ffc107" not in sheet
    assert "#0dcaf0" not in sheet
    assert "#6c757d" not in sheet


def test_the_toast_uses_the_status_background(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification(NotificationLevel.ERROR))
    qtbot.addWidget(toast)
    expected = status_colors(StatusRole.ERROR).background
    assert expected in toast.container.styleSheet()


def test_the_list_item_shows_the_level_as_text(
        qtbot, light_palette_app, make_notification):
    item = NotificationListItem(make_notification(NotificationLevel.WARNING))
    qtbot.addWidget(item)
    assert item.level_label.text() == "WARNING"


def test_the_list_item_level_text_follows_the_level(
        qtbot, light_palette_app, make_notification):
    for level in NotificationLevel:
        item = NotificationListItem(make_notification(level))
        qtbot.addWidget(item)
        assert item.level_label.text() == level.value.upper()
