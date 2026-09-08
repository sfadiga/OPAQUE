# Typed Service Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a wrong service name impossible to write, and make a missing service impossible to ignore.

**Architecture:** `ServiceLocator.get_service(name)` takes a string and answers `Optional[BaseService]`. Every caller pays twice for that: a misspelled name is a silent `None` instead of an error, which is how `console_presenter.py` asked for `"theme"` for months while the service was registered as `"themes"`, and every caller that wants a real method has to cast or guard. Decision D8 keeps the locator and types it: `ServiceLocator.get(SettingsService)` returns a `SettingsService` and raises when it is missing, `get_optional(SettingsService)` returns `Optional[SettingsService]` for the case where absence is normal. The string survives in exactly one place per service, as a `SERVICE_NAME` constant on the service class, which is also what the locator keys on.

**Tech Stack:** Python 3.11 (`TypeVar`, `Type`), PySide6, pytest, mypy.

**Closes:** review 4.1, decision D8.

**Depends on:** Plan 06. The interpreter is `uv run python`.

---

## Rules that apply to every task here

1. Read `docs/superpowers/plans/2026-09-08-techdebt-00-index.md` first. The rules there are binding.
2. Run every command from `C:\Users\sfadiga\sandro\opaque`.
3. There are 23 `get_service(` call sites in the repository: 13 in `src`, the rest in `tests` and `examples`. Task 3 and Task 4 convert all of them. Do not leave one behind.
4. A service that is genuinely optional keeps an optional lookup. The console service is registered only when a console feature exists, so it is the one clear case. Do not turn a real optional into a raise.

---

## File structure

| File | Responsibility |
|---|---|
| Modify: `src/opaque/services/service.py` | `SERVICE_NAME` on `BaseService`, and the two typed lookups on `ServiceLocator`. |
| Modify: every module under `src/opaque/services/` | Each service declares its own `SERVICE_NAME`. |
| Modify: 13 call sites under `src/opaque/` | Typed lookups replace the string lookups. |
| Modify: the call sites under `tests/` and `examples/` | The same. |
| Create: `tests/test_service_locator.py` | The locator contract. |
| Modify: `CLAUDE.md` | The service access rule. |

---

## Task 1: Every service declares its own name

**Files:**
- Modify: `src/opaque/services/service.py:20-40`
- Modify: `src/opaque/services/settings_service.py`, `workspace_service.py`, `theme_service.py`, `notification_service.py`, `logger_service.py`, `single_instance_service.py`, `console_service.py`, `version_service.py`
- Test: `tests/test_service_locator.py`

The name a service registers under is written as a literal inside its own `super().__init__("...")` call, and the name a caller asks for is written as another literal somewhere else. Nothing connects the two. A class attribute does.

- [ ] **Step 1: Write the failing test**

Create `tests/test_service_locator.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the service locator contract."""

import pytest

from opaque.services.console_service import ConsoleService
from opaque.services.logger_service import LoggerService
from opaque.services.notification_service import NotificationService
from opaque.services.service import BaseService, ServiceLocator
from opaque.services.settings_service import SettingsService
from opaque.services.single_instance_service import SingleInstanceService
from opaque.services.theme_service import ThemeService
from opaque.services.version_service import VersionManager
from opaque.services.workspace_service import WorkspaceService

SERVICE_CLASSES = [
    ConsoleService,
    LoggerService,
    NotificationService,
    SettingsService,
    SingleInstanceService,
    ThemeService,
    VersionManager,
    WorkspaceService,
]

EXPECTED_NAMES = {
    ConsoleService: "console",
    LoggerService: "logger",
    NotificationService: "notification",
    SettingsService: "settings",
    SingleInstanceService: "single_instance",
    ThemeService: "themes",
    VersionManager: "version",
    WorkspaceService: "workspace",
}


@pytest.fixture(autouse=True)
def empty_locator():
    """Give every test an empty locator and put nothing back."""
    ServiceLocator.cleanup_services()
    yield
    ServiceLocator.cleanup_services()


@pytest.mark.parametrize("service_class", SERVICE_CLASSES)
def test_every_service_declares_a_name(service_class):
    assert service_class.SERVICE_NAME != ""


@pytest.mark.parametrize("service_class", SERVICE_CLASSES)
def test_the_declared_name_is_the_registered_name(service_class):
    assert service_class.SERVICE_NAME == EXPECTED_NAMES[service_class]


def test_the_base_class_declares_no_name():
    assert BaseService.SERVICE_NAME == ""


def test_an_instance_reports_the_declared_name(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    assert service.name == "settings"
```

