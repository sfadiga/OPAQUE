# Plan 01 — Toolchain, Packaging, Public API, CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `opaque-framework` installable, importable, typed, and continuously proven, so every later plan has a feedback loop instead of a hope.

**Architecture:** Four independent repairs, in dependency order. First the metadata says what is true (floor 3.11, real URLs, no ghost package data). Then the one syntax error that stops the package from importing on 3.11 is fixed, which also un-blocks mypy. Then `opaque/__init__.py` becomes the public API with `py.typed`, so a user and a type checker see one shallow import path. Last, `uv` replaces the hand-rolled venv scripts and GitHub Actions runs the checks that would have caught all of the above.

**Tech Stack:** Python 3.11, `tomllib` (standard library on 3.11), setuptools build backend, uv, pytest, mypy, pylint, GitHub Actions.

Read **Rules for the executing agent** in `2026-09-08-techdebt-00-index.md` before you start.

**Closes:** review 2.4, 2.6, 2.7, 5.3, 5.6. Applies decisions D2 and D3.

---

## File Structure

| Path | Responsibility |
|---|---|
| Modify `pyproject.toml` | The single source of project metadata: Python floor, classifiers, URLs, package data, pytest and mypy configuration. |
| Modify `src/opaque/build_tools/pyinstaller_builder.py:203-283` | `_generate_spec_content` stops nesting same-quote f-strings, so the module parses on 3.11. |
| Modify `src/opaque/__init__.py` | The public API. Re-exports the framework contract and resolves `__version__` from installed metadata. |
| Create `src/opaque/py.typed` | PEP 561 marker. Without it, a type checker treats the whole package as untyped. |
| Create `tests/test_packaging.py` | Proves the metadata claims match the decisions of record. |
| Create `tests/test_public_api.py` | Proves every promised name is importable from `opaque` and that `__all__` has no dead entry. |
| Create `tests/test_imports.py` | Imports every module in the package. This one test would have caught review 2.4 and 2.5. |
| Modify `MANIFEST.in` | Drops the ghost `src/opaque/core/py.typed`. |
| Create `.python-version` | Pins the interpreter uv provisions. |
| Modify `.gitignore` | Ignores the run-time droppings that keep appearing in the repository root. |
| Modify `cicd.sh`, `cicd.ps1` | Use uv. Stop referring to a `requirements.txt` that does not exist. |
| Create `.github/workflows/ci.yml` | Runs the import check, the suite, mypy, and pylint on every push and pull request. |

---

### Task 1: The metadata says what is true

**Files:**
- Modify: `pyproject.toml`
- Modify: `MANIFEST.in`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_packaging.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""
Tests for the project metadata.

