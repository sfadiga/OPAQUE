# This Python file uses the following encoding: utf-8
"""The console must not ask the locator for a name nothing registers."""

import inspect

from opaque.presenters import console_presenter
from opaque.services.theme_service import ThemeService


def test_the_theme_service_is_registered_as_themes(qapp):
    assert ThemeService(qapp).name == "themes"


def test_the_console_presenter_asks_for_no_unknown_service_name():
    source = inspect.getsource(console_presenter)
    assert '"theme"' not in source
    assert "'theme'" not in source


def test_the_console_presenter_leaves_the_theme_signal_to_the_shell():
    source = inspect.getsource(console_presenter)
    assert "theme_changed" not in source
