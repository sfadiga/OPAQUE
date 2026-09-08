# Plan 02 — Documentation and Example Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every document and every example in the repository true, and add one test that keeps them true.

**Architecture:** The repair is not "rewrite the docs". A rewritten document decays the same way the current one did. So the order is: first build the checker (a test that extracts every `opaque` import from every Markdown file and proves the module and the name exist), then fix what it reports, then delete what cannot be fixed cheaply. The README quick start stops being a copy of code and becomes an include of a file that a test executes.

**Tech Stack:** pytest, Python `ast` and `importlib`, Markdown.

Read **Rules for the executing agent** in `2026-09-08-techdebt-00-index.md` before you start.

**Closes:** review 2.2, 2.3, 2.5, 5.1, 5.2, 5.4 (docstring half), 5.5.

**Depends on:** Plan 01 (the checker imports `opaque.build_tools`, which only parses after Plan 01 Task 2).

**Note for later plans:** Plans 05 to 08 change public signatures. `tests/test_documentation.py` and `tests/test_quickstart.py` will fail when they do. That is the point: the failing test is the reminder to update the document in the same commit.

---


## A gap the final review of Plan 01 found

`tests/test_example_app.py`, added by Plan 01 Task 4, builds the reference
example headless and passes. It looks like it covers the example services.
It does not. `examples/basic_example/main.py` never imports
`examples/basic_example/services/`, so the broken
`from opaque.core.services import BaseService` in those three files never
executes.

`tests/test_imports.py` does not cover them either. It walks the `opaque`
package only, and the examples live outside it.

So review item 2.5 has no test coverage at all right now, from either
direction. The import test this plan adds for the examples is the only
thing that will catch it. Do not assume any existing test helps.

## File Structure

| Path | Responsibility |
|---|---|
| Create `tests/test_documentation.py` | Extracts every `opaque` import from every `.md` file and proves module and name exist. The permanent guard. |
| Create `examples/quickstart/main.py` | The smallest application that really runs. The README includes it verbatim. |
| Create `tests/test_quickstart.py` | Proves the README block and the file are identical, and builds the application headless. |
| Modify `README.md` | Quick start replaced by the verified snippet. Dead documentation links removed. |
| Delete `docs/API.md` | 668 lines describing a framework that does not exist. Regeneration is Plan 10 Task 7. |
| Rewrite `docs/QUICK_REFERENCE.md` | Short and verified. Every name checked against source. |
| Modify `docs/DEVELOPER_GUIDE.md`, `docs/BUILD_GUIDE.md`, `docs/VERSION_MANAGEMENT.md` | Only the lines the checker reports. |
| Modify `examples/basic_example/services/*.py` | Import the real `BaseService`. Register under the names the presenters look up. |
| Modify `examples/basic_example/main.py` | Register the three example services. Nothing registers them today, so every lookup in the example returns `None`. |
| Modify `src/opaque/presenters/app_presenter.py:25` | The `TYPE_CHECKING` import of the ghost package `opaque.core.application`. |
| Modify `src/opaque/view/application.py:48-57`, `294-300` | Two false docstrings. |
| Modify `CLAUDE.md` | The "Do not trust these docs" section describes the state after this plan. |

---

### Task 1: The documentation checker