The metadata is a promise to a user who runs `pip install opaque-framework`.
A promise nothing checks is how this project came to claim Python 3.8 support
while one module needed 3.12.
"""

import tomllib
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


@pytest.fixture(scope="module")
def metadata() -> dict:
    with open(PYPROJECT, "rb") as handle:
        return tomllib.load(handle)


def test_the_python_floor_is_3_11(metadata):
    """Decision D3. One floor, stated once."""
    assert metadata["project"]["requires-python"] == ">=3.11"


def test_no_classifier_promises_a_python_below_the_floor(metadata):
    classifiers = metadata["project"]["classifiers"]
    unsupported = [
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ]
    assert [c for c in classifiers if c in unsupported] == []


def test_the_project_urls_are_real(metadata):
    for name, url in metadata["project"]["urls"].items():
        assert "yourusername" not in url, f"{name} is still a placeholder"


def test_the_package_data_names_no_ghost_package(metadata):
    """
    `core/py.typed` was packaged for a package `opaque.core` that never
    existed. It is the same ghost the example services import.
    """
    package_data = metadata["tool"]["setuptools"]["package-data"]["opaque"]
    assert "core/py.typed" not in package_data


def test_pytest_finds_the_sources_on_a_fresh_clone(metadata):
    """Bare `pytest` must work before an editable install."""
    assert metadata["tool"]["pytest"]["ini_options"]["pythonpath"] == ["src"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_packaging.py -q
```

Expected: FAIL. Five failures: `requires-python` is `">=3.8"`, three unsupported classifiers are present, four URLs hold `yourusername`, `core/py.typed` is present, and `pythonpath` raises `KeyError`.

- [ ] **Step 3: Fix the metadata**

In `pyproject.toml`, replace the line:

```toml
requires-python = ">=3.8"
```

with:

```toml
requires-python = ">=3.11"
```

Replace the whole `classifiers` list with:

```toml
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Software Development :: Libraries :: Application Frameworks",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Software Development :: User Interfaces",
]
```

Replace the whole `[project.urls]` section with:

```toml
[project.urls]
"Homepage" = "https://github.com/sfadiga/OPAQUE"
"Bug Tracker" = "https://github.com/sfadiga/OPAQUE/issues"
"Documentation" = "https://github.com/sfadiga/OPAQUE#readme"
"Source Code" = "https://github.com/sfadiga/OPAQUE"
```

Replace the `[tool.setuptools.package-data]` section with:

```toml
[tool.setuptools.package-data]
opaque = ["py.typed", "translations/*.qm", "translations/*.ts"]
```

Replace the `[tool.pytest.ini_options]` section with:

```toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-ra --strict-markers"
```

Add this section at the end of the file:

```toml
[tool.mypy]
python_version = "3.11"
files = ["src/opaque"]
ignore_missing_imports = true
```

In `MANIFEST.in`, delete this line:

```
include src/opaque/core/py.typed
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_packaging.py -q
```

Expected: PASS, 5 passed.

- [ ] **Step 5: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest tests -q
```

Expected: PASS, no failures. The count grows by 5.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml MANIFEST.in tests/test_packaging.py
git commit -m "fix(packaging): state the real python floor, urls and package data"
```

---

### Task 2: The package imports on Python 3.11

**Files:**
- Modify: `src/opaque/build_tools/pyinstaller_builder.py:203-283`
- Test: `tests/test_imports.py`

`_generate_spec_content` builds a PyInstaller spec with one big f-string, and at line 268 it opens a second `f'''...'''` inside the first one. Same-quote nesting needs PEP 701, which arrived in Python 3.12. On 3.11 the module raises `SyntaxError` at import, which kills `opaque.build_tools`, the `opaque-build` script, and every mypy run after that file.

The repair is not a quote swap. Build each variable part before the template, so the template holds no nested f-string at all.

- [ ] **Step 1: Write the failing test**

Create `tests/test_imports.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""
Import every module in the package.

This is the cheapest test in the suite and it is the one that was missing.
A module that only a console script imports, or that only an example
imports, was never executed by anything, so a syntax error and a ghost
import both survived a release.

Discovery walks the file system. It does not use `pkgutil.walk_packages`.
Three directories of this package -- `models`, `presenters` and `services`
-- have no `__init__.py`, so they are implicit namespace packages. A
`pkgutil` walk cannot see into them. It found 30 modules out of 52, and
every module it missed was in the model, presenter or service layer. A
test that cannot see the service layer does not do the job this test
exists to do.

`build_tools/templates` is excluded on purpose. Those files are source
templates for a generated application. They are not modules of this
package, and they are not expected to import.
"""

import importlib
from pathlib import Path

import pytest

import opaque

PACKAGE_ROOT = Path(opaque.__file__).resolve().parent
EXCLUDED_PARTS = ("build_tools", "templates")


