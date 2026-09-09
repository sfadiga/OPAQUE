# This Python file uses the following encoding: utf-8
"""Guards for the consistency and polish work."""

import importlib
import pkgutil

import pytest

import opaque


def _modules():
    """Return every module name under the opaque package."""
    return [
        name for _finder, name, _is_package
        in pkgutil.walk_packages(opaque.__path__, prefix="opaque.")
    ]


@pytest.mark.parametrize("removed", [
    "opaque.view.app_view",
    "opaque.view.layouts.flow",
])
def test_a_deleted_module_is_gone(removed):
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(removed)


@pytest.mark.parametrize("wrapper", [
    "add_separator",
    "connect_slot_to_button_click",
    "connect_signal_to_set_active",
    "connect_signal_to_set_inactive",
])
def test_a_pass_through_wrapper_is_gone(wrapper):
    from opaque.view.widgets.toolbar import OpaqueMainToolbar

    assert not hasattr(OpaqueMainToolbar, wrapper)


def test_the_base_view_offers_the_documented_setup_hook():
    from opaque.view.view import BaseView

    assert callable(getattr(BaseView, "setup_ui", None))


def test_every_module_still_imports():
    for name in _modules():
        importlib.import_module(name)


def test_the_version_manager_is_registered(app_window):
    from opaque.services.service import ServiceLocator
    from opaque.services.version_service import VersionManager

    assert isinstance(ServiceLocator.get(VersionManager), VersionManager)


def test_the_title_bar_reuses_one_version_manager(app_window, monkeypatch):
    from opaque.services import version_service

    built = []
    real = version_service.VersionManager.__init__

    def _counting_init(self, *args, **kwargs):
        built.append(True)
        real(self, *args, **kwargs)

    monkeypatch.setattr(
        version_service.VersionManager, "__init__", _counting_init)

    app_window.update_application_title(None)
    app_window.update_application_title(None)

    assert built == []


@pytest.mark.parametrize("removed", [
    "src/opaque/build_tools/templates/pyinstaller_config.py",
    "src/opaque/build_tools/templates/nuitka_config.cfg",
])
def test_an_unread_template_is_gone(removed):
    from pathlib import Path

    assert not Path(removed).exists()


def test_no_default_of_none_is_annotated_as_a_value():
    import inspect
    import typing

    from opaque.view.widgets.mdi_window import OpaqueMdiSubWindow

    hints = typing.get_type_hints(OpaqueMdiSubWindow.__init__)
    signature = inspect.signature(OpaqueMdiSubWindow.__init__)

    for name, parameter in signature.parameters.items():
        if parameter.default is None and name in hints:
            assert type(None) in typing.get_args(hints[name]) or hints[
                name] is type(None), name
