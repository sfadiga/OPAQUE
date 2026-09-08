# Shell Lifecycle and Feature Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give a feature one identity, shut the application down in an order that lets a presenter save its work, and close the eight small shell defects the review confirmed.

**Architecture:** Three of these defects are one-line mistakes that no test could catch because nothing asserted the behaviour: a service asked for by the wrong name, a `cleanup()` that calls `initialize()`, and a shutdown that destroys the services before the presenters that use them. The large item is identity. A feature carries three keys today — `model.feature_name()` for the registry, `presenter.feature_id` for the settings file and the presenter class name for the workspace file — so renaming a window title moves the registry key, and renaming a class loses the saved workspace. Decision D5 replaces all three with one declared `FEATURE_ID` on the model, and makes `feature_name()` display-only, which is what a translated string has to be.

**Tech Stack:** Python 3.11, PySide6 (`QMdiArea`, `QShortcut`, `QStandardPaths`), pytest, pytest-qt, `logging`.

**Closes:** review 3.1, review 3.2, review 3.3, review 3.9, review 4.7, five items of review 3.11, and the two working-directory paths the review noted in passing.

**Depends on:** Plan 04 (the presenter close order) and Plan 05 (the settings identity is used by `_on_settings_changed`). The interpreter is `uv run python`.

---

## Rules that apply to every task here

1. Read `docs/superpowers/plans/2026-09-08-techdebt-00-index.md` first. The rules there are binding.
2. Run every command from `C:\Users\sfadiga\sandro\opaque`.
3. Task 4 and Task 5 change a public contract. Every example under `examples/` and every stub presenter in `tests/` has to change with them, in the same commit.
4. A stored `settings.json` or workspace file written before Task 4 is keyed on the old identity and will not be read after it. That is accepted: the framework has not been published yet (decision D1 calls publication near-term, not done). Say so in the commit message, and do not write a migration.
5. Every user-visible string is a literal inside `self.tr()`.

---

## File structure

| File | Responsibility |
|---|---|
| Modify: `src/opaque/presenters/console_presenter.py` | Ask for the service by the name it is registered under. Drop the theme connection the shell now owns. |
| Modify: `src/opaque/services/workspace_service.py:88-90` | `cleanup()` cleans up. |
| Modify: `src/opaque/view/application.py` | Shut down in an order a presenter can survive, one identity for the registry, the dead monkey patch removed, and one settings lookup. |
| Modify: `src/opaque/models/model.py`, `src/opaque/models/console_model.py`, `src/opaque/models/app_model.py` | `FEATURE_ID` is declared and read. |
| Modify: `src/opaque/presenters/presenter.py` | `feature_id` comes from the model. The fourth constructor argument goes. |
| Modify: `src/opaque/view/dialogs/keyboard_map.py` | The list also holds the shortcuts that are `QShortcut` objects. |
| Modify: `src/opaque/view/widgets/mdi_window.py:29-40` | The MDI area stops shadowing a Qt signal. |
| Modify: `src/opaque/services/logger_service.py` | The framework's own log records reach the application log file. |
| Modify: `src/opaque/services/single_instance_service.py` | The lock file is not written into the working directory. |
| Create: `tests/test_feature_identity.py` | The one identity, end to end. |
| Create: `tests/test_shutdown_order.py` | A presenter can still save on the way down. |
| Modify: `CLAUDE.md` | Identity, shutdown order and the signal policy. |

---

## Task 1: Ask for the theme service by its real name

**Files:**
- Modify: `src/opaque/presenters/console_presenter.py:99-105`
- Test: `tests/test_console_presenter_theme.py`

`ThemeService` registers itself as `"themes"`. `console_presenter.py:101` asks the locator for `"theme"`, and `ServiceLocator.get_service` answers a name it does not know with `None`, so the branch is skipped in silence. Plan 03 Task 6 gave the shell one repaint walk that reaches every widget with an `apply_theme()` method, and the console widget has one, so the console is already repainted. That makes this presenter's own connection both wrong and unnecessary: it goes.

- [ ] **Step 1: Write the failing test**

Create `tests/test_console_presenter_theme.py`:

```python
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
```

`ThemeService` takes the `QApplication`, because Plan 03 Task 2 captures the palette at construction, so the test uses the `qapp` fixture.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_console_presenter_theme.py -q
```

Expected: `test_the_console_presenter_asks_for_no_unknown_service_name` FAILS and `test_the_console_presenter_leaves_the_theme_signal_to_the_shell` FAILS.

- [ ] **Step 3: Write the implementation**

In `src/opaque/presenters/console_presenter.py`, find the block around line 99 to 105. It reads:

```python
        theme_service = ServiceLocator.get_service("theme")
        if theme_service is not None and hasattr(theme_service, "theme_changed"):
            theme_service.theme_changed.connect(
                lambda _name: console_widget.apply_theme())
```

Delete the whole block, and the line above it that fetches the service if that line exists only for this block. Replace it with this comment:

```python
        # The console widget repaints itself from the theme tokens. The shell
        # calls apply_theme() on every widget that has it after a theme
        # change, so this presenter needs no theme connection of its own.
        # This code used to ask the locator for "theme"; the service is
        # registered as "themes", so the connection was never made.
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_console_presenter_theme.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Prove the console still follows the theme**

```bash
uv run python -m pytest tests/view/test_console_widget.py tests/test_application_shell.py -q
```

Expected: every test passes, including `test_a_theme_change_reaches_a_widget_that_paints_its_own_colours` from Plan 03 Task 6.

- [ ] **Step 6: Look for any other wrong service name**

```bash
uv run python -c "
import re, pathlib
from opaque.services.service import ServiceLocator
known = {'settings', 'workspace', 'themes', 'notification', 'logger', 'single_instance', 'console'}
pattern = re.compile(r'get_service\(\s*[\'\"]([a-z_]+)[\'\"]')
for path in pathlib.Path('src').rglob('*.py'):
    for name in pattern.findall(path.read_text(encoding='utf-8')):
        if name not in known:
            print('unknown name', name, 'in', path)
print('done')
"
```