def _module_names() -> list[str]:
    names = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        relative = path.relative_to(PACKAGE_ROOT)
        if "__pycache__" in relative.parts:
            continue
        if relative.parts[: len(EXCLUDED_PARTS)] == EXCLUDED_PARTS:
            continue
        parts = list(relative.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        if not parts:
            # `opaque/__init__.py` itself. Importing it is how we got here.
            continue
        names.append(".".join(["opaque"] + parts))
    return sorted(set(names))


MODULES = _module_names()


def test_the_walk_found_the_whole_package():
    """
    50 is a floor, not the exact count. It has to be high enough that a
    whole directory going missing from discovery fails this test.
    """
    assert len(MODULES) >= 50


def test_the_walk_reaches_the_namespace_packages():
    """The `pkgutil` walk this replaced could not see any of these three."""
    for name in (
        "opaque.models.abstract_model",
        "opaque.presenters.presenter",
        "opaque.services.service",
    ):
        assert name in MODULES


@pytest.mark.parametrize("module_name", MODULES)
def test_module_imports(module_name):
    importlib.import_module(module_name)
```

Discovery walks the file system on purpose. `pkgutil.walk_packages`
cannot see into `models`, `presenters` or `services`, because those three
directories have no `__init__.py` and are implicit namespace packages. A
`pkgutil` walk finds 30 modules out of 52, and every module it misses is
in the model, presenter or service layer.

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_imports.py -q
```

Expected: FAIL. Three parametrized cases fail: `opaque.build_tools`,
`opaque.build_tools.cli`, and `opaque.build_tools.pyinstaller_builder`. Each
reports `SyntaxError: f-string: expecting '}'` at
`pyinstaller_builder.py:268`. The other cases pass, and the two discovery
tests pass, because discovery reads the file system and never imports.

- [ ] **Step 3: Rewrite `_generate_spec_content`**

In `src/opaque/build_tools/pyinstaller_builder.py`, replace the whole method from line 203 (`def _generate_spec_content`) to line 283 (`return spec_template`) with exactly this:

```python
    def _generate_spec_content(self, entry_path: Path, **kwargs: Any) -> str:
        """
        Generate PyInstaller spec file content.

        Every variable part is built before the template. The template holds
        no nested f-string, because nesting a same-quote f-string needs
        PEP 701, which is Python 3.12 and above. This module must parse on
        the declared floor, 3.11.
        """
        name = kwargs.get("name", entry_path.stem)
        onefile = kwargs.get("onefile", False)
        console = kwargs.get("console", False)

        # Build data files list
        data_files: List[str] = []
        for data in kwargs.get("add_data", []):
            data_files.append(f"('{data}', '.')")
        data_files_str = ", ".join(data_files)

        # Build hidden imports list
        hidden_imports = self._get_pyside6_includes() + kwargs.get("hidden_imports", [])
        hidden_imports_str = ", ".join([f"'{imp}'" for imp in hidden_imports])

        # Build excludes list
        excludes = self._get_common_excludes() + kwargs.get("exclude_modules", [])
        excludes_str = ", ".join([f"'{exc}'" for exc in excludes])

        # A onefile build hands the binaries, the zipfiles and the datas to
        # EXE. A onedir build hands them to COLLECT instead, and EXE gets
        # empty lists.
        bundle_lines = "a.binaries," if onefile else "[],"
        zip_lines = "a.zipfiles," if onefile else "[],"
        data_lines = "a.datas," if onefile else "[],"

        debug_flag = str(kwargs.get("debug", False)).lower()
        upx_flag = str(kwargs.get("upx", False)).lower()
        console_flag = str(console).lower()

        icon = kwargs.get("icon", "")
        icon_line = f"    icon='{icon}'," if icon else ""

        collect_block = ""
        if not onefile:
            collect_block = (
                "\n\ncoll = COLLECT(\n"
                "    exe,\n"
                "    a.binaries,\n"
                "    a.zipfiles,\n"
                "    a.datas,\n"
                "    strip=False,\n"
                f"    upx={upx_flag},\n"
                "    upx_exclude=[],\n"
                f"    name='{name}',\n"
                ")\n"
            )

        spec_template = f'''# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for {name}
# Generated by OPAQUE Framework Build Tools

block_cipher = None

a = Analysis(
    ['{entry_path}'],
    pathex=[],
    binaries=[],
    datas=[{data_files_str}],
    hiddenimports=[{hidden_imports_str}],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[{excludes_str}],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    {bundle_lines}
    {zip_lines}
    {data_lines}
    name='{name}',
    debug={debug_flag},
    bootloader_ignore_signals=False,
    strip=False,
    upx={upx_flag},
    upx_exclude=[],
    runtime_tmpdir=None,
    console={console_flag},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
{icon_line}
)
{collect_block}'''
        return spec_template
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_imports.py -q
```

Expected: PASS, 54 passed. That is 52 module imports plus the two
discovery tests. Every module in the package imports on Python 3.11.

- [ ] **Step 5: Prove the generated spec is valid Python**

Run:

```
venv\Scripts\python.exe -c "import ast; from pathlib import Path; from opaque.build_tools.pyinstaller_builder import PyInstallerBuilder; b=PyInstallerBuilder(); [ast.parse(b._generate_spec_content(Path('main.py'), name='App', onefile=o, icon=i)) for o in (True, False) for i in ('', 'app.ico')]; print('spec parses')"
```

Expected: `spec parses`.

- [ ] **Step 6: Prove mypy now reads the whole package**

Run:

```
venv\Scripts\python.exe -m mypy src/opaque
```

Expected: mypy runs to the end and prints a summary line. It will report errors — that is fine and expected at this point. The requirement is that it no longer stops with `SyntaxError` at `pyinstaller_builder.py`. Record the error count in the commit body.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/build_tools/pyinstaller_builder.py tests/test_imports.py
git commit -m "fix(build_tools): build the spec without a nested f-string"
```

---

### Task 3: A public API with a version and a typed marker

**Files:**
- Modify: `src/opaque/__init__.py`
- Create: `src/opaque/py.typed`
- Test: `tests/test_public_api.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_public_api.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""
Tests for the public API surface.

A user, and every AI agent, learns a framework from its exports first. An
empty `__init__.py` sends them guessing at deep module paths, and the
codebase itself guessed wrong three times (`opaque.core`).
"""

from pathlib import Path

import opaque

EXPECTED = [
    "BaseApplication",
    "BaseModel",
    "BasePresenter",
    "BaseService",
    "BaseView",
    "BoolField",
    "ChoiceField",
    "DefaultApplicationConfiguration",
    "Field",
    "FloatField",
    "IntField",
    "ListField",
    "ServiceLocator",
    "StringField",
    "UIType",
]


def test_every_promised_name_is_exported():
    missing = [name for name in EXPECTED if name not in opaque.__all__]
    assert missing == []


def test_every_exported_name_resolves():
    """An `__all__` entry that does not resolve is worse than no entry."""
    unresolved = [name for name in opaque.__all__ if not hasattr(opaque, name)]
    assert unresolved == []


def test_the_package_states_its_version():
    assert isinstance(opaque.__version__, str)
    assert opaque.__version__.count(".") >= 2


def test_the_package_ships_a_py_typed_marker():
    marker = Path(opaque.__file__).parent / "py.typed"
    assert marker.is_file()


def test_the_version_falls_back_when_the_metadata_is_missing():
    """
    A source checkout with no install has no distribution metadata. The
    fallback has to keep the shape every other reader of `__version__`
    expects, which is why it is a version string and not an empty one.

    This runs in a child interpreter on purpose. Reloading `opaque` in
    this process would rebind every exported class, and the service
    locator and the Qt metaclasses in this suite hold references to the
    originals.
    """
    import os
    import subprocess
    import sys
    import textwrap

    code = textwrap.dedent(
        """
        import importlib.metadata as metadata

        def _missing(_name):
            raise metadata.PackageNotFoundError

        metadata.version = _missing

        import opaque

        print(opaque.__version__)
        """
    )
    # The child does not inherit `pythonpath` from pyproject.toml, and on a
    # fresh clone with no install there is no path file to put `src` on its
    # path either. Hand the parent's path to the child, so this test does
    # not quietly require an editable install.
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(path for path in sys.path if path)

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        env=environment,
    )
    assert result.stdout.strip() == "0.0.0+unknown"
    assert result.stdout.strip().count(".") >= 2
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_public_api.py -q
```

Expected: FAIL, 5 failures. `opaque` has no `__all__`, no `__version__`, and no `py.typed`. The fallback test fails too: the child interpreter imports the package, then raises `AttributeError` on `opaque.__version__`, so `check=True` raises `CalledProcessError`.

- [ ] **Step 3: Write the public API**

Replace the whole content of `src/opaque/__init__.py` with exactly this:

```python
# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

OPAQUE — an opinionated PySide6 MDI application framework.

Import the framework contract from here, not from the deep module paths.
One feature is one MVP triple: a BaseModel, a BaseView, and a BasePresenter.

    from opaque import BaseApplication, BaseModel, BasePresenter, BaseView

The imports below are grouped by layer. No order is required between them.
The one real import cycle in this package is `view/view.py` to
`view/widgets/__init__.py` to `toolbar.py` to `presenters/presenter.py`,
which would then re-import `view.py`. It is already broken inside
`presenters/presenter.py`, which keeps its `BaseView` and `BaseApplication`
imports behind `TYPE_CHECKING`. That guard holds whatever order this file
uses, so do not treat this list as fragile.
"""

from importlib.metadata import (
    PackageNotFoundError as _PackageNotFoundError,
    version as _installed_version,
)

from opaque.models.annotations import (
    BoolField,
    ChoiceField,
    Field,
    FloatField,
    IntField,
    ListField,
    StringField,
    UIType,
)
from opaque.models.abstract_model import AbstractModel
from opaque.models.configuration import DefaultApplicationConfiguration
from opaque.services.service import BaseService, ServiceLocator
from opaque.view.application import BaseApplication
from opaque.models.model import BaseModel
from opaque.view.view import BaseView
from opaque.presenters.presenter import BasePresenter

try:
    __version__ = _installed_version("opaque-framework")
except _PackageNotFoundError:
    # Running from a source tree with no install. The metadata is the only
    # place a version lives, so say so instead of inventing a number.
    __version__ = "0.0.0+unknown"

__all__ = [
    "AbstractModel",
    "BaseApplication",
    "BaseModel",
    "BasePresenter",
    "BaseService",
    "BaseView",
    "BoolField",
    "ChoiceField",
    "DefaultApplicationConfiguration",
    "Field",
    "FloatField",
    "IntField",
    "ListField",
    "ServiceLocator",
    "StringField",
    "UIType",
    "__version__",
]
```

Create `src/opaque/py.typed` as an empty file. PEP 561 says the marker's content is ignored, so it stays empty:

```bash
printf '' > src/opaque/py.typed
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_public_api.py -q
```

Expected: PASS, 5 passed.

The docstring says the import order does not matter. That is deliberate and it is tested: reordering the imports in a copy of the package outside the repository still imports cleanly. An earlier draft of this plan claimed the order was load bearing because of a `TYPE_CHECKING` import. That was wrong, because a `TYPE_CHECKING` block never runs at run time. Do not reinstate the claim.

- [ ] **Step 5: Prove the shallow import does not need a display**

Run:

```
venv\Scripts\python.exe -c "import os; os.environ['QT_QPA_PLATFORM']='offscreen'; import opaque; print(opaque.__version__, len(opaque.__all__))"
```

Expected: a version string and `17`.

- [ ] **Step 6: Run the whole suite**

Run:

```
venv\Scripts\python.exe -m pytest tests -q
```

Expected: PASS, no failures.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/__init__.py src/opaque/py.typed tests/test_public_api.py
git commit -m "feat(api): export the framework contract and ship py.typed"
```

---

### Task 4: The example application is a test

**Files:**
- Create: `tests/test_example_app.py`

`examples/basic_example/main.py` is the one accurate worked example, so a break in it is a break in the documentation. Nothing runs it.

- [ ] **Step 1: Write the failing test**

Create `tests/test_example_app.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""
Build the reference example application headless.

The example is the only worked example the review trusts, so it is the
contract a user copies. This test builds the window, checks that the
features registered, and closes it. It does not enter the event loop.

ServiceLocator is a process wide singleton that refuses a second
registration, and tests/test_application_shell.py already builds one
BaseApplication for the session. This test therefore clears the locator
first and puts it back afterwards.
"""

import sys
from pathlib import Path

import pytest

from opaque.services.service import ServiceLocator

EXAMPLE_DIR = Path(__file__).resolve().parent.parent / "examples" / "basic_example"


@pytest.fixture
def isolated_locator():
    """
    Give the test an empty service locator and restore the old one.

    This reaches into the private `_services` dict on purpose. The locator
    has no public reset API, and adding one belongs to the plan that makes
    service access typed. Do not replace this with an ad hoc public method.

    The teardown calls `cleanup_services()` before it restores, and the
    order is load bearing. Before the restore, `_services` holds only what
    this test registered, so `cleanup()` runs on those and nothing else.
    After the restore it would hold the session wide services that
    tests/test_application_shell.py still depends on, and cleaning those up
    would close a log handler that a live BaseApplication still expects to
    work.

    Without this, a failure part way through building the application would
    drop half-registered services with no `cleanup()`, and on Windows that
    can leave an open file handle behind.
    """
    saved = dict(ServiceLocator._services)
    ServiceLocator._services.clear()
    yield
    ServiceLocator.cleanup_services()
    ServiceLocator._services.update(saved)


def test_the_example_application_builds(qapp, isolated_locator, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(EXAMPLE_DIR))
    try:
        import importlib

        module = importlib.import_module("main")
        window = module.MyExampleApplication()
        try:
            registered = window._registered_features
            # Exact key membership, not a substring of a stringified list.
            # A substring match passed even when most features failed to
            # register, because one surviving key was enough.
            assert "Calculator" in registered, sorted(registered)
            # The example is the documentation, so its feature set is the
            # contract. Adding a feature to the example means updating this
            # set, and that is the point.
            expected = {
                "ApplicationPresenter",
                "Calculator",
                "Console",
                "Data Viewer",
                "Logging",
                "Notification Tester",
                "Tab Manager",
            }
            assert set(registered) == expected, sorted(registered)
        finally:
            window.close()
            window.deleteLater()
    finally:
        sys.path.remove(str(EXAMPLE_DIR))
        for name in [m for m in sys.modules if m in ("main", "features") or m.startswith("features.")]:
            del sys.modules[name]
```

The feature set assertion is deliberate. An earlier draft asserted `"Calculator" in str(list(window._registered_features))`, which is a substring match on a stringified list of keys. It passed while five of the seven features were missing. Do not weaken it back. The cleanup loop also has to match the bare `features` module, not only `features.` with the dot, because `main.py` imports through the package.

- [ ] **Step 2: Run the test**

Run:

```
venv\Scripts\python.exe -m pytest tests/test_example_app.py -q
```

Expected: PASS. If it fails, stop and report the failure — it means the reference example is broken, which is a P0 finding the review did not have.

- [ ] **Step 3: Commit**

```bash
git add tests/test_example_app.py
git commit -m "test(examples): build the reference application headless"
```

---

### Task 5: Repository hygiene

**Files:**
- Modify: `.gitignore`
- Modify: `cicd.sh`
- Modify: `cicd.ps1`

`cicd.sh` installs from a `requirements.txt` that does not exist, so `setup` has never worked on a fresh clone. Both scripts are replaced by thin wrappers over uv, which Task 6 installs.

Audited while executing this task. The old `cicd.sh` was worse than the
review said. `setup` installed from a `requirements.txt` that does not
exist. The `test` case called a function named `test` that was never
defined, so it fell through to the shell builtin and ran no tests at all.
The `upload` case had no function behind it. The `build` case ran
`pyside6-rcc` on `qresource.qrc`, and no `.qrc` file exists anywhere in the
repository, no compiled `rc_*.py` exists, and nothing imports one. So four
of the eight tasks were dead or broken.

Only two capabilities are really dropped, both on purpose. `venv` activated
the environment by hand, which uv makes unnecessary, and whose PowerShell
version called a `Project-Setup` function that does not exist. `build-exe`
could call PyInstaller or Nuitka directly when the `opaque-build` CLI would
not import; Plan 09 owns that fallback if it is wanted.

The new `cicd.sh` must be mode `100755` in git. Its own usage text says
`./cicd.sh <task>`, and that command fails on Linux when the file is
`100644`. Set it with `git update-index --chmod=+x cicd.sh`.

- [ ] **Step 1: Ignore the run-time droppings**

Append these lines to `.gitignore`:

```
# Run time output that belongs next to the user, not next to the source.
# `*.lock`, `*.wks` and `.venv` are already ignored earlier in this file,
# and `*.lock` covers the single instance lock whatever the app is called.
/logs/
*.egg-link
```

An earlier draft of this task also added `*.wks`, `application_name.lock`
and `.venv/`. All three were already covered, so they are dropped here.
Check before you add: a duplicate ignore rule is not an error, but it hides
which rule is doing the work.

- [ ] **Step 2: Replace the shell script**

Replace the whole content of `cicd.sh` with exactly this:

```bash
#!/usr/bin/env bash
# OPAQUE Framework developer tasks.
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.
#
# Every task goes through uv. uv owns the environment, the lock file and the
# interpreter, so there is no venv bootstrap here and no requirements.txt.
set -euo pipefail

ENTRYPOINT="examples/basic_example/main.py"

usage() {
    cat <<'USAGE'

~~~~~~~~ OPAQUE Framework developer tasks ~~~~~~~~

Usage: ./cicd.sh <task>

Tasks:
    setup       Create or update the environment from uv.lock
    test        Run the test suite
    check       Run mypy and pylint
    run         Run the reference example application
    dist        Build the wheel and the source distribution
    clean       Remove build output and __pycache__ directories
    build-exe   Build a standalone executable (see: uv run opaque-build --help)

USAGE
}

case "${1-}" in
    setup)     uv sync --all-extras ;;
    test)      uv run python -m pytest tests -q ;;
    check)
        # Run both tools and report both, then fail if either failed.
        # `mypy && pylint` hid pylint's output entirely while mypy was
        # dirty, and mypy is not clean yet.
        status=0
        uv run python -m mypy src/opaque || status=1
        uv run python -m pylint src/opaque || status=1
        exit "$status"
        ;;
    run)       uv run python "$ENTRYPOINT" ;;
    dist)      uv build ;;
    clean)
        rm -rf build dist ./*.egg-info
        # Prune the environments and the git directory first. Walking them
        # deletes the bytecode of every installed module for no benefit.
        find . -type d \( -name venv -o -name .venv -o -name .git \) -prune \
            -o -type d -name "__pycache__" -prune -exec rm -rf {} +
        ;;
    build-exe) shift; uv run opaque-build "$@" ;;
    -h|--help|"") usage ;;
    *) echo "ERROR: unknown task '${1}'" >&2; usage >&2; exit 1 ;;
esac
```

- [ ] **Step 3: Replace the PowerShell script**

Replace the whole content of `cicd.ps1` with exactly this:

```powershell
# OPAQUE Framework developer tasks.
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.
#
# Every task goes through uv. The old script shelled out to bash, which is not
# present on a plain Windows machine.
param(
    [string]$Task,
    [Parameter(ValueFromRemainingArguments)]
    [string[]]$Arguments
)

$EntryPoint = "examples/basic_example/main.py"

function Show-Usage {
    Write-Host ""
    Write-Host "~~~~~~~~ OPAQUE Framework developer tasks ~~~~~~~~"
    Write-Host ""
    Write-Host "Usage: .\cicd.ps1 <task>"
    Write-Host ""
    Write-Host "Tasks:"
    Write-Host "    setup       Create or update the environment from uv.lock"
    Write-Host "    test        Run the test suite"
    Write-Host "    check       Run mypy and pylint"
    Write-Host "    run         Run the reference example application"
    Write-Host "    dist        Build the wheel and the source distribution"
    Write-Host "    clean       Remove build output and __pycache__ directories"
    Write-Host "    build-exe   Build a standalone executable"
    Write-Host ""
}

# PowerShell returns 0 from a script that never calls `exit`, whatever the
# native commands inside it did. Every branch that runs a tool therefore
# records its exit code, and the script ends by returning it.
$exitCode = 0

switch ($Task) {
    "setup" { uv sync --all-extras; $exitCode = $LASTEXITCODE }
    "test"  { uv run python -m pytest tests -q; $exitCode = $LASTEXITCODE }
    "check" {
        # Both tools run. A short circuit hid one tool's output.
        uv run python -m mypy src/opaque
        if ($LASTEXITCODE -ne 0) { $exitCode = 1 }
        uv run python -m pylint src/opaque
        if ($LASTEXITCODE -ne 0) { $exitCode = 1 }
    }
    "run"   { uv run python $EntryPoint; $exitCode = $LASTEXITCODE }
    "dist"  { uv build; $exitCode = $LASTEXITCODE }
    "clean" {
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist
        # Only the project's own bytecode. Not the environments'.
        Get-ChildItem -Path "src", "tests", "examples" -Recurse -Directory `
            -Filter "__pycache__" -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force
    }
    "build-exe" { uv run opaque-build @Arguments; $exitCode = $LASTEXITCODE }
    default { Show-Usage }
}

