# This Python file uses the following encoding: utf-8
"""Shared fixtures for the view tests."""

from datetime import datetime

import pytest

from opaque.services.notification_service import Notification, NotificationLevel


@pytest.fixture
def make_notification():
    """
    Return a factory that builds a Notification.

    The default is persistent. A persistent notification starts no auto close
    timer, so a test cannot leave a timer behind that fires after the widget is
    gone. A test that needs the timer must pass persistent=False.
    """
    counter = {"value": 0}

    def _make(
        level: NotificationLevel = NotificationLevel.INFO,
        title: str = "Title",
        message: str = "Message",
        persistent: bool = True,
    ) -> Notification:
        counter["value"] += 1
        return Notification(
            id=f"test-{counter['value']}",
            level=level,
            title=title,
            message=message,
            source="Test",
            timestamp=datetime(2026, 9, 7, 12, 30, 45),
            persistent=persistent,
        )

    return _make