Expected: only `done`. Any other line printed is the same defect somewhere else; fix it and say which line.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/presenters/console_presenter.py tests/test_console_presenter_theme.py
git commit -m "fix(console): stop asking the locator for a service name nothing registers"
```

---

## Task 2: A cleanup that cleans up

**Files:**
- Modify: `src/opaque/services/workspace_service.py:88-90`
- Test: `tests/test_workspace_service.py`

`WorkspaceService.cleanup()` calls `super().initialize()`, so shutting the service down sets `_initialized = True`. The service reports itself as ready after it has been torn down, and `ServiceLocator.cleanup_services()` leaves the process holding a service that says it is alive.

- [ ] **Step 1: Write the failing test**

Create `tests/test_workspace_service.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the workspace service lifecycle."""

import pytest

from opaque.services.workspace_service import WorkspaceService


@pytest.fixture
def service():
    workspace = WorkspaceService()
    workspace.initialize()
    return workspace


def test_the_service_reports_itself_ready_after_initialize(service):
    assert service.is_initialized is True


def test_the_service_reports_itself_not_ready_after_cleanup(service):
    service.cleanup()
    assert service.is_initialized is False


def test_cleanup_forgets_every_registered_feature(service):
    class _Presenter:
        feature_id = "demo"

    service.register_feature(_Presenter())
    service.cleanup()

    assert service.save_workspace("unused.json") is None
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_workspace_service.py -q
```

Expected: `test_the_service_reports_itself_not_ready_after_cleanup` FAILS with `assert True is False`.

- [ ] **Step 3: Write the implementation**

In `src/opaque/services/workspace_service.py`, replace `cleanup`. Before:

```python
    def cleanup(self) -> None:
        super().initialize()
        self._features.clear()
```

After:

```python
    def cleanup(self) -> None:
        self._features.clear()
        return super().cleanup()
```

The call also moved to the end, so the base class marks the service as not initialized after this class has released what it owns, which is the order every other service uses.

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_workspace_service.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Check every other service for the same mistake**

```bash
grep -rn "def cleanup" -A 6 --include=*.py src/opaque/services | grep -n "super().initialize()"
```

Expected: no output.

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/services/workspace_service.py tests/test_workspace_service.py
git commit -m "fix(workspace): let cleanup clean up instead of initialising"
```

---

## Task 3: Shut down in an order a presenter can survive

**Files:**
- Modify: `src/opaque/view/application.py:407-416` (`closeEvent`)
- Test: `tests/test_shutdown_order.py`

`closeEvent` calls `ServiceLocator.cleanup_services()` first and then `presenter.cleanup()` on every feature. A presenter that saves its state on the way down asks the settings service or the workspace service for help and gets a service that has already released everything. The last thing the user does before closing the application is the thing most likely to be lost.

- [ ] **Step 1: Write the failing test**

Create `tests/test_shutdown_order.py`:

```python
# This Python file uses the following encoding: utf-8
"""The shutdown order must let a presenter finish its work."""

import pytest

from PySide6.QtGui import QCloseEvent

from opaque.services.service import ServiceLocator


def test_a_presenter_is_cleaned_up_before_the_services(app_window):
    order = []

    class _Recorder:
        def cleanup(self):
            order.append("presenter")

    app_window._registered_features["recorder"] = _Recorder()

    settings = ServiceLocator.get_service("settings")
    real_cleanup = settings.cleanup

    def _tracked_cleanup():
        order.append("service")
        real_cleanup()

    settings.cleanup = _tracked_cleanup

    app_window.closeEvent(QCloseEvent())

    assert order.index("presenter") < order.index("service")


def test_a_presenter_can_still_reach_a_service_while_closing(app_window):
    seen = []

    class _Saver:
        def cleanup(self):
            seen.append(ServiceLocator.get_service("settings"))

    app_window._registered_features["saver"] = _Saver()

    app_window.closeEvent(QCloseEvent())

    assert seen and seen[0] is not None


def test_a_presenter_that_raises_does_not_stop_the_shutdown(app_window):
    seen = []

    class _Broken:
        def cleanup(self):
            raise RuntimeError("no")

    class _Good:
        def cleanup(self):
            seen.append(True)

    app_window._registered_features["broken"] = _Broken()
    app_window._registered_features["good"] = _Good()

    app_window.closeEvent(QCloseEvent())

    assert seen == [True]
```

`app_window` is the fixture `tests/test_application_shell.py` already uses. Import it by putting these tests in a file that can see it: add `from tests.test_application_shell import app_window  # noqa: F401` at the top of the new file, or move the fixture into `tests/conftest.py` if that import does not resolve. Say which one you did.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_shutdown_order.py -q
```

Expected: `test_a_presenter_is_cleaned_up_before_the_services` FAILS, because `order` reads `["service", ..., "presenter"]`. `test_a_presenter_can_still_reach_a_service_while_closing` FAILS with `assert seen[0] is not None`, because the locator was emptied first. `test_a_presenter_that_raises_does_not_stop_the_shutdown` FAILS with the `RuntimeError` escaping.

- [ ] **Step 3: Write the implementation**

In `src/opaque/view/application.py`, replace `closeEvent`. Before:

```python
    def closeEvent(self, event: QCloseEvent):
        """Handle application close event to clean up services"""
        # Clean up all services
        ServiceLocator.cleanup_services()

        # Clean up active presenters
        for presenter in self._registered_features.values():
            presenter.cleanup()

        super().closeEvent(event)
```

After:

```python
    def closeEvent(self, event: QCloseEvent):
        """
        Release the features first, then the services.

        The order matters. A presenter saves its state on the way down, and it
        asks the settings service or the workspace service to do it. Cleaning
        the services up first handed every presenter a service that had
        already released everything, so the last thing the user did was the
        most likely thing to be lost.

        One presenter that raises must not stop the others, and must not stop
        the services from being released, so each one is guarded.
        """
        for feature_id, presenter in list(self._registered_features.items()):
            try:
                presenter.cleanup()
            except Exception:  # pylint: disable=broad-except
                logger.exception(
                    "The feature %s failed to clean up", feature_id)

        ServiceLocator.cleanup_services()

        super().closeEvent(event)
```

`logger` is already defined at the top of `application.py`.

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_shutdown_order.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 6: Look at the running application**

```bash
uv run python examples/basic_example/main.py
```

Open two feature windows, then close the application from the window close button. Expected: no traceback in the console. Start it again. Expected: the application starts normally. Record what you saw.

- [ ] **Step 7: Update CLAUDE.md**

In `## Architecture`, add this bullet after the registration recipe bullet:

```markdown
- **Shutdown order**: `BaseApplication.closeEvent` releases every feature presenter first and the services afterwards, each presenter guarded, so a presenter can still use a service while it saves. Do not move the service cleanup earlier.
```

- [ ] **Step 8: Commit**

```bash
git add src/opaque/view/application.py tests/test_shutdown_order.py CLAUDE.md
git commit -m "fix(shell): release the features before the services"
```

---

## Task 4: One declared identity per feature

**Files:**
- Modify: `src/opaque/models/abstract_model.py` (a class attribute and a classmethod)
- Modify: `src/opaque/models/app_model.py`, `src/opaque/models/console_model.py`, `src/opaque/models/notification_settings_model.py`
- Modify: `src/opaque/presenters/notification_presenter.py` (the constant reads the model)
- Modify: `src/opaque/view/application.py:295-320` (`register_feature`)
- Modify: seven example models and three test models, listed in Step 5
- Test: `tests/test_feature_identity.py`

`register_feature` keys the registry on `presenter.model.feature_name()`, and `feature_name()` is a display string that goes through `tr()`. Translating the interface therefore changes the registry key, and two features whose titles happen to match cannot both be registered. Decision D5: one declared `FEATURE_ID` string, stable for the life of the application, is the key for the registry, the settings block and the workspace block. `feature_name()` becomes display-only.

`FEATURE_ID` goes on `AbstractModel` and not on `BaseModel`, because the settings dialog and the notification settings both use models that extend `AbstractModel` directly.

- [ ] **Step 1: Write the failing test**

Create `tests/test_feature_identity.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the one declared identity of a feature."""

import pytest

from opaque.models.abstract_model import AbstractModel
from opaque.models.app_model import ApplicationModel
from opaque.models.console_model import ConsoleModel
from opaque.models.notification_settings_model import NotificationSettingsModel


class _Identified(AbstractModel):
    FEATURE_ID = "identified"

    def feature_name(self) -> str:
        return "Anything At All"


class _Anonymous(AbstractModel):
    def feature_name(self) -> str:
        return "Anonymous"


def test_a_declared_identity_is_returned():
    assert _Identified.feature_id() == "identified"


def test_the_identity_is_readable_from_an_instance():
    assert _Identified().feature_id() == "identified"


def test_a_missing_identity_names_the_class_and_the_attribute():
    with pytest.raises(NotImplementedError) as error:
        _Anonymous.feature_id()

    message = str(error.value)
    assert "_Anonymous" in message
    assert "FEATURE_ID" in message