**Files:**
- Create: `tests/test_documentation.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_documentation.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""
Prove that every `opaque` import printed in a Markdown file really exists.

For a human, wrong documentation costs one puzzled minute. For an AI agent
it costs a whole debugging loop: the agent trusts the document, writes code
against a class that was never written, and then has to re-derive the API
from source. This test makes that failure impossible to ship.

The test reads import statements only. It does not execute a snippet: most
snippets are fragments that need a running QApplication. An import that
resolves plus a name that resolves catches every defect the 2026-09-08
review found in the documentation.
"""

import ast
import importlib
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# A document may be kept on purpose while it is being rewritten. Name it
# here with the reason, or delete it. An empty exception list is the goal.
SKIPPED_FILES: dict[str, str] = {}

_CODE_BLOCK = re.compile(r"```(?:python|py)\n(.*?)```", re.DOTALL)


def _markdown_files() -> list[Path]:
    files = [REPO_ROOT / "README.md", REPO_ROOT / "CLAUDE.md"]
    files.extend(sorted((REPO_ROOT / "docs").rglob("*.md")))
    return [f for f in files if f.is_file() and f.name not in SKIPPED_FILES]


def _opaque_imports(text: str) -> list[tuple[str, tuple[str, ...]]]:
    """
    Return every opaque import in the Markdown text.

    Each entry is (module_name, imported_names). A plain `import opaque.x`
    gives an empty name tuple.
    """
    found: list[tuple[str, tuple[str, ...]]] = []
    for block in _CODE_BLOCK.findall(text):
        try:
            tree = ast.parse(block)
        except SyntaxError:
            # A fragment that is not a whole module. Its imports are still
            # readable line by line.
            tree = None
        if tree is None:
            for line in block.splitlines():
                stripped = line.strip()
                if not stripped.startswith(("from opaque", "import opaque")):
                    continue
                try:
                    tree = ast.parse(stripped)
                except SyntaxError:
                    continue
                found.extend(_from_tree(tree))
            continue
        found.extend(_from_tree(tree))
    return found


def _from_tree(tree: ast.AST) -> list[tuple[str, tuple[str, ...]]]:
    found: list[tuple[str, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] == "opaque":
                found.append((node.module, tuple(a.name for a in node.names)))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "opaque":
                    found.append((alias.name, ()))
    return found


CASES = [
    pytest.param(path, module, names, id=f"{path.name}:{module}")
    for path in _markdown_files()
    for module, names in _opaque_imports(path.read_text(encoding="utf-8"))
]


def test_the_scanner_found_documentation_to_check():
    assert len(CASES) > 10


@pytest.mark.parametrize("path,module,names", CASES)
def test_documented_import_resolves(path, module, names):
    try:
        imported = importlib.import_module(module)
    except ImportError as error:
        pytest.fail(f"{path.name} documents '{module}', which does not exist: {error}")

    missing = [name for name in names if not hasattr(imported, name)]
    assert missing == [], f"{path.name} documents {missing} in '{module}'"
```

- [ ] **Step 2: Run the test and record the report**

Run:

```
uv run python -m pytest tests/test_documentation.py -q
```

Expected: FAIL. Among the failures:
- `API.md` documents `build_executable` in `opaque.build_tools.cli`, and the module `opaque.build_tools.exceptions`, neither of which exists.
- `API.md` documents `Application` in `opaque.view.application`.
- `QUICK_REFERENCE.md` documents `Application`, `AppModel` in `opaque.models.app_model`, `AppPresenter` in `opaque.presenters.app_presenter`, and `AppView` in `opaque.view.app_view`.

Write the full failure list into the commit body of Task 6. It is the work list for Tasks 2 to 5.

- [ ] **Step 3: Commit the checker while it still fails**

The checker is committed first, deliberately: the next tasks are graded by it.

```bash
git add tests/test_documentation.py
git commit -m "test(docs): prove every documented opaque import exists"
```

---

### Task 2: A quick start that runs

**Files:**
- Create: `examples/quickstart/main.py`
- Create: `tests/test_quickstart.py`
- Modify: `README.md:33-95`

`MyAppConfig()` in the current README raises `TypeError: Can't instantiate abstract class MyAppConfig with abstract methods get_application_description, get_application_icon, get_application_name, get_application_organization, get_application_title`. Field declarations do not satisfy the five abstract accessors. The README shows a `MyPresenter(BasePresenter): pass`, which also cannot be instantiated: `bind_events`, `update`, `on_view_show`, and `on_view_close` are abstract.

- [ ] **Step 1: Write the runnable example**

Create `examples/quickstart/main.py` with exactly this content:

```python
# This Python file uses the following encoding: utf-8
"""
The smallest OPAQUE application that runs.

This file is the README quick start. tests/test_quickstart.py proves the two
are identical and builds this window headless, so the first thing a user
copies cannot be broken.
"""
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from opaque import (
    BaseApplication,
    BaseModel,
    BasePresenter,
    BaseView,
    DefaultApplicationConfiguration,
)


class QuickStartConfiguration(DefaultApplicationConfiguration):
    """The five accessors below are abstract. Every application must write them."""

    def get_application_name(self) -> str:
        return "QuickStart"

    def get_application_title(self) -> str:
        return "OPAQUE Quick Start"

    def get_application_description(self) -> str:
        return "The smallest OPAQUE application."

    def get_application_organization(self) -> str:
        return "My Company"

    def get_application_icon(self) -> QIcon:
        return QIcon()


class GreetingModel(BaseModel):
    """A feature model. feature_name() is the text the toolbar shows."""

    def feature_name(self) -> str:
        return "Greeting"

    def feature_icon(self) -> QIcon:
        return QIcon()

    def feature_description(self) -> str:
        return "Says hello."


class GreetingView(BaseView):
    """A feature view is one MDI sub-window. Build the UI before the presenter exists."""

    def __init__(self, app, parent=None) -> None:
        super().__init__(app, parent)
        self.label = QLabel(self.tr("Hello OPAQUE"))
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self.label)
        self.setWidget(content)


class GreetingPresenter(BasePresenter):
    """
    All four methods below are abstract on BasePresenter. A subclass that
    leaves one out cannot be instantiated.

    on_view_close must call super(): the base method holds the real cleanup.
    """

    def bind_events(self) -> None:
        pass

    def update(self, field_name, new_value, old_value=None, model=None) -> None:
        pass

    def on_view_show(self) -> None:
        pass

    def on_view_close(self) -> None:
        super().on_view_close()


class QuickStartApplication(BaseApplication):
    """
    The registration order is fixed: model, then view, then presenter, then
    register_feature. Each of the three takes the application object.
    """

    def __init__(self) -> None:
        super().__init__(QuickStartConfiguration())
        model = GreetingModel(self)
        view = GreetingView(self)
        self.register_feature(GreetingPresenter(model, view, self))


if __name__ == "__main__":
    qt_application = QApplication(sys.argv)
    window = QuickStartApplication()
    if not window.try_acquire_lock():
        window.show_already_running_message()
        sys.exit(1)
    window.show()
    sys.exit(qt_application.exec())
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_quickstart.py` with exactly this content:

```python
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
    saved = dict(ServiceLocator._services)
    ServiceLocator._services.clear()
    yield
    ServiceLocator._services.clear()
    ServiceLocator._services.update(saved)


def test_the_quickstart_application_builds(qapp, isolated_locator, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(QUICKSTART.parent))
    try:
        import importlib

        module = importlib.import_module("main")
        window = module.QuickStartApplication()
        try:
            assert "Greeting" in window._registered_features
        finally:
            window.close()
            window.deleteLater()
    finally:
        sys.path.remove(str(QUICKSTART.parent))
        sys.modules.pop("main", None)
```

- [ ] **Step 3: Run the test to verify it fails**

Run:

```
uv run python -m pytest tests/test_quickstart.py -q
```

Expected: FAIL on the first test, "the quickstart markers are missing from README.md". The second test passes.

- [ ] **Step 4: Put the verified snippet in the README**

In `README.md`, replace everything from the line `## 🏁 Quick Start` down to and including the line `self.register_feature(MyPresenter(MyModel(self), MyView(self), self))` and its closing fence, with exactly this:

````markdown
## 🏁 Quick Start

Create a `main.py`. This is `examples/quickstart/main.py`; the test suite builds it on every run, so it cannot go stale.

<!-- quickstart:begin -->
```python
PASTE THE WHOLE CONTENT OF examples/quickstart/main.py HERE
```
<!-- quickstart:end -->

Run it:

```bash
uv run python examples/quickstart/main.py
```

### What the framework demands of you

| You write | The framework needs |
|---|---|
| A configuration | The five `get_application_*` accessors. They are abstract; field declarations do not satisfy them. |
| A model | `feature_name()`, `feature_icon()`, `feature_description()`. |
| A view | A widget tree, built in `__init__`, handed to `setWidget()`. |
| A presenter | `bind_events()`, `update()`, `on_view_show()`, `on_view_close()`. All four are abstract. |
| Registration | Model, then view, then presenter, then `register_feature(presenter)`. In that order. |

Two traps that cost an hour each:

- `BasePresenter.__init__` calls `bind_events()` at its end. An attribute your subclass creates *after* `super().__init__(...)` does not exist yet inside `bind_events()`. Create it before the `super()` call, or guard for `None`.
- `on_view_close()` carries the real cleanup in its body. An override must call `super().on_view_close()`.
````

Then replace the placeholder line `PASTE THE WHOLE CONTENT OF examples/quickstart/main.py HERE` with the exact bytes of `examples/quickstart/main.py`, including its final newline. The test compares them character for character.

- [ ] **Step 5: Run the test to verify it passes**

Run:

```
uv run python -m pytest tests/test_quickstart.py -q
```

Expected: PASS, 2 passed.

- [ ] **Step 6: Commit**

```bash
git add examples/quickstart/main.py tests/test_quickstart.py README.md
git commit -m "docs(readme): replace the quick start with a snippet the suite runs"
```

---

### Task 3: Delete `API.md`, rewrite `QUICK_REFERENCE.md`

**Files:**
- Delete: `docs/API.md`
- Rewrite: `docs/QUICK_REFERENCE.md`
- Modify: `README.md` (the Documentation link list)

- [ ] **Step 1: Delete the file that cannot be repaired cheaply**

`docs/API.md` is 668 lines. Its build-tools half documents `build_executable`, `output_dir`, and `opaque.build_tools.exceptions`, none of which exist; its framework half documents `Application`. Repairing it line by line costs more than generating it from source, which is Plan 10 Task 7.

Run:

```bash
git rm docs/API.md
```

- [ ] **Step 2: Rewrite the quick reference**

Replace the whole content of `docs/QUICK_REFERENCE.md` with exactly this:

````markdown
# OPAQUE Quick Reference

Every name on this page is checked by `tests/test_documentation.py`. If a name here stops existing, the suite fails.

The one worked example is `examples/quickstart/main.py` (smallest) and `examples/basic_example/main.py` (full).

## The contract

One feature is one MVP triple.

```python
from opaque import BaseApplication, BaseModel, BasePresenter, BaseView
```

| Class | Module | Is a | You must write |
|---|---|---|---|
| `BaseApplication` | `opaque.view.application` | `QMainWindow` shell: service registry, feature registry, toolbar, MDI area | `__init__` that calls `super().__init__(configuration)` then registers features |
| `BaseModel` | `opaque.models.model` | State plus feature identity | `feature_name()`, `feature_icon()`, `feature_description()` |
| `BaseView` | `opaque.view.view` | One MDI sub-window | the widget tree |
| `BasePresenter` | `opaque.presenters.presenter` | The wiring | `bind_events()`, `update()`, `on_view_show()`, `on_view_close()` |
| `DefaultApplicationConfiguration` | `opaque.models.configuration` | Application metadata | five `get_application_*` accessors |

## Registering a feature

Order matters. A wrong order raises a bare `AttributeError`.

```python
model = MyModel(self)
view = MyView(self)
presenter = MyPresenter(model, view, self)
self.register_feature(presenter)
```

## Model fields

```python
from opaque.models.annotations import BoolField, IntField, StringField, UIType
```

Declare fields as class attributes. `ModelMeta` turns each one into a validating property.

```python
class MyModel(BaseModel):
    title = StringField(default="Untitled", description="Window title", settings=True)
    rows = IntField(default=10, min_value=1, max_value=100, settings=True)
    verbose = BoolField(default=False, workspace=True)
```

| Argument | Effect |
|---|---|
| `settings=True` | The field appears in the Settings dialog and in `settings.json`. |
| `workspace=True` | The field is written to and read from workspace files. |
| `min_value`, `max_value`, `choices` | Checked on every assignment. A bad value raises `ValueError`. |
| `ui_type` | Which widget the Settings dialog builds. See `UIType`. |

A field write calls the presenter's `update()` method. Write model fields from the UI thread only.

## Services

```python
from opaque.services.service import BaseService, ServiceLocator
```

The locator is string-keyed and returns `Optional[BaseService]`, so a wrong name is a silent `None`. The registered names are:

| Name | Class | Module |
|---|---|---|
| `"settings"` | `SettingsService` | `opaque.services.settings_service` |
| `"workspace"` | `WorkspaceService` | `opaque.services.workspace_service` |
| `"themes"` | `ThemeService` | `opaque.services.theme_service` |
| `"notification"` | `NotificationService` | `opaque.services.notification_service` |
| `"logger"` | `LoggerService` | `opaque.services.logger_service` |
| `"single_instance"` | `SingleInstanceService` | `opaque.services.single_instance_service` |
| `"console"` | `ConsoleService` | `opaque.services.console_service` (registered only once a console feature exists) |

`"themes"` is plural. There is no `"theme"`.

Your own service must be initialized before it is registered. `register_service` raises `ValueError` otherwise.