exit $exitCode
```

Both scripts must report failure. A PowerShell script that never calls
`exit` returns 0 even when the tool it ran failed, so `.\cicd.ps1 test`
reported success while pytest was failing. `check` must run both tools
rather than short circuit, because mypy is not clean until Plan 10 Task 8
and a short circuit hides pylint completely. `clean` must prune `venv` and
`.venv`. Do not simplify any of these back.

- [ ] **Step 4: Verify the scripts print their usage**

Run:

```
bash cicd.sh --help
```

Expected: the task list above. No error about `requirements.txt`.

- [ ] **Step 5: Commit**

```bash
git add .gitignore cicd.sh cicd.ps1
git commit -m "chore(tooling): run developer tasks through uv"
```

---

### Task 6: uv owns the environment

**Files:**
- Create: `.python-version`
- Create: `uv.lock` (generated, committed)
- Modify: `CLAUDE.md`
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Modify: `tests/test_packaging.py`

Two repairs come first, because `uv sync` cannot run without them. Both were
found by running this task.

**The `themes` extra pins a version that has never existed.**
`pyproject.toml` says `qt-themes>=1.0.0`. PyPI has published 0.1.0, 0.2.0,
0.3.0 and 0.4.0, and nothing else. So `pip install opaque-framework[themes]`
fails today, and `uv sync` refuses to resolve. Replace the pin with:

```toml
themes = [
    # 0.4.0 is the latest qt-themes on PyPI. The floor used to say 1.0.0,
    # which has never been published, so this extra could not install at all.
    "qt-themes>=0.4.0",
]
```

`requires-python` keeps its open upper bound. uv's error suggests limiting
the supported versions, and that advice is wrong for a library: an upper
bound on `requires-python` makes the package uninstallable on a newer
interpreter, and it cannot be fixed for a version already released. The
floor stays `>=3.11`, which is decision D3. `qt-material>=2.14` and
`QDarkStyle>=3.2.0` were both checked and both resolve.

**`.gitignore` ignores the file this task commits.** Replace these two lines:

```
# pyenv
.python-version
```

with:

```
# `.python-version` is deliberately NOT ignored. uv reads it to choose the
# interpreter, and it is committed so every machine and CI agree. The rule
# that ignored it came from a pyenv layout this project never used.
```

`.gitignore` hides `uv.lock` as well, and that one is easy to miss because
`git add` on an ignored file succeeds and does nothing. Replace these lines:

```
# Single-instance runtime lock file the application writes on start up
*.lock
```

with:

```
# Single-instance runtime lock file the application writes on start up.
# The name comes from the application name, which a user of this framework
# chooses, so the pattern has to stay a glob.
*.lock
# uv.lock is not a runtime lock. It is the dependency lock file, and it is
# committed because uv owns the environment. This exception must stay after
# the glob above: in .gitignore the last matching pattern wins. A later plan
# moves the runtime lock out of the working directory, and once no lock file
# is ever written next to the source, the glob and this exception can both go.
!uv.lock
```

After both edits, prove it. `git check-ignore -v .python-version` and
`git check-ignore -v uv.lock` must each report nothing and exit 1, while
`git check-ignore -v application_name.lock` must still report the glob. Then
check `git show HEAD --name-only` names both files after the commit. This is
the same trap as the empty `py.typed` marker in Task 3: a file that never
got staged looks exactly like a file with nothing in it.

Then add this test to `tests/test_packaging.py`, so the interpreter pin and
the declared floor cannot drift apart:

```python
def test_the_pinned_interpreter_matches_the_declared_floor(metadata):
    """
    `.python-version` tells uv which interpreter to provision, and
    `requires-python` tells a user which ones are supported. Nothing
    connected the two, so they could drift without a failure.
    """
    pinned = (PYPROJECT.parent / ".python-version").read_text(
        encoding="utf-8"
    ).strip()
    assert metadata["project"]["requires-python"] == f">={pinned}"