def test_the_message_shows_the_code_to_write():
    with pytest.raises(NotImplementedError) as error:
        _Anonymous.feature_id()
    assert "FEATURE_ID = " in str(error.value)


def test_the_identity_does_not_change_when_the_name_does():
    class _Renamed(_Identified):
        def feature_name(self) -> str:
            return "A Completely Different Title"

    assert _Renamed.feature_id() == "identified"


@pytest.mark.parametrize("model_class,expected", [
    (ApplicationModel, "application"),
    (ConsoleModel, "console"),
    (NotificationSettingsModel, "notification_settings"),
])
def test_every_framework_model_declares_its_identity(model_class, expected):
    assert model_class.FEATURE_ID == expected
    assert model_class.feature_id() == expected


def test_the_registry_is_keyed_on_the_identity(app_window):
    for key, presenter in app_window._registered_features.items():
        assert key == presenter.model.feature_id()


def test_two_features_with_the_same_identity_are_refused(app_window):
    presenter = next(iter(app_window._registered_features.values()))

    with pytest.raises(ValueError) as error:
        app_window.register_feature(presenter)

    assert presenter.model.feature_id() in str(error.value)
```

Add the `app_window` fixture the same way Task 3 did, and say which way you chose.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_feature_identity.py -q
```

Expected: a collection error or `AttributeError: type object '_Identified' has no attribute 'feature_id'`.

- [ ] **Step 3: Declare the identity on the model base**

In `src/opaque/models/abstract_model.py`, add this class attribute and this classmethod to `AbstractModel`, directly after the `_version = "1.0.0"` line:

```python
    # The one stable identity of this feature. A subclass must declare it.
    # Empty means undeclared, which feature_id() reports.
    FEATURE_ID: str = ""

    @classmethod
    def feature_id(cls) -> str:
        """
        Return the one stable identity of this feature.

        It is the key of the feature registry, of the block in settings.json
        and of the block in a workspace file. It must not change once an
        application has shipped, because a stored file is keyed on it.

        feature_name() is a different thing: a display title, translated, free
        to change. Using the title as a key meant that translating the
        interface moved the key.

        Raises:
            NotImplementedError: When the subclass declares no FEATURE_ID.
        """
        if not cls.FEATURE_ID:
            raise NotImplementedError(
                f"{cls.__name__} must declare FEATURE_ID. Write:\n"
                f"    class {cls.__name__}(BaseModel):\n"
                f"        FEATURE_ID = 'my_feature'\n"
                f"It is the key of the feature registry, of settings.json and "
                f"of the workspace file, so keep it short, keep it in ASCII, "
                f"and never change it once your application has shipped. The "
                f"display title is feature_name(), which is free to change.")
        return cls.FEATURE_ID
```

- [ ] **Step 4: Declare it on the framework models**

`src/opaque/models/app_model.py`, in `ApplicationModel`, replace the `FEATURE_NAME` line with both:

```python
    FEATURE_ID = "application"
    FEATURE_NAME = "Application"
```

`src/opaque/models/notification_settings_model.py`, in `NotificationSettingsModel`, add as the first line of the class body after the docstring:

```python
    FEATURE_ID = "notification_settings"
```

`src/opaque/models/console_model.py`, in `ConsoleModel`, add the attribute and the method. `ConsoleModel` is a `QObject` and not an `AbstractModel`, so it needs its own copy. Add directly after the `output_cleared = Signal()` line:

```python
    # ConsoleModel duck types the model interface instead of extending
    # AbstractModel, so it declares its own identity.
    FEATURE_ID = "console"

    @classmethod
    def feature_id(cls) -> str:
        """Return the one stable identity of the console feature."""
        return cls.FEATURE_ID
```

`src/opaque/presenters/notification_presenter.py`, make the constant read the model instead of repeating the string:

```python
# The settings.json key and the dialog page identity of the notification
# settings. It reads the model, so there is one declaration of the string.
NOTIFICATION_SETTINGS_ID = NotificationSettingsModel.FEATURE_ID
```

- [ ] **Step 5: Declare it on every other model in the repository**

Add one `FEATURE_ID` line as the first statement of each class body. Use these exact values, because they become file keys:

| File | Class | `FEATURE_ID` |
|---|---|---|
| `examples/basic_example/features/calculator/model.py` | the model class | `"calculator"` |
| `examples/basic_example/features/data_viewer/model.py` | the model class | `"data_viewer"` |
| `examples/basic_example/features/logging/model.py` | the model class | `"logging"` |
| `examples/basic_example/features/notification_tester/model.py` | the model class | `"notification_tester"` |
| `examples/basic_example/features/tab_manager/model.py` | the model class | `"tab_manager"` |
| `examples/closeable_tab_example/main.py` | the model class at line 140 | `"closeable_tab"` |
| `examples/my_example/features/todo_list/model.py` | the model class | `"todo_list"` |
| `examples/quickstart/main.py` | `GreetingModel` | `"greeting"` |
| `tests/test_application_shell.py` | the model at line 55 | `"shell_test"` |
| `tests/view/test_settings_dialog.py` | `DemoModel` | `"demo"` |
| `tests/view/test_settings_dialog.py` | `TypedModel` | `"typed"` |
| `tests/view/test_toolbar.py` | the model at line 38 | `"toolbar_test"` |
| `tests/test_presenter_contract.py` | `_FakeModel` | `"contract"` |

`examples/quickstart/main.py` was created by Plan 02 Task 2. `TypedModel` was created by Plan 05 Task 2. If either is missing, that plan has not run yet; report it and stop.

Find them all with:

```bash
grep -rn "def feature_name" --include=*.py src examples tests
```

Every class that command names must declare `FEATURE_ID` when you are done.

- [ ] **Step 6: Key the registry on the identity**

In `src/opaque/view/application.py`, replace the first lines of `register_feature`. Before:

```python
        feature_name = presenter.model.feature_name()
        if feature_name in self._registered_features:
            raise ValueError(f"Feature '{feature_name}' is already registered")

        self._registered_features[feature_name] = presenter
```

After:

```python
        feature_id = presenter.model.feature_id()
        if feature_id in self._registered_features:
            other = self._registered_features[feature_id]
            raise ValueError(
                f"The feature id '{feature_id}' is already registered by "
                f"{type(other.model).__name__}. Two features cannot share "
                f"one FEATURE_ID: it keys the registry, settings.json and "
                f"the workspace file. Give {type(presenter.model).__name__} "
                f"its own FEATURE_ID.")

        self._registered_features[feature_id] = presenter
```

- [ ] **Step 7: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_feature_identity.py -q
```

Expected: `10 passed`.

- [ ] **Step 8: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. Anything that looked a feature up by its title now fails; those call sites are part of this task.

- [ ] **Step 9: Run the two examples**

```bash
uv run python examples/basic_example/main.py
uv run python examples/quickstart/main.py
```

Expected: both start, every toolbar button appears, and no `NotImplementedError` about `FEATURE_ID`. Close both.

- [ ] **Step 10: Commit**

```bash
git add src/opaque/models src/opaque/presenters/notification_presenter.py src/opaque/view/application.py examples tests
git commit -m "feat(features): key the feature registry on a declared FEATURE_ID

