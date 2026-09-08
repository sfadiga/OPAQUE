# This Python file uses the following encoding: utf-8
"""
One sweep over every widget the framework ships.

Each earlier plan raised the hit targets of one widget. This file stops the
next widget from shipping a target that is too small, or a control that a
screen reader cannot name.
"""

from PySide6.QtWidgets import QAbstractButton, QLineEdit, QTabBar, QWidget

from opaque.view.dialogs.keyboard_map import KeyboardMapDialog
from opaque.view.dialogs.version_info import (
    AboutDialog,
    VersionInfoDialog,
    VersionStatusWidget,
)
from opaque.view.self_check import (
    MINIMUM_TARGET,
    _has_a_readable_label,
    _is_a_platform_internal_button,
)
from opaque.view.widgets.closeable_tab_widget import CloseableTabWidget
from opaque.view.widgets.color_picker import ColorPicker
from opaque.view.widgets.console_widget import ConsoleWidget
from opaque.view.widgets.notification_widget import (
    NotificationListItem,
    SimplifiedNotificationList,
    ToastWidget,
)


def _every_widget(qtbot, make_notification):
    """Build one of each widget the framework ships. Returns name and widget."""
    notification = make_notification()

    # KeyboardMapDialog is Qt-parented to the window it reads shortcuts from,
    # and no longer keeps that window alive itself (see keyboard_map.py for
    # why). A throwaway QWidget() passed straight into the constructor would
    # have no Python reference left the moment the constructor call returns,
    # so it is named here and tracked in widgets below, the same way
    # notification is kept alive by being stored on the widgets that need it.
    keyboard_map_window = QWidget()

    widgets = [
        ("ConsoleWidget", ConsoleWidget()),
        ("ColorPicker", ColorPicker("#336699")),
        ("SimplifiedNotificationList", SimplifiedNotificationList()),
        ("NotificationListItem", NotificationListItem(notification)),
        ("ToastWidget", ToastWidget(notification)),
        ("CloseableTabWidget", CloseableTabWidget(widget_type=QWidget)),
        ("AboutDialog", AboutDialog()),
        ("VersionInfoDialog", VersionInfoDialog()),
        ("VersionStatusWidget", VersionStatusWidget({"version": "1.0"})),
        ("KeyboardMapDialog", KeyboardMapDialog(keyboard_map_window)),
        ("_KeyboardMapDialogWindow", keyboard_map_window),
    ]

    for _name, widget in widgets:
        qtbot.addWidget(widget)
        if isinstance(widget, ToastWidget):
            # This toast is inspected, never closed by a presenter. Left
            # alone, its auto-dismiss timer and fade animation stay armed
            # after this test ends and can fire during a later test's event
            # loop, against an object this test has already torn down.
            widget.close_timer.stop()
            widget.anim.stop()
    return widgets


def _is_a_tab_bar_button(button) -> bool:
    """A tab close button is sized by the platform style, not by this code."""
    return isinstance(button.parent(), QTabBar)


def test_no_button_is_capped_below_the_minimum_target(
        qtbot, light_palette_app, make_notification):
    offenders = []
    for name, widget in _every_widget(qtbot, make_notification):
        for button in widget.findChildren(QAbstractButton):
            if _is_a_tab_bar_button(button) or _is_a_platform_internal_button(button):
                continue
            cap = button.maximumSize()
            if cap.width() < MINIMUM_TARGET or cap.height() < MINIMUM_TARGET:
                label = button.text() or button.accessibleName() or "unnamed"
                offenders.append(
                    f"{name}: '{label}' capped at "
                    f"{cap.width()}x{cap.height()}"
                )
    assert offenders == []


def test_every_button_can_be_announced(
        qtbot, light_palette_app, make_notification):
    offenders = []
    for name, widget in _every_widget(qtbot, make_notification):
        for button in widget.findChildren(QAbstractButton):
            if _is_a_tab_bar_button(button) or _is_a_platform_internal_button(button):
                continue
            if not _has_a_readable_label(button):
                offenders.append(f"{name}: '{button.text()}'")
    assert offenders == []


def test_every_text_box_has_an_accessible_name(
        qtbot, light_palette_app, make_notification):
    offenders = []
    for name, widget in _every_widget(qtbot, make_notification):
        for box in widget.findChildren(QLineEdit):
            if not box.accessibleName().strip():
                offenders.append(f"{name}: a QLineEdit with no name")
    assert offenders == []