If a service class name in that list does not exist, correct the list to the real class names and say what you changed. Find them with:

```bash
grep -rn "class .*BaseService" --include=*.py src/opaque/services
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_service_locator.py -q
```

Expected: every test FAILS with `AttributeError: type object '...' has no attribute 'SERVICE_NAME'`.

- [ ] **Step 3: Write the implementation**

In `src/opaque/services/service.py`, add the attribute and let the constructor use it. Before:

```python
class BaseService(QObject):
    """
    Abstract base class for all services in the application.
    Services encapsulate business logic and can be accessed via the service locator.
    """

    def __init__(self, name: str):
        """
        Initialize the service.
        Args:
            name: service name for identification
        """
        super().__init__()  # Initialize QObject properly
        self._name = name
        self._initialized = False
```

After:

```python
class BaseService(QObject):
    """
    Abstract base class for all services in the application.
    Services encapsulate business logic and can be accessed via the service locator.

    A subclass declares SERVICE_NAME, and that one string is both the name it
    registers under and the key ServiceLocator.get() looks up. The name used
    to be a literal inside each constructor call and another literal at each
    call site, with nothing connecting the two.
    """

    # The registry key of this service. A subclass must declare it. Empty on
    # the base class, which is never registered.
    SERVICE_NAME: str = ""

    def __init__(self, name: Optional[str] = None):
        """
        Initialize the service.

        Args:
            name: Service name for identification. Defaults to SERVICE_NAME,
                which is what every service in the framework uses. Pass a
                name only to register two instances of one class, which the
                framework never does.

        Raises:
            ValueError: When neither a name nor a SERVICE_NAME is given.
        """
        super().__init__()  # Initialize QObject properly
        resolved = name or self.SERVICE_NAME
        if not resolved:
            raise ValueError(
                f"{type(self).__name__} must declare SERVICE_NAME, for "
                f"example:\n"
                f"    class {type(self).__name__}(BaseService):\n"
                f"        SERVICE_NAME = 'my_service'\n"
                f"It is the key ServiceLocator uses.")
        self._name = resolved
        self._initialized = False
```

- [ ] **Step 4: Declare the name on every service**

Add `SERVICE_NAME` as the first line of each class body, and drop the string from the `super().__init__` call. For `SettingsService` the change reads:

```python
class SettingsService(BaseService):
    """Manages application settings persistence."""

    SERVICE_NAME = "settings"

    settings_changed = Signal(str, object)  # feature_id, settings

    def __init__(self, settings_file: Optional[Path] = None):
        ...
        super().__init__()
```

Do the same for all eight, using exactly these strings so no stored data and no call site changes meaning:

| Class | `SERVICE_NAME` |
|---|---|
| `ConsoleService` | `"console"` |
| `LoggerService` | `"logger"` |
| `NotificationService` | `"notification"` |
| `SettingsService` | `"settings"` |
| `SingleInstanceService` | `"single_instance"` |
| `ThemeService` | `"themes"` |
| `VersionManager` | `"version"` |
| `WorkspaceService` | `"workspace"` |

`ThemeService` keeps `"themes"`, plural. It is the registered name and changing it would break every stored reference and every caller; Plan 06 Task 1 already fixed the one caller that asked for the singular.

Find every `super().__init__("` still carrying a name:

```bash
grep -rn 'super().__init__("' --include=*.py src/opaque/services
```

Expected when you are done: no output.

- [ ] **Step 5: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_service_locator.py -q
```

Expected: `18 passed`.

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/services tests/test_service_locator.py
git commit -m "refactor(services): let each service declare its own registry name"
```

