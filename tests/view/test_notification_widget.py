# This Python file uses the following encoding: utf-8
"""Tests for the toast widget and the notification list item."""

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from opaque.services.notification_service import NotificationLevel
from opaque.view.theme import StatusRole, status_colors
from opaque.view.theme import contrast_ratio, surface
from opaque.view.theme.contrast import TEXT_CONTRAST_MINIMUM
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


def test_the_timestamp_is_not_a_grey_literal(
        qtbot, light_palette_app, make_notification):
    item = NotificationListItem(make_notification())
    qtbot.addWidget(item)
    sheet = item.time_label.styleSheet()
    assert "gray" not in sheet
    assert "font-size" not in sheet


def test_the_timestamp_passes_contrast_on_a_light_surface(
        qtbot, light_palette_app, make_notification):
    item = NotificationListItem(make_notification())
    qtbot.addWidget(item)
    ratio = contrast_ratio(item.timestamp_colour, surface())
    assert ratio >= TEXT_CONTRAST_MINIMUM


def test_the_timestamp_passes_contrast_on_a_dark_surface(
        qtbot, dark_palette_app, make_notification):
    item = NotificationListItem(make_notification())
    qtbot.addWidget(item)
    ratio = contrast_ratio(item.timestamp_colour, surface())
    assert ratio >= TEXT_CONTRAST_MINIMUM


def test_the_list_item_close_button_is_large_enough(
        qtbot, light_palette_app, make_notification):
    item = NotificationListItem(make_notification())
    qtbot.addWidget(item)
    assert item.close_button.width() >= NotificationListItem.CLOSE_BUTTON_SIZE
    assert NotificationListItem.CLOSE_BUTTON_SIZE >= 24


def test_the_toast_close_button_is_large_enough(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification())
    qtbot.addWidget(toast)
    assert toast.close_button.width() >= 24
    assert toast.close_button.height() >= 24


def test_both_close_buttons_have_an_accessible_name(
        qtbot, light_palette_app, make_notification):
    item = NotificationListItem(make_notification())
    qtbot.addWidget(item)
    toast = ToastWidget(make_notification())
    qtbot.addWidget(toast)
    assert item.close_button.accessibleName() != ""
    assert toast.close_button.accessibleName() != ""


def test_closed_is_not_emitted_immediately_on_close(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification())
    qtbot.addWidget(toast)
    seen = []
    toast.closed.connect(seen.append)

    toast.close_toast()

    assert seen == []


def test_closed_is_emitted_after_the_fade_out_finishes(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification())
    qtbot.addWidget(toast)

    with qtbot.waitSignal(toast.closed, timeout=2000) as blocker:
        toast.close_toast()

    assert blocker.args == [toast.notification.id]


def test_closing_twice_emits_closed_once(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification())
    qtbot.addWidget(toast)
    seen = []
    toast.closed.connect(seen.append)

    with qtbot.waitSignal(toast.closed, timeout=2000):
        toast.close_toast()
        toast.close_toast()
    qtbot.wait(400)

    assert seen == [toast.notification.id]


def test_escape_closes_the_toast(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification())
    qtbot.addWidget(toast)
    escape = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Escape,
        Qt.KeyboardModifier.NoModifier,
    )

    with qtbot.waitSignal(toast.closed, timeout=2000):
        toast.keyPressEvent(escape)


def test_info_closes_after_four_seconds():
    assert ToastWidget.duration_for_level(NotificationLevel.INFO) == 4000
    assert ToastWidget.duration_for_level(NotificationLevel.DEBUG) == 4000


def test_warning_stays_longer_than_info():
    warning = ToastWidget.duration_for_level(NotificationLevel.WARNING)
    info = ToastWidget.duration_for_level(NotificationLevel.INFO)
    assert warning > info


def test_error_stays_longer_than_warning():
    error = ToastWidget.duration_for_level(NotificationLevel.ERROR)
    warning = ToastWidget.duration_for_level(NotificationLevel.WARNING)
    assert error > warning


def test_critical_never_closes_on_its_own():
    assert ToastWidget.duration_for_level(NotificationLevel.CRITICAL) is None


def test_a_persistent_notification_has_no_running_timer(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification(persistent=True))
    qtbot.addWidget(toast)
    assert not toast.close_timer.isActive()


def test_pause_and_resume_control_the_timer(
        qtbot, light_palette_app, make_notification):
    toast = ToastWidget(make_notification(
        NotificationLevel.INFO, persistent=False))
    qtbot.addWidget(toast)
    assert toast.close_timer.isActive()

    toast.pause_auto_close()
    assert not toast.close_timer.isActive()

    toast.resume_auto_close()
    assert toast.close_timer.isActive()

    toast.pause_auto_close()