```python
class CalculationService(BaseService):
    def __init__(self) -> None:
        super().__init__("calculation")

    def initialize(self) -> None:
        super().initialize()

    def cleanup(self) -> None:
        super().cleanup()


service = CalculationService()
service.initialize()
ServiceLocator.register_service(service)
```

## Themes

```python
from opaque.services.service import ServiceLocator

theme_service = ServiceLocator.get_service("themes")
theme_service.get_available_themes()          # every name this machine can apply
theme_service.apply_theme("Default")          # True when applied, False when unknown
theme_service.theme_changed.connect(repaint)  # a widget that paints must repaint
```

Never write a colour or a point size in a widget. Ask the token layer:

```python
from opaque.view.theme import tokens, type_scale
```

## Strings the user can see

Every one of them is a literal inside `self.tr()`. `tests/test_localisation.py` scans the source and fails the build on a violation.

```python
self.setWindowTitle(self.tr("Results"))     # correct
self.setWindowTitle(self.tr(f"{n} rows"))   # rejected: lupdate cannot read it
```

## Commands

```bash
uv sync --all-extras
uv run python -m pytest tests -q
uv run python -m mypy src/opaque
uv run python examples/quickstart/main.py
```
````

- [ ] **Step 3: Fix the documentation links in the README**

In `README.md`, replace the whole `## 📚 Documentation` list with exactly this:

```markdown
## 📚 Documentation

*   [**Quick Reference**](docs/QUICK_REFERENCE.md): The contract on one page. Every name is checked by the test suite.
*   [**Developer Guide**](docs/DEVELOPER_GUIDE.md): Bootstrapping, features, and the built-in services.
*   [**Build Guide**](docs/BUILD_GUIDE.md): How to create standalone executables.
*   [**Version Management**](docs/VERSION_MANAGEMENT.md): Handling application versions.
*   [**Engineering Review**](docs/ENGINEERING_REVIEW.md): The current known-defect list.
```

Also replace the `## 📂 Examples` list with exactly this, because two of the three named directories do not exist:

```markdown
## 📂 Examples

*   `examples/quickstart`: The smallest application that runs. The suite builds it on every run.
*   `examples/basic_example`: Full showcase of MVP, logging, console, tabs, and notifications.
```

- [ ] **Step 4: Run the checker**

Run:

```
uv run python -m pytest tests/test_documentation.py -q
```

Expected: the `API.md` and `QUICK_REFERENCE.md` failures are gone. Failures may remain in `DEVELOPER_GUIDE.md`, `BUILD_GUIDE.md`, and `VERSION_MANAGEMENT.md`; Task 4 handles those.

- [ ] **Step 5: Commit**

```bash
git add -A docs/API.md docs/QUICK_REFERENCE.md README.md
git commit -m "docs: delete API.md and rewrite the quick reference from source"
```

---

### Task 4: Fix what the checker still reports

**Files:**
- Modify: `docs/DEVELOPER_GUIDE.md`
- Modify: `docs/BUILD_GUIDE.md`
- Modify: `docs/VERSION_MANAGEMENT.md`

- [ ] **Step 1: List the remaining failures**

Run:

```
uv run python -m pytest tests/test_documentation.py -q --no-header -rf
```

Write down every reported `path:module` pair and the missing name.

- [ ] **Step 2: Repair each reported line**

For each failure, apply exactly one of these three repairs, in this order of preference:

1. **The name moved.** Correct the module path or the class name to the real one. Verify with:
   `uv run python -c "from <module> import <name>; print('ok')"`
2. **The name never existed but the behaviour does.** Replace the snippet with the real API. For `build_executable`, the real entry point is the `opaque-build` console script and `opaque.build_tools.builder.Builder`; Plan 09 gives that API its final shape, so keep the snippet minimal here.
3. **The name never existed and the behaviour does not either.** Delete the snippet and the paragraph that introduces it. Do not leave a "coming soon" line.

Known-good names for the three files, verified during this review:

| Name | Real module |
|---|---|
| `VersionManager` | `opaque.services.version_service` |
| `VersionInfoDialog`, `VersionStatusWidget`, `AboutDialog` | `opaque.view.dialogs.version_info` |
| `CloseableTabWidget`, `ColorPicker`, `OpaqueMdiSubWindow`, `SimplifiedNotificationList`, `ToastWidget`, `OpaqueMainToolbar` | `opaque.view.widgets` |
| `PyInstallerBuilder` | `opaque.build_tools.pyinstaller_builder` |
| `NuitkaBuilder` | `opaque.build_tools.nuitka_builder` |
| `Builder`, `BuildError` | `opaque.build_tools.builder` |
| `ConsolePresenter` | `opaque.presenters.console_presenter` |
| `ConsoleModel` | `opaque.models.console_model` |