A settings or workspace file written before this change is keyed on the
presenter class name and is not read any more. The framework is not
published yet, so no migration is provided."
```

---

## Task 5: The settings key and the workspace key are the same key

**Files:**
- Modify: `src/opaque/presenters/presenter.py:37-60, 84-87, 152-178`
- Modify: `src/opaque/presenters/console_presenter.py` (the `super().__init__` call)
- Modify: `src/opaque/view/application.py:175-188` (`_init_application_settings`), `_on_settings_changed`
- Test: `tests/test_feature_identity.py` (add to it)

`BasePresenter.__init__` takes an optional `feature_id` and falls back to the presenter class name, `save_workspace` and `load_workspace` key on `self.__class__.__name__`, and the settings service is registered with `presenter.feature_id`. Renaming a presenter class therefore loses the saved workspace, and the settings block and the workspace block for one feature can carry two different names. There is one identity now; everything uses it.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_feature_identity.py`:

```python
def test_the_presenter_identity_comes_from_the_model(app_window):
    for presenter in app_window._registered_features.values():
        assert presenter.feature_id == presenter.model.feature_id()


def test_the_presenter_constructor_takes_no_identity_argument():
    import inspect

    from opaque.presenters.presenter import BasePresenter

    parameters = list(
        inspect.signature(BasePresenter.__init__).parameters)
    assert parameters == ["self", "model", "view", "app"]


def test_the_workspace_block_is_keyed_on_the_identity(app_window, tmp_path):
    import json

    path = tmp_path / "bench.wks"
    app_window.workspace_service.save_workspace(str(path))

    saved = json.loads(path.read_text(encoding="utf-8"))
    for key in saved:
        assert key in app_window._registered_features


def test_a_saved_workspace_loads_back_into_the_same_feature(app_window,
                                                            tmp_path):
    path = tmp_path / "bench.wks"
    app_window.workspace_service.save_workspace(str(path))

    assert app_window.workspace_service.load_workspace(str(path)) is not None


def test_the_settings_block_is_keyed_on_the_identity(app_window):
    stored = app_window.settings_service.get_all_settings()
    assert "application" in stored


def test_a_settings_change_is_delivered_by_one_lookup(app_window,
                                                      monkeypatch):
    presenter = app_window._registered_features["application"]
    calls = []
    monkeypatch.setattr(
        presenter, "apply_settings", lambda: calls.append(True))

    app_window.settings_service.settings_changed.emit("application", {})

    assert calls == [True]
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_feature_identity.py -q -k "presenter_identity or constructor_takes_no or workspace_block or settings_block"
```

Expected: `test_the_presenter_constructor_takes_no_identity_argument` FAILS with a list holding a fifth entry. `test_the_workspace_block_is_keyed_on_the_identity` FAILS, because the keys are presenter class names. `test_the_settings_block_is_keyed_on_the_identity` FAILS, because the block is called `ApplicationPresenter`.

- [ ] **Step 3: Take the identity from the model**

In `src/opaque/presenters/presenter.py`, replace the constructor signature and the identity block. Before:

```python
    def __init__(
            self,
            model: BaseModel,
            view: BaseView,
            app: 'BaseApplication',
            feature_id: Optional[str] = None
    ) -> None:
        """
        Initialize the presenter.
        """

        # Auto-generate feature_id if not provided
        if feature_id is None:
            # Use the presenter class name as the feature_id
            self._feature_id = self.__class__.__name__
        else:
            self._feature_id = feature_id

        self._app: 'BaseApplication' = app
```

After:

```python
    def __init__(
            self,
            model: BaseModel,
            view: BaseView,
            app: 'BaseApplication',
    ) -> None:
        """
        Initialize the presenter.

        The identity comes from the model and from nowhere else. It used to be
        an optional argument that fell back to the presenter class name, so
        renaming a class lost the saved settings and the saved workspace.
        """
        self._feature_id: str = model.feature_id()

        self._app: 'BaseApplication' = app
```

Then replace the `feature_id` property docstring:

```python
    @property
    def feature_id(self) -> str:
        """
        The identity of this feature, declared by the model as FEATURE_ID.

        It keys the feature registry, the settings block and the workspace
        block. All three are the same key.
        """
        return self._feature_id
```

Then key the workspace on it. Before:

```python
    def save_workspace(self, workspace_object: dict) -> None:
        """
        Save the current worskpace state.
        Override this to implement state persistence.
        """
        state = self.view.get_geometry_state()
        workspace_object[self.__class__.__name__] = {"window_state": state}
        fields = type(self.model).get_fields()
        for name, field in fields.items():
            if field.is_workspace:
                workspace_object[self.__class__.__name__][name] = getattr(
                    self.model, name)

    def load_workspace(self, workspace_object: dict) -> None:
        """
        Restore a previously workspace saved state.
        Override this to implement state restoration.
        """
        if self.__class__.__name__ in workspace_object:
            if "window_state" in workspace_object[self.__class__.__name__]:
                state = workspace_object[self.__class__.__name__]["window_state"]
                self.view.set_geometry_state(state)
            if workspace_object[self.__class__.__name__]:
                for key, value in workspace_object[self.__class__.__name__].items():
                    if hasattr(self.model, key):
                        setattr(self.model, key, value)
                        self.update(key, value)
```

After:

```python
    def save_workspace(self, workspace_object: dict) -> None:
        """
        Save the current workspace state.

        The block is keyed on feature_id, the same key the settings file uses.
        It used to be keyed on the presenter class name, so renaming a class
        lost every saved workspace.

        Override this to add more state.
        """
        block: dict = {"window_state": self.view.get_geometry_state()}
        for name, field in type(self.model).get_fields().items():
            if field.is_workspace:
                block[name] = getattr(self.model, name)
        workspace_object[self.feature_id] = block

    def load_workspace(self, workspace_object: dict) -> None:
        """
        Restore a previously saved workspace state.

        Override this to restore more state.
        """
        block = workspace_object.get(self.feature_id)
        if not block:
            return

        if "window_state" in block:
            self.view.set_geometry_state(block["window_state"])

        fields = type(self.model).get_fields()
        for key, value in block.items():
            if key == "window_state" or key not in fields:
                continue
            setattr(self.model, key, fields[key].coerce(value))
            self.update(key, value)
```

The reader now skips a key that is not a declared field, instead of writing any key the model happens to have, and it converts the value the way Plan 05 Task 1 taught the field to. `window_state` is skipped because it is the geometry, not a field.

`Optional` may now be unused in `presenter.py`. Check the file and remove it from the `typing` import if nothing else uses it.

- [ ] **Step 4: Fix the two call sites that passed an identity**

In `src/opaque/presenters/console_presenter.py`, find the `super().__init__` call. It passes `"console"` as the fourth positional argument. Remove that argument only:

```python
        super().__init__(model, view, app)
```

Then check `src/opaque/presenters/app_presenter.py` and every presenter under `examples/` the same way:

```bash
grep -rn "super().__init__(" --include=*.py src/opaque/presenters examples
```

Every call that passes four arguments must pass three when you are done.

- [ ] **Step 5: Use the identity in the shell**

In `src/opaque/view/application.py`, `_init_application_settings` already keys on `presenter.feature_id`, which is now `"application"`, so it needs no change. Confirm it reads:

```python
        self._registered_features[presenter.feature_id] = presenter
```

Then simplify `_on_settings_changed`, which Plan 05 Task 10 wrote as a search. Before:

```python
        if feature_id == NOTIFICATION_SETTINGS_ID:
            self.notification_presenter.apply_settings()
            return

        for presenter in self._registered_features.values():
            if presenter.feature_id == feature_id:
                presenter.apply_settings()
                return
```

After:

```python
        if feature_id == NOTIFICATION_SETTINGS_ID:
            self.notification_presenter.apply_settings()
            return

        # One key now: the registry, the settings block and the workspace
        # block all use FEATURE_ID, so this is a lookup and not a search.
        presenter = self._registered_features.get(feature_id)
        if presenter is not None:
            presenter.apply_settings()
```

