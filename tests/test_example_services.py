# This Python file uses the following encoding: utf-8
"""
Prove the example services import and answer to the names the example
presenters look up.

The "write your own service" example was the only one the framework ships,
and it failed at import. tests/test_imports.py cannot catch this: the
examples are outside the opaque package.
"""

import importlib
import sys
from pathlib import Path

import pytest

EXAMPLE_DIR = Path(__file__).resolve().parent.parent / "examples" / "basic_example"

EXPECTED_NAMES = {
    "services.calculation_service": ("CalculationService", "calculation"),
    "services.data_service": ("DataService", "data"),
    "services.logging_service": ("LoggingService", "logging"),
}


@pytest.fixture
def example_on_path():
    sys.path.insert(0, str(EXAMPLE_DIR))
    yield
    sys.path.remove(str(EXAMPLE_DIR))
    for name in [m for m in list(sys.modules) if m.startswith("services")]:
        del sys.modules[name]


@pytest.mark.parametrize("module_name", sorted(EXPECTED_NAMES))
def test_example_service_imports_and_names_itself(module_name, example_on_path):
    class_name, service_name = EXPECTED_NAMES[module_name]
    module = importlib.import_module(module_name)
    service = getattr(module, class_name)()
    assert service.name == service_name