```

There is deliberately no test that a dependency floor exists on PyPI. That
needs the network, and this suite is offline and headless. The committed
`uv.lock` is the guard, because resolution is proven when it is written, and
from Task 7 CI runs `uv sync` on every push.

- [ ] **Step 1: Confirm uv is present**

Run:

```
uv --version
```

Expected: a version line. If the command is not found, stop and report it. Do not install uv without asking; ask the user to run `winget install --id=astral-sh.uv` themselves.

- [ ] **Step 2: Pin the interpreter**

Create `.python-version` with exactly this content:

```
3.11
```

- [ ] **Step 3: Create the environment and the lock file**

Run:

```
uv sync --all-extras
```

Expected: uv creates `.venv`, resolves the dependencies, writes `uv.lock`, and installs the project in editable mode.

- [ ] **Step 4: Prove the suite passes through uv**

Run:

```
uv run python -m pytest tests -q
```

Expected: PASS, **324 passed**. That is the 323 from Task 5 plus the interpreter pin guard added above. Run the old `venv\Scripts\python.exe` suite once more too, and confirm it also reports 324. Both environments have to work at this point, because the earlier tasks all used the old one. Note that the old `venv` holds `qt-themes` 0.3.0 while `.venv` gets 0.4.0, so a theme test that passes in one and fails in the other is a real finding about that upgrade, not something to adjust.

- [ ] **Step 5: Update the command list in CLAUDE.md**

In `CLAUDE.md`, replace the whole fenced command block under `## Commands` with exactly this:

```bash
uv sync --all-extras                                  # create or update the environment
uv run python -m pytest tests -q                      # full suite, headless, ~3 s
uv run python -m pytest tests/test_localisation.py -q # one file
uv run python -m pytest tests -k "name" -q            # one test by name
uv run python -m mypy src/opaque                      # type check
uv run python -m pylint src/opaque                    # lint (config in pyproject.toml)
uv run python examples/basic_example/main.py          # run the example app
```

In the `Notes:` list under that block, delete the bullet that begins "mypy currently aborts at" and the bullet that begins "Tests import `opaque` from the installed package", and add this bullet:

```markdown
- The interpreter floor is Python 3.11 and `uv` owns the environment. `uv.lock` is committed; run `uv sync --all-extras` after a pull that changes it.
```

- [ ] **Step 6: Commit**

```bash
git add .python-version uv.lock CLAUDE.md
git commit -m "chore(tooling): adopt uv as the project manager"
```

---

### Task 7: CI proves it, and the plans are tracked

**Files:**
- Create: `.github/workflows/ci.yml`
- Add to git: `docs/superpowers/`, `docs/ENGINEERING_REVIEW.md`, `CLAUDE.md`

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/ci.yml` with exactly this content:

```yaml
# OPAQUE Framework continuous integration.
#
# No CI is the root cause of the two release blockers the 2026-09-08 review
# found: a module with a syntax error and a package of example services that
# import a package that does not exist. Nothing ever imported them.
name: CI