---

## Task 2: Two typed lookups

**Files:**
- Modify: `src/opaque/services/service.py` (`ServiceLocator`)
- Test: `tests/test_service_locator.py` (add to it)

`get_service(name)` answers `Optional[BaseService]`, so a caller that wants `SettingsService.save_feature_settings` has to guard, cast, or hope. The two new lookups take the class, so the name cannot be misspelled and the answer has the type the caller asked for.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_service_locator.py`:

```python
def test_get_returns_the_registered_service(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    ServiceLocator.register_service(service)

    assert ServiceLocator.get(SettingsService) is service


def test_get_answers_with_the_type_that_was_asked_for(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    ServiceLocator.register_service(service)

    found = ServiceLocator.get(SettingsService)
    assert isinstance(found, SettingsService)


def test_get_raises_when_the_service_is_missing():
    with pytest.raises(LookupError) as error:
        ServiceLocator.get(SettingsService)

    message = str(error.value)
    assert "SettingsService" in message
    assert "settings" in message


def test_the_missing_service_message_lists_what_is_registered(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    ServiceLocator.register_service(service)

    with pytest.raises(LookupError) as error:
        ServiceLocator.get(NotificationService)

    assert "settings" in str(error.value)


def test_get_optional_answers_none_when_the_service_is_missing():
    assert ServiceLocator.get_optional(ConsoleService) is None


def test_get_optional_returns_the_registered_service(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    ServiceLocator.register_service(service)

    assert ServiceLocator.get_optional(SettingsService) is service


def test_get_raises_when_another_class_holds_the_name(tmp_path):
    class _Impostor(BaseService):
        SERVICE_NAME = "settings"

        def initialize(self) -> None:
            super().initialize()

        def cleanup(self) -> None:
            super().cleanup()

    impostor = _Impostor()
    impostor.initialize()
    ServiceLocator.register_service(impostor)

    with pytest.raises(TypeError) as error:
        ServiceLocator.get(SettingsService)

    assert "_Impostor" in str(error.value)


def test_a_service_whose_name_does_not_match_its_class_is_refused(tmp_path):
    service = SettingsService(tmp_path / "settings.json")
    service.initialize()
    service._name = "something_else"

    with pytest.raises(ValueError) as error:
        ServiceLocator.register_service(service)

    assert "something_else" in str(error.value)


def test_the_string_lookup_is_gone():
    assert not hasattr(ServiceLocator, "get_service")
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_service_locator.py -q -k "get_ or string_lookup or does_not_match"
```

Expected: every one FAILS. `ServiceLocator` has no `get`, no `get_optional`, and still has `get_service`.

- [ ] **Step 3: Write the implementation**

In `src/opaque/services/service.py`, add the type variable above `class ServiceLocator`:

```python
# Bound to BaseService so ServiceLocator.get() can only be asked for a real
# service class, and so the answer keeps the type the caller asked for.
ServiceType = TypeVar("ServiceType", bound="BaseService")
```

and extend the typing import:

```python
from typing import Optional, Type, TypeVar
```

Then replace `get_service` with the two typed lookups:

```python
    @classmethod
    def get(cls, service_class: Type[ServiceType]) -> ServiceType:
        """
        Return the registered service of this class.

        Use this when the application cannot work without the service, which
        is the normal case. It raises instead of answering None, because a
        None that is never checked is how a misspelled service name stayed
        in the code base for months without one failing test.

        Args:
            service_class: The service class to look up. Its SERVICE_NAME is
                the registry key.

        Returns:
            The registered instance, typed as the class that was asked for.

        Raises:
            LookupError: When no service is registered under that name.
            TypeError: When another class is registered under that name.
        """
        with cls._lock:
            found = cls._services.get(service_class.SERVICE_NAME)
            registered = sorted(cls._services)

        if found is None:
            raise LookupError(
                f"No {service_class.__name__} is registered under the name "
                f"'{service_class.SERVICE_NAME}'. Registered services: "
                f"{registered}. A service must be initialized and registered "
                f"before a feature asks for it; BaseApplication.__init__ does "
                f"that for the framework services.")

        if not isinstance(found, service_class):
            raise TypeError(
                f"The name '{service_class.SERVICE_NAME}' is registered by "
                f"{type(found).__name__}, not by {service_class.__name__}.")

        return found

    @classmethod
    def get_optional(
            cls, service_class: Type[ServiceType]) -> Optional[ServiceType]:
        """
        Return the registered service of this class, or None.

        Use this only where absence is normal. The console service is the one
        such case in the framework: it exists only when a console feature has
        been registered.

        Args:
            service_class: The service class to look up.

        Returns:
            The registered instance, or None when it is not registered or
            another class holds the name.
        """
        with cls._lock:
            found = cls._services.get(service_class.SERVICE_NAME)

        if found is None or not isinstance(found, service_class):
            return None

        return found
```

Then make registration refuse a name that does not match the class. In `register_service`, after the "already registered" check, add:

```python
            expected = type(service).SERVICE_NAME
            if expected and service.name != expected:
                raise ValueError(
                    f"{type(service).__name__} declares SERVICE_NAME "
                    f"'{expected}' but is registering as '{service.name}'. "
                    f"ServiceLocator.get() looks up the declared name, so a "
                    f"service registered under any other name cannot be "
                    f"found.")
```

- [ ] **Step 4: Run the test to verify it fails on the last test only**

```bash
uv run python -m pytest tests/test_service_locator.py -q
```

Expected: every test passes except `test_the_string_lookup_is_gone`, which still FAILS. `get_service` is removed in Task 4, after every call site is converted; removing it now would break the suite.

- [ ] **Step 5: Mark the old lookup**

Replace the docstring of `get_service` so the next reader does not add a new caller:

```python
    @classmethod
    def get_service(cls, name: str) -> Optional[BaseService]:
        """
        Get a registered service by name. Do not use this in new code.

        It answers None for a name nothing registered, and the answer has no
        useful type. Use ServiceLocator.get(SomeService) instead, or
        get_optional(SomeService) where absence is normal. This method is
        removed in Task 4 of this plan, once every call site is converted.

        Args:
            name: Service identifier

        Returns:
            Service instance or None if not found
        """
        with cls._lock:
            return cls._services.get(name)
```

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/services/service.py tests/test_service_locator.py
git commit -m "feat(services): add typed service lookups to the locator"
```

---

## Task 3: Convert the framework call sites

**Files:**
- Modify: `src/opaque/models/logger_model.py`, `src/opaque/models/notification_model.py`
- Modify: `src/opaque/presenters/app_presenter.py`, `src/opaque/presenters/console_presenter.py`, `src/opaque/presenters/notification_presenter.py`
- Modify: `src/opaque/services/logger_service.py`
- Modify: `src/opaque/view/application.py`, `src/opaque/view/dialogs/settings.py`, `src/opaque/view/widgets/notification_widget.py`
- Test: the whole suite

Twelve call sites in `src` ask for a service by string. Each becomes a typed lookup. The choice between `get` and `get_optional` is not free: use `get` where the code already assumed the service was there, and `get_optional` only where a real branch handles the absence.

- [ ] **Step 1: List the call sites**

```bash
grep -rn "get_service(" --include=*.py src/opaque | grep -v "def get_service"
```

Expected: twelve lines. Write them down; you convert every one.

- [ ] **Step 2: Convert the ones that must not be missing**

Use this table. The left column is the current call, the right column replaces it.

| Current | Replacement |
|---|---|
| `ServiceLocator.get_service("settings")` | `ServiceLocator.get(SettingsService)` |
| `ServiceLocator.get_service("themes")` | `ServiceLocator.get(ThemeService)` |
| `ServiceLocator.get_service("notification")` | `ServiceLocator.get(NotificationService)` |
| `ServiceLocator.get_service("logger")` | `ServiceLocator.get(LoggerService)` |
| `ServiceLocator.get_service("console")` | `ServiceLocator.get_optional(ConsoleService)` |

Add the import each file needs beside its existing `ServiceLocator` import, for example:

```python
from opaque.services.service import ServiceLocator
from opaque.services.settings_service import SettingsService
```

`src/opaque/services/logger_service.py` asks for the notification service inside `_send_to_notification_service`. That module cannot import `notification_service` at module scope, because `notification_service` does not import it back but the local import there is already deliberate. Keep the import inside the method and change only the lookup:

```python
            from opaque.services.notification_service import (
                NotificationLevel,
                NotificationService,
            )

            notification_service = ServiceLocator.get_optional(
                NotificationService)
            if notification_service is None:
                return
```

That call site keeps `get_optional`, because logging must work before any service is registered.

- [ ] **Step 3: Remove the guards that are now dead**

A call site that used `get` no longer needs its `if service is None` branch, and no longer needs `isinstance` or `cast`. Delete each one as you convert it, so the type checker is the only guard. Two examples:

`src/opaque/view/dialogs/settings.py`, before:

```python
        self.settings_service: SettingsService = ServiceLocator.get_service("settings")
        if not self.settings_service:
            raise RuntimeError("SettingsService not found.")
```

after:

```python
        # get() raises a LookupError that names the missing service and lists
        # what is registered, which is more than this check ever said.
        self.settings_service: SettingsService = ServiceLocator.get(
            SettingsService)
```

`src/opaque/view/application.py`, in `_init_application_settings`, before:

```python
        settings_service = ServiceLocator.get_service("settings")
        if isinstance(settings_service, SettingsService):
            settings_service.register_model(
                presenter.feature_id, presenter.model)
```

after:

```python
        ServiceLocator.get(SettingsService).register_model(
            presenter.feature_id, presenter.model)
```

`src/opaque/presenters/notification_presenter.py` keeps its `try` around `_setup_models`, so the `LookupError` there is caught and logged as before. Leave that `try` alone.

- [ ] **Step 4: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. A `LookupError` in a test means that test builds an object without registering the service it needs; register the service in that test's fixture and say which test you changed.

- [ ] **Step 5: Prove no string lookup is left in src**

```bash
grep -rn "get_service(" --include=*.py src/opaque | grep -v "def get_service"
```

Expected: no output.

- [ ] **Step 6: Type check**

```bash
uv run python -m mypy src/opaque
```

Expected: fewer errors than before this task, and no error of the form "Item None of Optional[BaseService] has no attribute". Record the count before and after.

- [ ] **Step 7: Commit**

```bash
git add src/opaque
git commit -m "refactor(services): ask the locator for a class, not a string"
```

---

## Task 4: Convert the tests and the examples, and remove the string lookup

**Files:**
- Modify: every file under `tests/` and `examples/` that calls `get_service`
- Modify: `src/opaque/services/service.py` (remove `get_service`)
- Test: `tests/test_service_locator.py`

- [ ] **Step 1: List the remaining call sites**

```bash
grep -rn "get_service(" --include=*.py tests examples
```

Expected: about ten lines. Convert each one with the same table Task 3 used.

- [ ] **Step 2: Convert them**

An example service under `examples/basic_example/services/` registers itself with a name of its own. Plan 02 Task 5 gave those three services the names `"calculation"`, `"data"` and `"logging"`. Give each one a `SERVICE_NAME` class attribute with that same string, drop the literal from its `super().__init__` call, and convert every lookup of it to `ServiceLocator.get(TheServiceClass)`.

- [ ] **Step 3: Remove the string lookup**

In `src/opaque/services/service.py`, delete the whole `get_service` classmethod.

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_service_locator.py -q
```

Expected: `27 passed`, including `test_the_string_lookup_is_gone`.

- [ ] **Step 5: Prove nothing calls it anywhere**

```bash
grep -rn "get_service" --include=*.py --include=*.md src examples tests docs README.md CLAUDE.md
```

Expected: no output. A hit in a document is a document that has to be corrected in this task.

- [ ] **Step 6: Run the whole suite and the examples**

```bash
uv run python -m pytest tests -q
uv run python examples/basic_example/main.py
uv run python examples/quickstart/main.py
```

Expected: zero failures, and both examples start and close with no traceback.

- [ ] **Step 7: Commit**

```bash
git add src examples tests docs README.md CLAUDE.md
git commit -m "refactor(services): remove the untyped service lookup"
```

---

## Task 5: Write the rule down

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/QUICK_REFERENCE.md`
- Test: `tests/test_documentation.py` (from Plan 02 Task 1) and `tests/test_service_locator.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_service_locator.py`:

```python
def test_the_service_table_in_the_quick_reference_is_complete():
    from pathlib import Path

    text = Path("docs/QUICK_REFERENCE.md").read_text(encoding="utf-8")
    for service_class in SERVICE_CLASSES:
        assert service_class.__name__ in text
        assert service_class.SERVICE_NAME in text
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_service_locator.py -q -k "quick_reference"
```

Expected: FAIL on the first service class the document does not name.

- [ ] **Step 3: Update CLAUDE.md**

In `## Architecture`, replace the whole `ServiceLocator` bullet:

```markdown
- **ServiceLocator** (`services/service.py`): typed. `ServiceLocator.get(SettingsService)` returns a `SettingsService` and raises `LookupError` naming the missing service when it is not registered; `get_optional(ConsoleService)` returns `Optional[...]` and is for the one case where absence is normal. The registry key is the `SERVICE_NAME` class attribute of the service, which is also the only place the string is written. Registered services: `SettingsService`, `WorkspaceService`, `ThemeService` (`"themes"`, plural), `NotificationService`, `LoggerService`, `SingleInstanceService`, `VersionManager`, and `ConsoleService` (lazy, only after a console feature exists). There is no `get_service(name)` any more.
```

- [ ] **Step 4: Update the quick reference**

In `docs/QUICK_REFERENCE.md`, replace the verified service name table Plan 02 Task 3 wrote with one that has three columns: the class, its `SERVICE_NAME`, and how to reach it. Every class in `SERVICE_CLASSES` gets a row. Show the two calls once above the table:

```python
from opaque.services.service import ServiceLocator
from opaque.services.settings_service import SettingsService

settings = ServiceLocator.get(SettingsService)            # raises if missing
console = ServiceLocator.get_optional(ConsoleService)     # may be None
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_service_locator.py tests/test_documentation.py -q
```

Expected: zero failures. `tests/test_documentation.py` imports every `opaque` name the documents show, so a wrong class name in the table fails there.

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 7: Commit**

```bash
git add CLAUDE.md docs/QUICK_REFERENCE.md tests/test_service_locator.py
git commit -m "docs(services): document the typed service lookups"
```

---

## Verification of the whole plan

- [ ] **Check 1: a wrong name cannot be written**

```bash
uv run python -c "
from PySide6.QtWidgets import QApplication
from opaque.services.service import ServiceLocator
from opaque.services.theme_service import ThemeService
app = QApplication([])
try:
    ServiceLocator.get(ThemeService)
except LookupError as error:
    print('LookupError:', error)
"
```

Expected: a `LookupError` whose text names `ThemeService`, the name `themes`, and the empty list of registered services. This is what the old code answered with `None`.

- [ ] **Check 2: no string lookup survives**

```bash
grep -rn "get_service" --include=*.py src examples tests
```

Expected: no output.

- [ ] **Check 3: the whole suite, the type check and the lint**

```bash
uv run python -m pytest tests -q
uv run python -m mypy src/opaque
uv run python -m pylint src/opaque/services
```

Expected: the suite reports zero failures. Report the mypy error count and compare it with the count you recorded in Task 3 Step 6.

---

## What this plan does not do

| Left open | Owner |
|---|---|
| A feature still reaches a service through the process-wide locator instead of being handed what it needs. `FeatureContext` changes that. | Plan 08 Task 1 to Task 4 |
| `VersionManager` is registered by nothing, so `ServiceLocator.get(VersionManager)` raises everywhere. | Plan 10 Task 3 |
| The locator is still a process-wide singleton, so a test has to clean it up by hand. | Plan 08 Task 4 |