Also update the docstring of that method: remove the sentence that says a feature has three identity keys and that Plan 06 makes this one lookup.

- [ ] **Step 6: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_feature_identity.py -q
```

Expected: `16 passed`.

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 8: Update the three documents**

`CLAUDE.md`, in `## Architecture`, replace the whole **Three identity keys per feature** bullet:

```markdown
- **One identity per feature**: the model declares `FEATURE_ID`, a short stable ASCII string. It keys the feature registry, the settings block in `settings.json` and the block in a workspace file. `feature_name()` is the display title, is translated, and keys nothing. Never change a shipped `FEATURE_ID`.
```

`docs/QUICK_REFERENCE.md`, in the contract table Plan 02 Task 3 wrote, add the `FEATURE_ID` row and correct any row that mentions the presenter class name as a key.

`README.md`, in the quick start and in the "What the framework demands of you" table, add `FEATURE_ID` to what a model must declare. The quickstart example in `examples/quickstart/main.py` and the README block have to stay byte-identical; `tests/test_quickstart.py` from Plan 02 Task 2 fails if they drift.

- [ ] **Step 9: Look at the running application**

```bash
uv run python examples/basic_example/main.py
```

Open two features, move the windows, save the workspace from the File menu, close the application, start it again and load the workspace. Expected: the windows come back where you left them. Open `settings.json` and the workspace file and check the block names: they must be the `FEATURE_ID` strings from Task 4 Step 5. Record what you saw.

- [ ] **Step 10: Commit**

```bash
git add src/opaque/presenters src/opaque/view/application.py tests CLAUDE.md README.md docs/QUICK_REFERENCE.md examples
git commit -m "refactor(features): use FEATURE_ID for settings and workspace too"
```

---

## Task 6: Remove the monkey patch nothing reads

**Files:**
- Modify: `src/opaque/view/application.py:68-70`
- Test: `tests/test_application_shell.py` (add to it)

`BaseApplication.__init__` writes `app.main_window = self` onto the `QApplication` with the comment "Make this window accessible to views via QApplication" and a `# type: ignore` to keep mypy quiet. Nothing in the framework, the examples or the tests ever reads it. It is an attribute bolted onto a Qt object, which no type checker can follow and no reader can find.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_application_shell.py`:

```python
def test_the_application_object_carries_no_bolted_on_window(app_window):
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance()

    assert not hasattr(application, "main_window")


def test_the_shell_is_reachable_through_the_presenter(app_window):
    presenter = next(iter(app_window._registered_features.values()))
    assert presenter.app is app_window
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_application_shell.py -q -k "bolted_on"
```

Expected: FAIL with `assert not True`.

- [ ] **Step 3: Write the implementation**

In `src/opaque/view/application.py`, delete the assignment. Before:

```python
        app = QApplication.instance()
        if app:
            app.main_window = self  # type: ignore
            # The translator must be installed before any widget is built.
```

After:

```python
        app = QApplication.instance()
        if app:
            # The translator must be installed before any widget is built.
```

Every object that needs the shell already holds it: a model takes it as `app`, a view takes it, and a presenter exposes it as `presenter.app`.

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_application_shell.py -q
```

Expected: every test passes.

- [ ] **Step 5: Prove nothing read it**

```bash
grep -rn "\.main_window" --include=*.py src examples tests | grep -v "_main_window" | grep -v "main_window = "
```

Expected: no output. A line that reads `something.main_window` means a caller did use it; report the line and stop instead of deleting its ground.

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/application.py tests/test_application_shell.py
git commit -m "refactor(shell): drop the unread main_window attribute on QApplication"
```

---

## Task 7: The keyboard map shows every shortcut

**Files:**
- Modify: `src/opaque/view/dialogs/keyboard_map.py:34-73`
- Modify: `src/opaque/view/widgets/console_widget.py:88-105`
- Test: `tests/view/test_keyboard_map.py` (add to it)

`collect_shortcuts` reads `window.actions()` and the actions of every child widget. A shortcut created as a `QShortcut` object is not an action, so it never appears. The console widget creates two of them, Find Next and Find Previous, and the dialog that claims to list every shortcut in the application does not list them. A `QShortcut` carries no label, so the widget that owns it says what it is called through `setWhatsThis`.

- [ ] **Step 1: Write the failing test**

Add to `tests/view/test_keyboard_map.py`:

```python
def test_a_qshortcut_appears_in_the_list(qtbot):
    from PySide6.QtGui import QKeySequence, QShortcut
    from PySide6.QtWidgets import QWidget

    from opaque.view.dialogs.keyboard_map import collect_shortcuts

    window = QWidget()
    qtbot.addWidget(window)
    shortcut = QShortcut(QKeySequence("Ctrl+Shift+K"), window)
    shortcut.setWhatsThis("Kick the tyres")

    entries = collect_shortcuts(window)

    assert ("Kick the tyres", "Ctrl+Shift+K") in entries


def test_a_qshortcut_without_a_label_is_left_out(qtbot):
    from PySide6.QtGui import QKeySequence, QShortcut
    from PySide6.QtWidgets import QWidget

    from opaque.view.dialogs.keyboard_map import collect_shortcuts

    window = QWidget()
    qtbot.addWidget(window)
    QShortcut(QKeySequence("Ctrl+Shift+L"), window)

    keys = [key for _label, key in collect_shortcuts(window)]

    assert "Ctrl+Shift+L" not in keys


def test_the_same_key_is_not_listed_twice(qtbot):
    from PySide6.QtGui import QKeySequence, QShortcut
    from PySide6.QtWidgets import QWidget

    from opaque.view.dialogs.keyboard_map import collect_shortcuts

    window = QWidget()
    qtbot.addWidget(window)
    for _ in range(2):
        shortcut = QShortcut(QKeySequence("Ctrl+Shift+M"), window)
        shortcut.setWhatsThis("Twice")

    entries = collect_shortcuts(window)

    assert entries.count(("Twice", "Ctrl+Shift+M")) == 1


def test_the_console_search_shortcuts_are_labelled(qtbot):
    from opaque.view.widgets.console_widget import ConsoleWidget

    widget = ConsoleWidget()
    qtbot.addWidget(widget)

    labels = [widget.next_shortcut.whatsThis(),
              widget.prev_shortcut.whatsThis()]

    assert all(labels)


def test_the_console_search_shortcuts_appear_in_the_list(qtbot):
    from opaque.view.dialogs.keyboard_map import collect_shortcuts
    from opaque.view.widgets.console_widget import ConsoleWidget

    widget = ConsoleWidget()
    qtbot.addWidget(widget)

    labels = [label for label, _key in collect_shortcuts(widget)]

    assert widget.next_shortcut.whatsThis() in labels
```

`ConsoleWidget()` may need arguments. Check its constructor and pass what `tests/view/test_console_widget.py` already passes.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/view/test_keyboard_map.py -q -k "qshortcut or console_search"
```

Expected: `test_a_qshortcut_appears_in_the_list` FAILS, and both `console_search` tests FAIL.

- [ ] **Step 3: Read the QShortcut objects too**

In `src/opaque/view/dialogs/keyboard_map.py`, add `QShortcut` to the imports from `PySide6.QtGui`, then replace `collect_shortcuts`:

```python
def collect_shortcuts(window: QWidget) -> List[Tuple[str, str]]:
    """
    Return every shortcut label and key on a window, sorted by label.

    Two kinds of shortcut exist in a Qt application. A QAction carries its own
    label, and a QShortcut carries none, so the widget that owns a QShortcut
    says what it is called with setWhatsThis. A QShortcut with no whatsThis is
    left out, because a key with no label tells the user nothing.

    Args:
        window: The widget whose shortcuts are read. Every child widget is
            read too, so a menu bar action and a console search key are both
            found.

    Returns:
        A list of label and key pairs. A shortcut with no key or no label is
        left out, and the menu ampersand is removed from the label.
    """
    entries: List[Tuple[str, str]] = []
    seen: set = set()

    for action in window.actions():
        _add_action(action, entries, seen)

    for child in window.findChildren(QWidget):
        for action in child.actions():
            _add_action(action, entries, seen)

    for shortcut in window.findChildren(QShortcut):
        _add_shortcut(shortcut, entries, seen)

    entries.sort(key=lambda pair: pair[0])
    return entries


def _add_shortcut(shortcut, entries: List[Tuple[str, str]], seen: set) -> None:
    """Add one QShortcut to the list, if it has a key and a label."""
    key = shortcut.key().toString()
    if not key:
        return

    label = shortcut.whatsThis().replace("&", "").strip()
    if not label:
        return

    if (label, key) in seen:
        return

    seen.add((label, key))
    entries.append((label, key))
```

`findChildren(QShortcut)` finds a `QShortcut` on the window itself as well as on any child, because a `QShortcut` is a `QObject` whose parent is the widget it belongs to.

- [ ] **Step 4: Label the console shortcuts**

In `src/opaque/view/widgets/console_widget.py`, give both shortcuts a label. Before:

```python
        self.next_shortcut = QShortcut(
            QKeySequence.StandardKey.FindNext, self)
        self.next_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.next_shortcut.activated.connect(self._search_next)

        self.prev_shortcut = QShortcut(
            QKeySequence.StandardKey.FindPrevious, self)
        self.prev_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.prev_shortcut.activated.connect(self._search_previous)
```

After:

```python
        self.next_shortcut = QShortcut(
            QKeySequence.StandardKey.FindNext, self)
        self.next_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut)
        # A QShortcut carries no label, and the keyboard map dialog needs one.
        self.next_shortcut.setWhatsThis(self.tr("Console: find next"))
        self.next_shortcut.activated.connect(self._search_next)

        self.prev_shortcut = QShortcut(
            QKeySequence.StandardKey.FindPrevious, self)
        self.prev_shortcut.setContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.prev_shortcut.setWhatsThis(self.tr("Console: find previous"))
        self.prev_shortcut.activated.connect(self._search_previous)
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
uv run python -m pytest tests/view/test_keyboard_map.py tests/view/test_console_widget.py tests/test_localisation.py -q
```

Expected: every test passes. `tests/test_localisation.py` checks that the two new strings are literals inside `tr()`.

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/dialogs/keyboard_map.py src/opaque/view/widgets/console_widget.py tests/view/test_keyboard_map.py
git commit -m "fix(shortcuts): list the QShortcut objects in the keyboard map"
```

---

## Task 8: Stop shadowing a Qt signal

**Files:**
- Modify: `src/opaque/view/widgets/mdi_window.py:29-32`
- Test: `tests/view/test_mdi_area.py`

`OpaqueMdiArea` declares `subWindowActivated = Signal(QMdiSubWindow)`. `QMdiArea` already has a signal with that exact name, and the redeclaration replaces it, so the signal Qt emits when the active sub-window changes is gone. Nothing in the repository connects to it, which is why nobody noticed: the class docstring promises a signal that never fires.

- [ ] **Step 1: Write the failing test**

Create `tests/view/test_mdi_area.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the MDI area wrapper."""

from PySide6.QtWidgets import QMdiArea, QWidget

from opaque.view.widgets.mdi_window import OpaqueMdiArea


def test_the_area_declares_no_signal_of_its_own(qtbot):
    # A subclass that redeclares a Qt signal replaces it, and the version Qt
    # emits is then lost.
    assert "subWindowActivated" not in vars(OpaqueMdiArea)


def test_the_qt_signal_still_fires_when_a_window_is_activated(qtbot):
    area = OpaqueMdiArea()
    qtbot.addWidget(area)
    area.show()

    with qtbot.waitSignal(area.subWindowActivated, timeout=1000):
        window = area.addSubWindow(QWidget())
        window.show()
        area.setActiveSubWindow(window)


def test_the_tabbed_view_can_be_switched_on_and_off(qtbot):
    area = OpaqueMdiArea()
    qtbot.addWidget(area)

    area.set_tabbed(True)
    assert area.is_tabbed() is True
    assert area.viewMode() == QMdiArea.ViewMode.TabbedView

    area.set_tabbed(False)
    assert area.is_tabbed() is False
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/view/test_mdi_area.py -q
```

Expected: `test_the_area_declares_no_signal_of_its_own` FAILS. `test_the_qt_signal_still_fires_when_a_window_is_activated` FAILS with a timeout, because the redeclared signal is never emitted by Qt.

- [ ] **Step 3: Write the implementation**

In `src/opaque/view/widgets/mdi_window.py`, delete the redeclaration and correct the docstring. Before:

```python
class OpaqueMdiArea(QMdiArea):
    """A MDI area that emits a signal when the active subwindow changes."""

    subWindowActivated = Signal(QMdiSubWindow)

    def is_tabbed(self) -> bool:
```

After:

```python
class OpaqueMdiArea(QMdiArea):
    """
    A MDI area that can show its windows as tabs.

    QMdiArea already has a subWindowActivated signal. This class used to
    redeclare it, which replaced the Qt signal with one that nothing ever
    emitted, so a listener was told nothing. Connect to the inherited signal.
    """

    def is_tabbed(self) -> bool:
```

`Signal` and `QMdiSubWindow` are both still used further down the file by `OpaqueMdiSubWindow`, so leave the imports alone.

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/view/test_mdi_area.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/widgets/mdi_window.py tests/view/test_mdi_area.py
git commit -m "fix(mdi): stop replacing the Qt subWindowActivated signal"
```

---

## Task 9: The framework's own log records reach the log file

**Files:**
- Modify: `src/opaque/services/logger_service.py:81-96, 157-190`
- Test: `tests/test_logger_reach.py`

`LoggerService._setup_logger` configures the logger named `"opaque_app"` and attaches the file handler and the console handler to it. Every module of the framework logs to `logging.getLogger(__name__)`, which is `"opaque.services.settings_service"` and friends. Those names are not below `"opaque_app"`, so every warning and every exception the framework reports goes to the stdlib root logger, which has no handler, and is lost. The application log file holds only what somebody passed to `LoggerService.log()` by hand.

- [ ] **Step 1: Write the failing test**

Create `tests/test_logger_reach.py`:

```python
# This Python file uses the following encoding: utf-8
"""The framework's own log records must reach the application log file."""

import logging
from pathlib import Path

import pytest

from opaque.services.logger_service import LoggerService


@pytest.fixture
def service(tmp_path):
    logger_service = LoggerService(
        log_directory=str(tmp_path / "logs"), application_name="reach")
    logger_service.initialize()
    yield logger_service
    logger_service.cleanup()


def _log_text(service) -> str:
    path = service.get_log_file_path()
    assert path is not None
    for handler in logging.getLogger(LoggerService.LOGGER_NAME).handlers:
        handler.flush()
    return Path(path).read_text(encoding="utf-8")


def test_a_record_from_a_framework_module_reaches_the_file(service):
    logging.getLogger("opaque.services.settings_service").warning(
        "the settings file is gone")

    assert "the settings file is gone" in _log_text(service)