on:
  push:
    branches: [master]
  pull_request:

jobs:
  check:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: ["3.11", "3.12"]

    env:
      # Qt needs a platform plugin. Every test in this suite is headless.
      QT_QPA_PLATFORM: offscreen

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Create the environment
        # Not --all-extras. The `build` extra pulls PyInstaller and Nuitka,
        # which are tens of megabytes on each of the four matrix legs, and no
        # test in this suite runs a real build. `themes` is included because
        # the theme service imports its packages.
        run: >
          uv sync --extra dev --extra themes
          --python ${{ matrix.python-version }}

      - name: Install the Linux Qt runtime libraries
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y libegl1 libgl1 libxkbcommon-x11-0 libdbus-1-3

      - name: Import every module
        run: uv run python -m pytest tests/test_imports.py -q

      - name: Run the suite
        run: uv run python -m pytest tests -q

      - name: Type check
        run: uv run python -m mypy src/opaque

      - name: Lint
        run: uv run python -m pylint src/opaque
```

- [ ] **Step 2: Decide the gate for mypy and pylint**

Run:

```
uv run python -m mypy src/opaque
```

If mypy reports errors, the `Type check` step will fail the build. Do **not** loosen mypy to make it green. Instead, in `.github/workflows/ci.yml`, add `continue-on-error: true` to the `Type check` step and the `Lint` step, and add this comment directly above the `Type check` step:

```yaml
      # These two steps report but do not gate yet. Plan 10 Task 8 removes
      # continue-on-error once the existing error count reaches zero.