`VERSION_MANAGEMENT.md` states that `VersionManager` is available through the service locator. It is not: nothing registers it. Replace any `ServiceLocator.get_service("version")` snippet with direct construction, `VersionManager()`, and add this note under the first mention:

```markdown
> `VersionManager` is not registered in the service locator. Construct it where you need it.
```

- [ ] **Step 3: Run the checker to verify it passes**

Run:

```
uv run python -m pytest tests/test_documentation.py -q
```

Expected: PASS, no failures, and `SKIPPED_FILES` in the test is still empty.

- [ ] **Step 4: Commit**

```bash
git add docs
git commit -m "docs: correct every documented import against the source"
```

---

### Task 5: The example services import and register

**Files:**
- Modify: `examples/basic_example/services/calculation_service.py`
- Modify: `examples/basic_example/services/data_service.py`
- Modify: `examples/basic_example/services/logging_service.py`
- Modify: `examples/basic_example/main.py`
- Modify: `src/opaque/presenters/app_presenter.py:25`
- Test: `tests/test_example_services.py`

Three defects sit on top of each other here. The files import `opaque.core.services`, which does not exist. Each service registers a name (`"CalculationService"`) that no presenter looks up (`"calculation"`). And `examples/basic_example/main.py` never registers any of them, so every lookup in the reference example returns `None` and the example silently runs with no services.

- [ ] **Step 1: Write the failing test**

Create `tests/test_example_services.py` with exactly this content:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```
uv run python -m pytest tests/test_example_services.py -q
```

Expected: FAIL, 3 failures, `ModuleNotFoundError: No module named 'opaque.core'`.

- [ ] **Step 3: Fix the imports and the names**

In each of the three files under `examples/basic_example/services/`, replace:

```python
from opaque.core.services import BaseService
```

with:

```python
from opaque.services.service import BaseService
```

In `calculation_service.py`, replace `super().__init__("CalculationService")` with:

```python
        # The name is the locator key. The presenters look up "calculation".
        super().__init__("calculation")
```

In `data_service.py`, replace `super().__init__("DataService")` with:

```python
        # The name is the locator key. The presenters look up "data".
        super().__init__("data")
```

In `logging_service.py`, replace `super().__init__("LoggingService")` with:

```python
        # The name is the locator key. The presenters look up "logging".
        super().__init__("logging")
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```
uv run python -m pytest tests/test_example_services.py -q
```

Expected: PASS, 3 passed.

- [ ] **Step 5: Register the services in the example**

In `examples/basic_example/main.py`, insert this method into `MyExampleApplication` directly above `def register_features(self):`:

```python
    def register_services(self) -> None:
        """
        Register the example services.

        A service must be initialized before it is registered; the locator
        raises ValueError otherwise. The name a service passes to
        BaseService.__init__ is the key the presenters look up.
        """
        from services.calculation_service import CalculationService
        from services.data_service import DataService
        from services.logging_service import LoggingService

        for service in (CalculationService(), DataService(), LoggingService()):
            service.initialize()
            ServiceLocator.register_service(service)
```

In the same file, add this import below `from opaque.models.configuration import DefaultApplicationConfiguration`:

```python
from opaque.services.service import ServiceLocator
```

And in `MyExampleApplication.__init__`, insert the call directly above `self.register_features()`:

```python
        self.register_services()
```

- [ ] **Step 6: Fix the ghost import in the framework**

In `src/opaque/presenters/app_presenter.py`, replace:

```python
if TYPE_CHECKING:
    from opaque.core.application import BaseApplication
```

with:

```python
if TYPE_CHECKING:
    from opaque.view.application import BaseApplication
