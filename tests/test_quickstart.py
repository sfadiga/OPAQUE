# This Python file uses the following encoding: utf-8
"""
Prove the README quick start is the file the tests execute.

The README used to hold hand-written code that nobody ran. It raised
TypeError on the first line a user copies.
"""

import re
import sys
from pathlib import Path

import pytest

from opaque.services.service import ServiceLocator

REPO_ROOT = Path(__file__).resolve().parent.parent
QUICKSTART = REPO_ROOT / "examples" / "quickstart" / "main.py"
README = REPO_ROOT / "README.md"

_MARKED_BLOCK = re.compile(
    r"<!-- quickstart:begin -->\n```python\n(.*?)```\n<!-- quickstart:end -->",
    re.DOTALL,
)


def test_the_readme_carries_the_quickstart_verbatim():
    match = _MARKED_BLOCK.search(README.read_text(encoding="utf-8"))
    assert match is not None, "the quickstart markers are missing from README.md"
    assert match.group(1) == QUICKSTART.read_text(encoding="utf-8")


@pytest.fixture
def isolated_locator():
    """
    Give the test an empty service locator and restore the old one.

    Building QuickStartApplication registers a LoggerService that opens a
    RotatingFileHandler, among other services. cleanup_services() must run
    on those before the restore, or the handle leaks; see the identical
    fixture and its comment in tests/test_example_app.py.
    """
    saved = dict(ServiceLocator._services)
    ServiceLocator._services.clear()
    yield
    ServiceLocator.cleanup_services()
    ServiceLocator._services.update(saved)


def test_the_quickstart_application_builds(qapp, isolated_locator, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(QUICKSTART.parent))
    try:
        import importlib

        module = importlib.import_module("main")
        window = module.QuickStartApplication()
        try:
            assert "greeting" in window._registered_features
        finally:
            window.close()
            window.deleteLater()
    finally:
        sys.path.remove(str(QUICKSTART.parent))
        sys.modules.pop("main", None)