```

If mypy reports no errors, leave both steps gating and skip this step.

- [ ] **Step 3: Track the design record**

Run:

```bash
git add CLAUDE.md docs/ENGINEERING_REVIEW.md docs/superpowers
git commit -m "docs: track the engineering review and the design plans"
```

- [ ] **Step 4: Commit the workflow**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: import every module, run the suite, mypy and pylint"
```

- [ ] **Step 5: Report the CI state**

CI runs on GitHub. This repository's remote is `github.com/sfadiga/OPAQUE`, which is a personal namespace, not an approved Archer destination. **Do not push.** Report to the user that the workflow is committed locally and that they must push it themselves.

---

## Self-review notes

- Review 2.7 lists "no CI configuration at all" as the root cause of 2.4 and 2.5. Task 2 fixes 2.4 and Task 2's test (`tests/test_imports.py`) is what catches both; 2.5 itself is repaired in Plan 02 Task 4, and `tests/test_imports.py` will not catch it because the example services are outside the `opaque` package. Plan 02 Task 4 therefore adds its own import test for the examples.
- `tests/test_example_app.py` touches `ServiceLocator._services` directly. That is a private attribute on purpose: the locator has no reset API, and adding one is Plan 07's job, which is where this fixture gets replaced.
- The `pythonpath = ["src"]` entry makes bare `pytest` work on a fresh clone. It does not replace `uv sync`; the Qt dependency still has to be installed.
