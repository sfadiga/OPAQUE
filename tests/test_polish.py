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


HIT_TARGET_USERS = [
    "opaque.view.self_check",
    "opaque.view.widgets.color_picker",
    "opaque.view.widgets.notification_widget",
    "opaque.view.dialogs.version_info",
]


@pytest.mark.parametrize("module_name", HIT_TARGET_USERS)
def test_no_module_defines_its_own_hit_target(module_name):
    import importlib
    import inspect

    module = importlib.import_module(module_name)
    source = inspect.getsource(module)

    assert "MINIMUM_HIT_TARGET" in source


TYPOS = ["Prensenter", "worskpace", "heigh ", "single instead service",
         "peparator"]


@pytest.mark.parametrize("typo", TYPOS)
def test_a_shipped_typo_is_gone(typo):
    import pathlib

    hits = [
        str(path) for path in pathlib.Path("src").rglob("*.py")
        if typo in path.read_text(encoding="utf-8")
    ]
    assert hits == []


def test_every_user_visible_string_in_the_running_message_is_translated():
    import inspect

    from opaque import shell

    source = inspect.getsource(shell.BaseApplication.show_already_running_message)
    normalised = " ".join(source.split())

    # Every string the user reads must be inside self.tr(). An f-string
    # cannot be, because lupdate cannot read it.
    assert 'f"' not in source
    assert "setText( self.tr(" in normalised
    assert "setInformativeText( self.tr(" in normalised


def test_no_module_has_an_unused_import():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pylint", "--disable=all",
         "--enable=W0611", "--score=n", "src/opaque"],
        capture_output=True, text=True, check=False)

    assert result.stdout.strip() == "", result.stdout


def test_no_module_has_an_unused_variable():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pylint", "--disable=all",
         "--enable=W0612", "--score=n", "src/opaque"],
        capture_output=True, text=True, check=False)

    assert result.stdout.strip() == "", result.stdout


COMMENTED_OUT_CODE = [
    "src/opaque/view/view.py",
    "src/opaque/view/widgets/toolbar.py",
    "src/opaque/models/configuration.py",
    "src/opaque/presenters/notification_presenter.py",
]


@pytest.mark.parametrize("path", COMMENTED_OUT_CODE)
def test_a_file_holds_no_commented_out_code(path):
    import pathlib
    import re

    # A comment that starts with a statement keyword or an attribute write is
    # code, not prose.
    pattern = re.compile(
        r"^\s*#\s*(self\.|from |import |return |def |class |if |for |while )")

    offenders = [
        line for line in pathlib.Path(path).read_text(
            encoding="utf-8").splitlines()
        if pattern.match(line)
    ]

    assert offenders == []


def test_no_framework_module_calls_print():
    import pathlib

    # build_tools/cli.py is a command line entry point: printing to the
    # terminal is its normal interface, not a framework failure report.
    excluded = {str(pathlib.Path("src/opaque/build_tools/cli.py"))}

    offenders = []
    for path in pathlib.Path("src/opaque").rglob("*.py"):
        if str(path) in excluded:
            continue
        for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("print(") or " print(" in stripped:
                offenders.append(f"{path}:{number}")

    assert offenders == []


def test_the_close_button_has_one_definition():
    import pathlib

    offenders = [
        str(path) for path in pathlib.Path("src/opaque").rglob("*.py")
        if "×" in path.read_text(encoding="utf-8")
        and path.name != "close_button.py"
    ]

    assert offenders == []


def test_the_close_button_is_big_enough_to_hit(qtbot):
    from opaque.view.theme import MINIMUM_HIT_TARGET
    from opaque.view.widgets.close_button import CloseButton

    button = CloseButton()
    qtbot.addWidget(button)

    assert button.minimumWidth() >= MINIMUM_HIT_TARGET
    assert button.minimumHeight() >= MINIMUM_HIT_TARGET


def test_the_close_button_reaches_a_screen_reader(qtbot):
    from opaque.view.widgets.close_button import CloseButton

    button = CloseButton()
    qtbot.addWidget(button)

    assert button.accessibleName()


def test_the_confirm_dialog_mechanics_have_one_definition():
    """
    CloseableTabWidget and NotificationListItem each keep their own
    overridable _confirm_* method, because tests replace those methods by
    name so the question box never opens in a test run. What used to be
    duplicated is the QMessageBox.question(...) call itself; that now has
    exactly one definition, in opaque.view.widgets.confirm.
    """
    import pathlib

    offenders = [
        str(path) for path in pathlib.Path("src/opaque").rglob("*.py")
        if "QMessageBox.question(" in path.read_text(encoding="utf-8")
        and path.name != "confirm.py"
    ]

    assert offenders == []


def test_no_connected_handler_has_an_empty_body():
    import inspect
    import re

    from opaque.presenters import notification_presenter

    source = inspect.getsource(notification_presenter)
    # A handler with nothing but a docstring and pass is either dead wiring
    # or an unfinished job. Both have to be resolved, not left connected.
    assert not re.search(r"def _on_[a-z_]+\([^)]*\)[^:]*:\s*\n(\s*\"\"\"[^\"]*\"\"\"\s*\n)?\s*pass\s*\n", source)


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