```

Then confirm no reference to the ghost package survives. Run:

```bash
grep -rn "opaque.core" src examples docs README.md CLAUDE.md pyproject.toml
```

Expected: no output. If `CLAUDE.md` still names the ghost package as a warning, that single mention is allowed and Task 6 rewrites it.

- [ ] **Step 7: Run the whole suite**

Run:

```
uv run python -m pytest tests -q
```

Expected: PASS, no failures. `tests/test_example_app.py` from Plan 01 Task 4 now exercises the registered services too.

- [ ] **Step 8: Commit**

```bash
git add examples/basic_example src/opaque/presenters/app_presenter.py tests/test_example_services.py
git commit -m "fix(examples): import the real BaseService and register the services"
```

---

### Task 6: The docstrings that lie, and CLAUDE.md

**Files:**
- Modify: `src/opaque/view/application.py:48-57`, `294-300`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Fix the class docstring**

`BaseApplication`'s docstring names `application_name()`, `application_title()`, and `application_organization()` as methods the developer must implement. No such method exists on the class; the five accessors live on the configuration object.

In `src/opaque/view/application.py`, replace the class docstring (lines 48 to 57) with exactly this:

```python
    """
    The main application window: the MDI area, the toolbar, the service
    registry and the feature registry.

    A subclass writes one `__init__` that calls
    `super().__init__(configuration)` and then registers its features. It
    implements nothing else; the five application accessors
    (`get_application_name`, `get_application_title`,
    `get_application_description`, `get_application_organization`,
    `get_application_icon`) are abstract on
    `DefaultApplicationConfiguration`, not on this class.

    See `examples/quickstart/main.py` for the smallest complete subclass.
    """
```

- [ ] **Step 2: Fix the `register_feature` docstring**

The current text promises "The presenter will be instantiated when the feature is activated" — there is no lazy instantiation, the caller instantiates — and names a parameter `presenter_class` that does not exist.

Replace the docstring of `register_feature` (lines 295 to 301) with exactly this:

```python
        """
        Register one built MVP triple and show its window.

        The caller builds the triple, in this order: model, then view, then
        presenter. Nothing is lazy: the presenter passed here is already
        constructed and its `bind_events()` has already run.

        Registration does four things: it adds the feature to the registry,
        registers it with the workspace service and the settings service,
        adds its toolbar button, and adds its view to the MDI area.

        Args:
            presenter: The presenter of the feature to register.

        Raises:
            ValueError: When another feature is already registered under the
                same name.
        """
```

- [ ] **Step 3: Prove the docstrings name only real methods**

Run:

```
uv run python -c "from opaque import BaseApplication as A; d=A.__doc__ + A.register_feature.__doc__; bad=[n for n in ('application_name()','application_title()','application_organization()','presenter_class') if n in d]; print('leftover:', bad); assert not bad"
```

Expected: `leftover: []` and no assertion error.

- [ ] **Step 4: Bring CLAUDE.md up to date**

In `CLAUDE.md`, replace the whole `## Do not trust these docs` section with exactly this:

```markdown
## Documentation state

`docs/API.md` is deleted; it described a framework that does not exist. `docs/QUICK_REFERENCE.md` and the README quick start were rewritten from source on 2026-09-08 and are now guarded by tests: `tests/test_documentation.py` proves every `opaque` import printed in any Markdown file resolves, and `tests/test_quickstart.py` proves the README block is byte-identical to `examples/quickstart/main.py` and that it builds headless.

If you change a public name, those two tests fail. Update the document in the same commit; do not add the file to `SKIPPED_FILES`.

The worked examples are `examples/quickstart/main.py` (smallest) and `examples/basic_example/main.py` (full). The package `opaque.core` does not exist and never did — never import it.
```

In the `## Project` section, replace the sentence that begins "The reference application is" with exactly this:

```markdown
The reference applications are `examples/quickstart/main.py` (smallest, executed by the suite) and `examples/basic_example/main.py` (full).
```

- [ ] **Step 5: Run the whole suite**

Run:

```
uv run python -m pytest tests -q
```

Expected: PASS, no failures.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/application.py CLAUDE.md
git commit -m "docs(shell): correct the BaseApplication and register_feature docstrings"
```

---

## Self-review notes

- The checker reads imports, not whole snippets. A snippet can still be wrong in its *body* (a method that does not exist on a class that does). Plan 10 Task 7 adds the generated API reference, which is where method-level truth gets enforced.
- `tests/test_quickstart.py` and `tests/test_example_app.py` both reach into `ServiceLocator._services`. Plan 07 Task 5 replaces both fixtures with the public reset the typed locator gains.
- `SKIPPED_FILES` exists in the checker with an empty dictionary on purpose: it gives a future engineer a visible, reviewable place to record a temporary exception instead of deleting the test.