def test_a_record_from_a_deep_module_reaches_the_file(service):
    logging.getLogger("opaque.view.widgets.toolbar").error("no icon")

    assert "no icon" in _log_text(service)


def test_the_service_own_log_call_still_reaches_the_file(service):
    service.log("INFO", "started", source="Test")

    assert "started" in _log_text(service)


def test_a_record_from_another_library_does_not_reach_the_file(service):
    logging.getLogger("some_other_library").error("not ours")

    assert "not ours" not in _log_text(service)


def test_the_framework_logger_does_not_also_print_through_the_root(service):
    assert logging.getLogger(LoggerService.LOGGER_NAME).propagate is False
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_logger_reach.py -q
```

Expected: a collection error or `AttributeError: type object 'LoggerService' has no attribute 'LOGGER_NAME'`, and the first two tests FAIL because the records are lost.

- [ ] **Step 3: Write the implementation**

In `src/opaque/services/logger_service.py`, add the class attribute. Put it beside `LEVEL_MAPPING` at the top of the class:

```python
    # The framework logs to logging.getLogger(__name__) in every module, and
    # every one of those names is below "opaque". Configuring that logger is
    # what makes the framework's own records reach the application log file.
    # The handlers used to sit on "opaque_app", which is not a parent of any
    # of them, so every framework warning went to the stdlib root logger and
    # was lost.
    LOGGER_NAME: str = "opaque"

    # The name the service's own log() calls use. It is a child of
    # LOGGER_NAME, so it reaches the same handlers and stays recognisable in
    # the file.
    APPLICATION_LOGGER_NAME: str = "opaque.app"
```

Then replace `_setup_logger`:

```python
    def _setup_logger(self) -> None:
        """Set up the logger with file and console handlers"""
        # Configure the whole opaque logger tree, so every module of the
        # framework writes into the same session file.
        self._logger = logging.getLogger(self.LOGGER_NAME)
        self._logger.setLevel(self._log_level)

        # Clear any existing handlers
        self._logger.handlers.clear()

        # Do not hand the records to the stdlib root logger as well. A host
        # application that configures its own root handler would otherwise
        # print every framework line twice.
        self._logger.propagate = False

        # Set up file logging
        if self._file_logging_enabled:
            self._setup_file_logging()

        # Set up console logging
        if self._console_logging_enabled:
            self._setup_console_logging()
```

Then, in `log`, write through the application child logger. Before:

```python
        # Log the message
        self._logger.log(log_level, f"[{source}] {message}")
```

After:

```python
        # Log through the child logger, so the file says where the record
        # came from and the handlers on LOGGER_NAME still receive it.
        logging.getLogger(self.APPLICATION_LOGGER_NAME).log(
            log_level, "[%s] %s", source, message)
```

Finally, in `cleanup`, put the tree back the way it was found, so a second application in the same process is not left with a silenced logger. Add these two lines at the start of `cleanup`:

```python
        if self._logger is not None:
            self._logger.handlers.clear()
            self._logger.propagate = True
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_logger_reach.py -q
```

Expected: `5 passed`.

- [ ] **Step 5: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. Watch for a test that asserts on captured log output: `caplog` attaches its handler to the root logger, and `propagate = False` keeps framework records away from it while a `LoggerService` is running. If a test fails for that reason, give that test `caplog.set_level(..., logger="opaque")` and say which test you changed.

- [ ] **Step 6: Look at the running application**

```bash
uv run python examples/basic_example/main.py
```

Close the application, then find the newest session folder under the log directory and read the file. Expected: it holds records whose logger name starts with `opaque.`, not only `opaque.app` lines. Record the first such line you saw.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/services/logger_service.py tests/test_logger_reach.py
git commit -m "fix(logging): send every framework record to the session log file"
```

---

## Task 10: The signal policy is written down

**Files:**
- Modify: `src/opaque/view/application.py` (the `_wire_shell_signals` docstring)
- Modify: `CLAUDE.md`
- Test: `tests/test_signal_policy.py`

Review 4.7 found that the shell connects signals through lambdas and never disconnects them, and that a feature never unloads, so nothing leaks in practice. Decision D6 accepts the debt with a written note instead of a disconnect discipline. A note that is only in a review document is not a policy, so it goes where the next reader will be, and a test keeps the assumption it rests on true.

- [ ] **Step 1: Write the failing test**

Create `tests/test_signal_policy.py`:

```python
# This Python file uses the following encoding: utf-8
"""
The signal policy of the shell.

Decision D6: features never unload at run time, so the shell connects its
signals once and never disconnects them. These tests keep the assumption that
makes it safe. If one of them fails, the policy has to change with the code.
"""

import inspect

from opaque.view.application import BaseApplication


def test_the_shell_offers_no_way_to_unregister_a_feature():
    assert not hasattr(BaseApplication, "unregister_feature")


def test_the_wiring_docstring_states_the_policy():
    text = inspect.getdoc(BaseApplication._wire_shell_signals) or ""
    assert "never unload" in text
    assert "disconnect" in text


def test_a_presenter_still_disconnects_from_its_own_view():
    from opaque.presenters.presenter import BasePresenter

    source = inspect.getsource(BasePresenter.cleanup)
    assert "disconnect" in source
```

`WorkspaceService.unregister_feature` exists and stays: it removes a presenter from the workspace collection, which is not the same thing as unloading a feature from the shell. Only `BaseApplication` is asserted here.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_signal_policy.py -q
```

Expected: `test_the_wiring_docstring_states_the_policy` FAILS.

- [ ] **Step 3: Write the policy where the reader is**

In `src/opaque/view/application.py`, replace the docstring of `_wire_shell_signals`. Before:

```python
        """
        Connect the toolbar to the services that change what it must show.

        Every connection below goes through a lambda on purpose. A signal
        connected straight to a bound method keeps the object it saw at
        connect time, which makes the connection impossible to replace in a
        test and impossible to follow when the toolbar is rebuilt.
        """
```

After:

```python
        """
        Connect the toolbar to the services that change what it must show.

        Every connection below goes through a lambda on purpose. A signal
        connected straight to a bound method keeps the object it saw at
        connect time, which makes the connection impossible to replace in a
        test and impossible to follow when the toolbar is rebuilt.

        These connections are made once and are never taken apart. That is a
        decision, not an oversight: features never unload at run time, and
        the shell lives as long as the process, so there is nothing to
        disconnect from and nothing to leak. `tests/test_signal_policy.py`
        keeps that assumption honest. If a way to unload a feature is ever
        added, this method needs a matching teardown, and a lambda that
        captures `self` has to be replaced first.

        A presenter is different: it connects to its own view, and its view
        can go away, so `BasePresenter.cleanup()` does disconnect.
        """
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_signal_policy.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Write it in CLAUDE.md too**

In `## Conventions`, replace the shell signal bullet. Before:

```markdown
- Shell signal wiring goes through lambdas by stated policy (`_wire_shell_signals` docstring); there is no disconnect discipline yet, and features never unload at runtime.
```

After:

