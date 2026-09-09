# This Python file uses the following encoding: utf-8
"""The application template must import and build a window."""

import ast
import importlib
import importlib.util
from pathlib import Path

import pytest

from opaque.services.service import ServiceLocator

TEMPLATE = (Path("src/opaque/build_tools/templates/basic_app_template")
            / "main.py").resolve()


@pytest.fixture
def isolated_locator():
    """
    Give the test an empty service locator and restore the old one.

    Building TemplateApplication registers a LoggerService that opens a
    RotatingFileHandler, among other services. cleanup_services() must run
    on those before the restore, or the handle leaks; see the identical
    fixture in tests/test_quickstart.py.
    """
    saved = dict(ServiceLocator._services)
    ServiceLocator._services.clear()
    yield
    ServiceLocator.cleanup_services()
    ServiceLocator._services.update(saved)


def _opaque_imports(path: Path):
    """Return every (module, name) the file imports from opaque."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "opaque"):
            for alias in node.names:
                found.append((node.module, alias.name))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("opaque"):
                    found.append((alias.name, None))
    return found


def test_the_template_is_valid_python():
    ast.parse(TEMPLATE.read_text(encoding="utf-8"))


def test_the_template_imports_only_names_that_exist():
    missing = []
    for module_name, name in _opaque_imports(TEMPLATE):
        module = importlib.import_module(module_name)
        if name is not None and not hasattr(module, name):
            missing.append(f"{module_name}.{name}")
    assert missing == []


def test_the_template_names_no_ghost_class():
    # A plain substring check on "Application(" would also match the class
    # definition line `class TemplateApplication(BaseApplication):`, since
    # any subclass of BaseApplication is itself named "...Application"
    # followed directly by its base-class parenthesis. Check for a call to
    # the bare, ghost `Application` name instead, which is what the old
    # template wrote (`Application(sys.argv)`).
    tree = ast.parse(TEMPLATE.read_text(encoding="utf-8"))
    calls_to_application = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Application"
    ]
    assert calls_to_application == []

    text = TEMPLATE.read_text(encoding="utf-8")
    for ghost in ("AppModel", "AppPresenter", "AppView", "opaque.core"):
        assert ghost not in text, ghost


def test_the_template_builds_a_window(qapp, qtbot, isolated_locator,
                                      tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    specification = importlib.util.spec_from_file_location(
        "template_main", TEMPLATE)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)

    window = module.TemplateApplication()
    qtbot.addWidget(window)

    assert window.windowTitle()


def test_the_template_registers_one_feature(qapp, qtbot, isolated_locator,
                                            tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    specification = importlib.util.spec_from_file_location(
        "template_main2", TEMPLATE)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)

    window = module.TemplateApplication()
    qtbot.addWidget(window)

    assert "template" in window._registered_features


def test_the_requirements_name_the_package_that_is_published():
    text = (TEMPLATE.parent / "requirements.txt").read_text(encoding="utf-8")
    assert "opaque-framework" in text