```markdown
- Shell signal wiring goes through lambdas by stated policy (`_wire_shell_signals` docstring). There is deliberately no disconnect discipline in the shell: features never unload at run time and the shell lives as long as the process. `tests/test_signal_policy.py` fails if that stops being true. A presenter is different and does disconnect from its own view in `cleanup()`.
```

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/application.py CLAUDE.md tests/test_signal_policy.py
git commit -m "docs(shell): write down the signal connection policy"
```

---

## Task 11: Nothing is written into the working directory

**Files:**
- Modify: `src/opaque/services/single_instance_service.py:38-52`
- Modify: `src/opaque/services/logger_service.py:45-48`
- Test: `tests/test_writable_paths.py`

`SingleInstanceService` writes its lock to `os.path.join(".", f"{app_name}.lock")` and `LoggerService` defaults its log directory to `"logs"`. Both are relative to the working directory, which is wherever the user happened to start the application. A packaged application started from `C:\Program Files` cannot write either one, and a user who starts the same application from two folders gets two locks and no single-instance protection at all.

- [ ] **Step 1: Write the failing test**

Create `tests/test_writable_paths.py`:

```python
# This Python file uses the following encoding: utf-8
"""No service may write into the working directory."""

from pathlib import Path

from opaque.services.logger_service import LoggerService
from opaque.services.single_instance_service import SingleInstanceService


def test_the_lock_file_is_not_in_the_working_directory(qapp):
    service = SingleInstanceService(app_name="paths")
    path = Path(service.lock_file_path)

    assert path.is_absolute()
    assert path.parent != Path.cwd()


def test_the_lock_file_carries_the_application_name(qapp):
    service = SingleInstanceService(app_name="paths")
    assert "paths" in Path(service.lock_file_path).name


def test_two_services_with_one_name_choose_one_lock(qapp):
    first = SingleInstanceService(app_name="paths")
    second = SingleInstanceService(app_name="paths")
    assert first.lock_file_path == second.lock_file_path


def test_the_log_directory_is_not_in_the_working_directory(qapp):
    service = LoggerService(application_name="paths")
    path = Path(service.get_configuration()["log_directory"])

    assert path.is_absolute()
    assert path.parent != Path.cwd()


def test_an_explicit_log_directory_is_still_honoured(tmp_path, qapp):
    service = LoggerService(
        log_directory=str(tmp_path / "here"), application_name="paths")
    assert str(tmp_path / "here") in service.get_configuration()[
        "log_directory"]
```

Both tests take `qapp`, because `QStandardPaths` answers with the application name that the `QCoreApplication` carries.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_writable_paths.py -q
```

Expected: `test_the_lock_file_is_not_in_the_working_directory` FAILS with `assert False` on `is_absolute()`. `test_the_log_directory_is_not_in_the_working_directory` FAILS the same way.

- [ ] **Step 3: Put the lock somewhere writable**

In `src/opaque/services/single_instance_service.py`, add the import:

```python
from PySide6.QtCore import QStandardPaths
```

Then replace the lock path line. Before:

```python
        self.lock_file_path = os.path.join(".", f"{app_name}.lock")
```

After:

```python
        # The lock goes into the per user temporary folder, not into the
        # working directory. A packaged application started from a read only
        # folder cannot write there, and a user who starts the application
        # from two folders used to get two locks and no protection at all.
        temporary = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.TempLocation)
        self.lock_file_path = os.path.join(
            temporary or tempfile.gettempdir(), f"{app_name}.lock")
```

Add `import tempfile` to the import block. `QStandardPaths.writableLocation` answers with an empty string on a system with no such location, and the standard library fallback keeps the service working.

- [ ] **Step 4: Put the logs somewhere writable**

In `src/opaque/services/logger_service.py`, add the import:

```python
from PySide6.QtCore import QStandardPaths
```

Then replace the log directory default. Before:

```python
        self._log_directory = log_directory or "logs"
```

After:

```python
        # "logs" was relative to the working directory, so a packaged
        # application could not write it. The per user application data
        # folder always can, and one place holds every session.
        self._log_directory = log_directory or self._default_log_directory()
```

And add this method directly after `__init__`:

```python
    @staticmethod
    def _default_log_directory() -> str:
        """
        Return the per user folder that receives the log files.

        QStandardPaths answers with a folder Qt guarantees is writable for
        this user and this application. An empty answer, which happens on a
        system with no such location, falls back to a folder beside the
        user's home.
        """
        location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation)
        if not location:
            return str(Path.home() / ".opaque" / "logs")
        return str(Path(location) / "logs")
```

`Path` is already imported in this module.

- [ ] **Step 5: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_writable_paths.py -q
```

Expected: `5 passed`.

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. A test that expected a `logs` folder beside the repository fails here; change it to read `service.get_configuration()["log_directory"]` and say which test you changed.

- [ ] **Step 7: Update .gitignore and CLAUDE.md**

Plan 01 Task 5 added `/logs/` and `application_name.lock` to `.gitignore`. Neither is written any more, so replace both lines with one comment:

```gitignore
# The logs and the single instance lock now live under the per user
# application data and temporary folders. See LoggerService and
# SingleInstanceService.
```

In `CLAUDE.md`, in `## Architecture`, add this bullet after the `ServiceLocator` bullet:

```markdown
- **Writable paths**: nothing is written into the working directory. `LoggerService` writes under `QStandardPaths.AppDataLocation`, `SingleInstanceService` writes its lock under `TempLocation`, and the settings file comes from the application configuration. `tests/test_writable_paths.py` fails if a relative path comes back.
```

- [ ] **Step 8: Look at the running application**

```bash
uv run python examples/basic_example/main.py
```

Close it, then print the two paths:

```bash
uv run python -c "
from PySide6.QtWidgets import QApplication
from opaque.services.logger_service import LoggerService
from opaque.services.single_instance_service import SingleInstanceService
app = QApplication([])
print('logs:', LoggerService(application_name='demo').get_configuration()['log_directory'])
print('lock:', SingleInstanceService(app_name='demo').lock_file_path)
"
```

Expected: two absolute paths, neither of them inside the repository. Record both.

- [ ] **Step 9: Commit**

```bash
git add src/opaque/services/single_instance_service.py src/opaque/services/logger_service.py tests/test_writable_paths.py .gitignore CLAUDE.md
git commit -m "fix(services): write the log and the lock to a writable location"
```

---

## Verification of the whole plan

- [ ] **Check 1: one identity everywhere**

```bash
grep -rn "feature_name()" --include=*.py src/opaque | grep -v "def feature_name"
```

Expected: only lines that use the name for display, which are the toolbar button, the window title and the settings dialog group list. No line where it is used as a dictionary key.

- [ ] **Check 2: the shutdown order**

```bash
uv run python -m pytest tests/test_shutdown_order.py tests/test_feature_identity.py tests/test_workspace_service.py -q
```

Expected: zero failures.

- [ ] **Check 3: nothing writes to the working directory**

```bash
git status --short
```

Expected: no `logs/` folder and no `.lock` file appears after running the example.

- [ ] **Check 4: the whole suite, the type check and the lint**

```bash
uv run python -m pytest tests -q
uv run python -m mypy src/opaque
uv run python -m pylint src/opaque
```

Expected: the suite reports zero failures. Report every mypy or pylint message that names a line this plan wrote. Removing the `# type: ignore` in Task 6 should reduce the mypy count by one.

---

## What this plan does not do

| Left open | Owner |
|---|---|
| A presenter, a model and a view each still hold the whole `BaseApplication`. | Plan 08 Task 1 to Task 4 |
| Services are still reached by string through `ServiceLocator.get_service`. | Plan 07 |
| `show_already_running_message` builds two user-visible strings outside `tr()`. | Plan 10 Task 4 |
| `OpaqueMdiSubWindow.__init__` annotates `fixed_size: Tuple[int, int] = None`, which is not `Optional`. | Plan 10 Task 1 |
| The four notification handlers whose bodies are `pass`. | Plan 10 Task 6 |
| The five remaining `print()` calls. | Plan 10 Task 6 |
