# FeatureContext and Declarative Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hand a feature only what a feature needs, build the three parts of a feature in one call instead of three, and put the shell in a package whose name matches what it does.

**Architecture:** Every model, every view and every presenter takes the whole `BaseApplication` and keeps it. `BaseApplication` is a `QMainWindow` that also owns the service registry, the feature registry, the toolbar and the MDI area, so a feature that holds it can reach anything, and `ApplicationModel` already reaches through it into a private attribute (`self.app._configuration`). This plan replaces that reference with a `FeatureContext`: the configuration, a typed service lookup, and one method to put a window on screen. Nothing else. With the context in place, assembly becomes declarative: `register(GreetingModel, GreetingView, GreetingPresenter)` builds the three parts in the order the framework requires, so the order can no longer be got wrong. Last, the shell moves from `opaque/view/application.py` to `opaque/shell.py`, because it is not a view.

**Tech Stack:** Python 3.11 (`TypeVar`, `Type`, `Protocol`), PySide6, pytest, pytest-qt, mypy.

**Closes:** review 4.2, review 4.3, review 4.4, and part of review 5.4.

**Depends on:** Plan 07. The typed service lookups are what makes the context worth having. The interpreter is `uv run python`.

---

## Rules that apply to every task here

1. Read `docs/superpowers/plans/2026-09-08-techdebt-00-index.md` first. The rules there are binding.
2. Run every command from `C:\Users\sfadiga\sandro\opaque`.
3. This plan changes the public constructor of `BaseModel`, `BaseView` and `BasePresenter`. Every example, every test double and both documented examples change with them, in the same commit as the class they follow.
4. The framework itself barely uses the application object: only `app_model.py:54-55` reads anything from it. The examples use it more. Convert them; do not add a compatibility shim.
5. `README.md` and `examples/quickstart/main.py` must stay byte-identical, because `tests/test_quickstart.py` from Plan 02 Task 2 compares them.

---

## File structure

| File | Responsibility |
|---|---|
| Create: `src/opaque/features/__init__.py`, `src/opaque/features/context.py` | `FeatureContext`: the configuration, typed services, and one way to show a window. |
| Create: `tests/test_feature_context.py` | The context contract, with no shell at all. |
| Modify: `src/opaque/models/model.py`, `src/opaque/view/view.py`, `src/opaque/presenters/presenter.py` | Take a `FeatureContext` instead of the application. |
| Modify: `src/opaque/models/app_model.py`, `src/opaque/models/console_model.py` | Read the icon from the context, not from a private attribute. |
| Modify: `src/opaque/view/application.py` | Own one context, and register a feature from three classes. |
| Create: `src/opaque/shell.py` | The new home of `BaseApplication`. |
| Modify: `src/opaque/view/application.py` (after the move) | A re-export, so one import path keeps working for one release. |
| Modify: every file under `examples/` | The new constructors and the new registration. |
| Modify: `CLAUDE.md`, `README.md`, `docs/QUICK_REFERENCE.md` | The new recipe. |

---

## Task 1: The context

**Files:**
- Create: `src/opaque/features/__init__.py`
- Create: `src/opaque/features/context.py`
- Test: `tests/test_feature_context.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_feature_context.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for FeatureContext, the only thing a feature may know."""

import pytest

from PySide6.QtGui import QIcon

from opaque.features.context import FeatureContext
from opaque.models.configuration import DefaultApplicationConfiguration
from opaque.services.console_service import ConsoleService
from opaque.services.service import ServiceLocator
from opaque.services.settings_service import SettingsService


@pytest.fixture
def context(tmp_path, qapp):
    ServiceLocator.cleanup_services()
    settings = SettingsService(tmp_path / "settings.json")
    settings.initialize()
    ServiceLocator.register_service(settings)
    yield FeatureContext(configuration=DefaultApplicationConfiguration())
    ServiceLocator.cleanup_services()


def test_the_context_gives_the_configuration(context):
    assert isinstance(
        context.configuration, DefaultApplicationConfiguration)


def test_the_context_gives_a_typed_service(context):
    assert isinstance(context.service(SettingsService), SettingsService)


def test_a_missing_service_raises_through_the_context(context):
    from opaque.services.theme_service import ThemeService

    with pytest.raises(LookupError):
        context.service(ThemeService)


def test_an_optional_service_answers_none(context):
    assert context.optional_service(ConsoleService) is None


def test_the_context_gives_the_application_icon(context):
    assert isinstance(context.application_icon(), QIcon)


def test_the_context_carries_no_main_window_by_default(context):
    assert context.shell is None


def test_showing_a_window_without_a_shell_is_refused(context, qtbot):
    from PySide6.QtWidgets import QWidget

    widget = QWidget()
    qtbot.addWidget(widget)

    with pytest.raises(RuntimeError) as error:
        context.show_window(widget)

    assert "shell" in str(error.value)


def test_the_context_holds_no_reference_to_a_service_instance(context):
    # The context looks a service up on every call, so a service that is
    # replaced at run time is not shadowed by a stale reference.
    first = context.service(SettingsService)
    ServiceLocator.unregister_service(SettingsService.SERVICE_NAME)

    with pytest.raises(LookupError):
        context.service(SettingsService)

    assert first is not None
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_feature_context.py -q
```

Expected: a collection error, `ModuleNotFoundError: No module named 'opaque.features'`.

- [ ] **Step 3: Write the implementation**

Create `src/opaque/features/__init__.py`:

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

The feature layer.

A feature is one model, one view and one presenter, and FeatureContext is
everything the framework lets it know about the application it runs in.
"""

from opaque.features.context import FeatureContext

__all__ = ["FeatureContext"]
```

Create `src/opaque/features/context.py`:

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

What a feature is allowed to know about its application.
"""

from typing import Optional, Type, TypeVar

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget

from opaque.models.configuration import DefaultApplicationConfiguration
from opaque.services.service import BaseService, ServiceLocator

ServiceType = TypeVar("ServiceType", bound=BaseService)


class FeatureContext:
    """
    Everything a feature may know about the application it runs in.

    A model, a view and a presenter used to take the whole BaseApplication,
    which is a QMainWindow that also owns the service registry, the feature
    registry, the toolbar and the MDI area. A feature that holds that can
    reach anything, and ApplicationModel did: it read a private attribute
    through it. The context gives three things and nothing else: the
    configuration, a typed service lookup, and one way to put a window on
    screen.

    A service is looked up on every call, never cached, so nothing here can
    hold a service that has been cleaned up.
    """

    def __init__(
            self,
            configuration: DefaultApplicationConfiguration,
            shell: Optional[QWidget] = None,
    ) -> None:
        """
        Build a context.

        Args:
            configuration: The application configuration. Read only as far as
                a feature is concerned.
            shell: The main window, when there is one. A test builds a
                context without it, and show_window then refuses instead of
                failing somewhere deeper.
        """
        self._configuration = configuration
        self._shell = shell

    @property
    def configuration(self) -> DefaultApplicationConfiguration:
        """The application configuration."""
        return self._configuration

    @property
    def shell(self) -> Optional[QWidget]:
        """
        The main window, or None in a test that has no shell.

        Prefer show_window() over reaching through this. It is here so a
        feature that genuinely needs a parent widget, for example a modal
        dialog, has one.
        """
        return self._shell

    def service(self, service_class: Type[ServiceType]) -> ServiceType:
        """
        Return the service of this class, or raise.

        Args:
            service_class: The service class to look up.

        Returns:
            The registered service, typed as the class asked for.

        Raises:
            LookupError: When the service is not registered.
        """
        return ServiceLocator.get(service_class)

    def optional_service(
            self, service_class: Type[ServiceType]) -> Optional[ServiceType]:
        """
        Return the service of this class, or None.

        Use this only where absence is normal, for example the console
        service, which exists only when a console feature was registered.
        """
        return ServiceLocator.get_optional(service_class)

    def application_icon(self) -> QIcon:
        """
        The application icon, as a QIcon.

        The configuration answers with whatever the application declared, a
        path or an icon, and a feature should not have to know which.
        """
        icon = self._configuration.get_application_icon()
        return icon if isinstance(icon, QIcon) else QIcon(icon)

    def show_window(self, view: QWidget) -> None:
        """
        Put one feature window on screen.

        Args:
            view: The view to show.

        Raises:
            RuntimeError: When the context has no shell, which means the
                feature was built outside an application.
        """
        if self._shell is None:
            raise RuntimeError(
                "This FeatureContext has no shell, so it cannot show a "
                "window. A context built by BaseApplication has one; a "
                "context built in a test does not. Pass shell=... if the "
                "test needs to show a window.")

        add_sub_window = getattr(self._shell, "add_feature_window", None)
        if add_sub_window is None:
            raise RuntimeError(
                f"{type(self._shell).__name__} cannot host a feature window: "
                f"it has no add_feature_window(view) method.")
        add_sub_window(view)
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_feature_context.py -q
```

Expected: `8 passed`.

If `DefaultApplicationConfiguration()` needs arguments, read `src/opaque/models/configuration.py` and pass what `examples/quickstart/main.py` passes. Say what you passed.

- [ ] **Step 5: Export it**

Add `FeatureContext` to the re-exports in `src/opaque/__init__.py` that Plan 01 Task 3 created: the import line, and the entry in `__all__`, keeping the alphabetical order.

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. `tests/test_public_api.py` from Plan 01 Task 3 checks the `__all__` list against the imports, so it fails if you added one and not the other.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/features src/opaque/__init__.py tests/test_feature_context.py
git commit -m "feat(features): add FeatureContext"
```

---

## Task 2: The shell owns one context

**Files:**
- Modify: `src/opaque/view/application.py`
- Modify: `src/opaque/models/app_model.py:50-56`
- Test: `tests/test_application_shell.py` (add to it)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_application_shell.py`:

```python
def test_the_shell_offers_one_context(app_window):
    from opaque.features.context import FeatureContext

    assert isinstance(app_window.context, FeatureContext)


def test_the_shell_context_carries_the_shell(app_window):
    assert app_window.context.shell is app_window


def test_the_shell_context_carries_the_configuration(app_window):
    assert app_window.context.configuration is app_window._configuration


def test_the_shell_can_host_a_feature_window(app_window, qtbot):
    from PySide6.QtWidgets import QWidget

    before = len(app_window.mdi_area.subWindowList())
    app_window.add_feature_window(QWidget())

    assert len(app_window.mdi_area.subWindowList()) == before + 1


def test_the_application_model_reads_the_icon_from_the_context(app_window):
    from PySide6.QtGui import QIcon

    presenter = app_window._registered_features["application"]
    assert isinstance(presenter.model.feature_icon(), QIcon)


def test_no_model_reaches_a_private_shell_attribute():
    import inspect

    from opaque.models import app_model

    assert "_configuration" not in inspect.getsource(app_model)
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_application_shell.py -q -k "context or host_a_feature or private_shell"
```

Expected: `AttributeError: 'MyApplication' object has no attribute 'context'` on the first three, `AttributeError: ... 'add_feature_window'` on the fourth, and a FAIL on the last.

- [ ] **Step 3: Build the context in the shell**

In `src/opaque/view/application.py`, in `__init__`, directly after `self._configuration = configuration`, add:

```python
        # The one context every feature of this application receives. It is
        # built as early as possible, because the application settings
        # feature below needs it.
        self._context = FeatureContext(
            configuration=configuration, shell=self)
```

Add the import:

```python
from opaque.features.context import FeatureContext
```

Then add the property and the window host method, directly after `register_feature`:

```python
    @property
    def context(self) -> FeatureContext:
        """
        The context every feature of this application receives.

        A feature holds this instead of the whole application. See
        FeatureContext for what it offers and why.
        """
        return self._context

    def add_feature_window(self, view: QWidget) -> None:
        """
        Put one feature window into the MDI area and show it.

        FeatureContext.show_window() calls this. It is the only way a feature
        reaches the MDI area, which is why the MDI area is not on the
        context.
        """
        self.mdi_area.addSubWindow(view)
        view.show()
```

Then use it in `register_feature`. Before:

```python
        self.mdi_area.addSubWindow(presenter.view)
        presenter.view.show()
```

After:

```python
        self.add_feature_window(presenter.view)
```

- [ ] **Step 4: Read the icon from the context**

In `src/opaque/models/app_model.py`, replace `feature_icon`. Before:

```python
    def feature_icon(self) -> QIcon:
        """
        Return the feature icon for the settings dialog.
        """
        if self.app:
            return self.app._configuration.get_application_icon()
        return QIcon.fromTheme("tool")
```

After:

```python
    def feature_icon(self) -> QIcon:
        """
        Return the feature icon for the settings dialog.

        This used to read a private attribute of the application object
        through self.app, which is exactly what FeatureContext exists to
        stop.
        """
        return self.context.application_icon()
```

`self.context` arrives in Task 3. Until then this method fails, so run only the tests named in Step 5 before Task 3 is done, and expect the icon tests to fail until Task 3 lands. If you prefer a green suite at every step, do Task 3 Step 3 first and then come back; say which order you used.

- [ ] **Step 5: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_application_shell.py -q -k "offers_one_context or host_a_feature"
```

Expected: `2 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/application.py src/opaque/models/app_model.py tests/test_application_shell.py
git commit -m "feat(shell): build one FeatureContext and host feature windows"
```

---

## Task 3: A feature takes a context, not the application

**Files:**
- Modify: `src/opaque/models/model.py:22-31`
- Modify: `src/opaque/view/view.py:23-37`
- Modify: `src/opaque/presenters/presenter.py:37-60, 99-102`
- Modify: `src/opaque/models/console_model.py`, `src/opaque/presenters/console_presenter.py`, `src/opaque/presenters/app_presenter.py`, `src/opaque/view/app_view.py`
- Modify: every model, view and presenter under `examples/` and every double under `tests/`
- Test: `tests/test_feature_context.py` (add to it)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_feature_context.py`:

```python
def test_a_model_takes_a_context(context):
    from opaque.models.model import BaseModel

    class _Model(BaseModel):
        FEATURE_ID = "ctx_model"

        def feature_name(self) -> str:
            return "Context Model"

    model = _Model(context)
    assert model.context is context


def test_a_model_no_longer_offers_the_whole_application(context):
    from opaque.models.model import BaseModel

    assert not hasattr(BaseModel, "app")


def test_a_view_takes_a_context(context, qtbot):
    from opaque.view.view import BaseView

    view = BaseView(context)
    qtbot.addWidget(view)
    assert view.context is context


def test_a_view_no_longer_offers_the_whole_application():
    from opaque.view.view import BaseView

    assert not hasattr(BaseView, "app")


def test_a_presenter_takes_a_context(context, qtbot):
    from opaque.models.model import BaseModel
    from opaque.presenters.presenter import BasePresenter
    from opaque.view.view import BaseView

    class _Model(BaseModel):
        FEATURE_ID = "ctx_presenter"

        def feature_name(self) -> str:
            return "Context Presenter"

    class _Presenter(BasePresenter):
        def bind_events(self) -> None:
            pass

        def update(self, field_name, new_value, old_value=None, model=None):
            pass

        def on_view_show(self) -> None:
            pass

    view = BaseView(context)
    qtbot.addWidget(view)
    presenter = _Presenter(_Model(context), view, context)

    assert presenter.context is context


def test_the_presenter_constructor_asks_for_a_context():
    import inspect

    from opaque.presenters.presenter import BasePresenter

    parameters = list(inspect.signature(BasePresenter.__init__).parameters)
    assert parameters == ["self", "model", "view", "context"]
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_feature_context.py -q -k "takes_a_context or no_longer_offers or asks_for_a_context"
```

Expected: every one FAILS. `BaseModel` still has `app`, and the constructor parameter is still called `app`.

- [ ] **Step 3: Change the three base classes**

`src/opaque/models/model.py`, before:

```python
class BaseModel(AbstractModel):

    def __init__(self, app: 'BaseApplication') -> None:
        super().__init__()
        self._app: 'BaseApplication' = app

    @property
    def app(self) -> 'BaseApplication':
        return self._app
```

after:

```python
class BaseModel(AbstractModel):
    """
    The model of one feature.

    It takes a FeatureContext, not the application. A model that held the
    whole application could reach the toolbar, the MDI area and the service
    registry, and one of them did reach a private attribute.
    """

    def __init__(self, context: FeatureContext) -> None:
        super().__init__()
        self._context: FeatureContext = context

    @property
    def context(self) -> FeatureContext:
        """The context this feature was built with."""
        return self._context
```

Replace the `TYPE_CHECKING` import block of that file with a real import, because `FeatureContext` does not import the models package:

```python
from opaque.features.context import FeatureContext
```

`src/opaque/view/view.py`, before:

```python
    def __init__(self, app: 'BaseApplication', parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._app: 'BaseApplication' = app

        #self._content_widget = None

    @property
    def app(self) -> 'BaseApplication':
        return self._app
```

after:

```python
    def __init__(
            self,
            context: FeatureContext,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._context: FeatureContext = context

    @property
    def context(self) -> FeatureContext:
        """The context this feature was built with."""
        return self._context
```

and replace its `TYPE_CHECKING` block the same way. The commented out `#self._content_widget = None` line goes with it: dead code.

`src/opaque/presenters/presenter.py`, replace the constructor head:

```python
    def __init__(
            self,
            model: BaseModel,
            view: BaseView,
            context: FeatureContext,
    ) -> None:
        """
        Initialize the presenter.

        The identity comes from the model. The context is what the feature is
        allowed to know about the application.
        """
        self._feature_id: str = model.feature_id()
        self._context: FeatureContext = context
```

and the property:

```python
    @property
    def context(self) -> FeatureContext:
        """The context this feature was built with."""
        return self._context
```

Delete the `app` property and every `self._app` reference in that file.

- [ ] **Step 4: Convert the framework's own features**

```bash
grep -rn "self.app\|self._app\|\.app\b" --include=*.py src/opaque
```

Every hit outside `theme_service.py` is a feature holding the application; convert it to `self.context`. `theme_service.py` holds a `QApplication`, which is a different thing and stays.

`src/opaque/models/console_model.py` takes `app` in its constructor and exposes it as `app`. Rename both to `context` the same way, and change the one caller in `console_presenter.py`.

`src/opaque/view/app_view.py` and `src/opaque/presenters/app_presenter.py` take the application; change both to the context, and change `_init_application_settings` in `application.py` to pass `self._context` to all three.

- [ ] **Step 5: Convert the examples and the test doubles**

```bash
grep -rln "BaseModel\|BaseView\|BasePresenter" --include=*.py examples tests
```

Every file that command names constructs one of the three with the application. Change each to the context. In an example `main.py` the call becomes:

```python
        model = TodoListModel(self.context)
        view = TodoListView(self.context)
        presenter = TodoListPresenter(model, view, self.context)
        self.register_feature(presenter)
```

Task 4 replaces those four lines with one call, so do not spend time making them pretty here; make them correct.

`README.md` and `examples/quickstart/main.py` change together and must stay byte-identical.

- [ ] **Step 6: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_feature_context.py -q
```

Expected: `14 passed`.

- [ ] **Step 7: Run the whole suite and both examples**

```bash
uv run python -m pytest tests -q
uv run python examples/basic_example/main.py
uv run python examples/quickstart/main.py
```

Expected: zero failures, and both examples start and close with no traceback.

- [ ] **Step 8: Type check**

```bash
uv run python -m mypy src/opaque
```

Expected: no error about `BaseApplication` in the models or the views. `models/model.py` and `view/view.py` no longer import it at all, so the `TYPE_CHECKING` cycle that forced the string annotations is gone.

- [ ] **Step 9: Commit**

```bash
git add src examples tests README.md
git commit -m "refactor(features): give a feature a context instead of the application"
```

---

## Task 4: One call builds one feature

**Files:**
- Modify: `src/opaque/view/application.py` (a new `register` method)
- Modify: every `main.py` under `examples/`
- Test: `tests/test_feature_registration.py`

The registration recipe is four statements in a fixed order: model, then view, then presenter, then `register_feature`. Getting the order wrong raises a bare `AttributeError`, and `CLAUDE.md` has to warn about it. A method that takes the three classes cannot be called in the wrong order.

- [ ] **Step 1: Write the failing test**

Create `tests/test_feature_registration.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for declarative feature registration."""

import pytest

from opaque.models.model import BaseModel
from opaque.presenters.presenter import BasePresenter
from opaque.view.view import BaseView


class DemoModel(BaseModel):
    FEATURE_ID = "registration_demo"

    def feature_name(self) -> str:
        return "Registration Demo"


class DemoView(BaseView):
    pass


class DemoPresenter(BasePresenter):
    def bind_events(self) -> None:
        pass

    def update(self, field_name, new_value, old_value=None, model=None):
        pass

    def on_view_show(self) -> None:
        pass


def test_one_call_builds_and_registers_a_feature(app_window):
    presenter = app_window.register(DemoModel, DemoView, DemoPresenter)

    assert isinstance(presenter, DemoPresenter)
    assert app_window._registered_features["registration_demo"] is presenter


def test_the_three_parts_get_the_shell_context(app_window):
    presenter = app_window.register(DemoModel, DemoView, DemoPresenter)

    assert presenter.context is app_window.context
    assert presenter.model.context is app_window.context
    assert presenter.view.context is app_window.context


def test_the_window_is_on_screen_after_registration(app_window):
    presenter = app_window.register(DemoModel, DemoView, DemoPresenter)

    assert presenter.view in [
        window for window in app_window.mdi_area.subWindowList()]


def test_the_toolbar_gained_a_button(app_window):
    before = len(app_window.toolbar._feature_buttons)

    app_window.register(DemoModel, DemoView, DemoPresenter)

    assert len(app_window.toolbar._feature_buttons) == before + 1


def test_registering_the_same_feature_twice_is_refused(app_window):
    app_window.register(DemoModel, DemoView, DemoPresenter)

    with pytest.raises(ValueError) as error:
        app_window.register(DemoModel, DemoView, DemoPresenter)

    assert "registration_demo" in str(error.value)


def test_the_manual_recipe_still_works(app_window):
    class OtherModel(DemoModel):
        FEATURE_ID = "registration_manual"

    model = OtherModel(app_window.context)
    view = DemoView(app_window.context)
    presenter = DemoPresenter(model, view, app_window.context)
    app_window.register_feature(presenter)

    assert app_window._registered_features["registration_manual"] is presenter
```

`app_window.toolbar._feature_buttons` is the list the toolbar already keeps; `update_theme` iterates it. If the attribute has another name, read `src/opaque/view/widgets/toolbar.py` and use the real one.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_feature_registration.py -q
```

Expected: five FAIL with `AttributeError: ... has no attribute 'register'`. `test_the_manual_recipe_still_works` passes already.

- [ ] **Step 3: Write the implementation**

In `src/opaque/view/application.py`, add this method directly before `register_feature`:

```python
    def register(
            self,
            model_class: Type[BaseModel],
            view_class: Type[BaseView],
            presenter_class: Type[BasePresenter],
    ) -> BasePresenter:
        """
        Build one feature from its three classes and register it.

        This is the recipe. The three parts have to be built in this order,
        because a presenter takes a model and a view that already exist, and
        BasePresenter.__init__ reads both. Doing it by hand in the wrong
        order raised a bare AttributeError, so the framework does it.

        Args:
            model_class: The model class of the feature.
            view_class: The view class of the feature.
            presenter_class: The presenter class of the feature.

        Returns:
            The presenter that was built and registered. Keep it if the
            application needs to reach the feature later; it is also in the
            feature registry under the model's FEATURE_ID.

        Raises:
            ValueError: When the FEATURE_ID is already registered.
        """
        model = model_class(self._context)
        view = view_class(self._context)
        presenter = presenter_class(model, view, self._context)
        self.register_feature(presenter)
        return presenter
```

Add `Type` to the typing import at the top of the file, and import the three base classes if they are not already imported:

```python
from typing import Dict, Optional, Type

from opaque.models.model import BaseModel
from opaque.presenters.presenter import BasePresenter
from opaque.view.view import BaseView
```

`BasePresenter` is already imported. Adding `BaseModel` and `BaseView` closes no cycle now, because neither imports the application any more after Task 3.

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_feature_registration.py -q
```

Expected: `6 passed`.

- [ ] **Step 5: Use it in every example**

In each `main.py` under `examples/`, replace the four statement recipe with one call. For `examples/my_example/main.py` the change reads, before:

```python
        todo_model = TodoListModel(self.context)
        todo_view = TodoListView(self.context)
        todo_presenter = TodoListPresenter(todo_model, todo_view, self.context)
        self.register_feature(todo_presenter)
```

after:

```python
        self.register(TodoListModel, TodoListView, TodoListPresenter)
```

Do the same in `examples/basic_example/main.py`, `examples/quickstart/main.py`, `examples/closeable_tab_example/main.py` and `examples/notification_example/main.py`. A feature whose presenter needs an extra argument keeps the manual recipe; say which ones you left manual and why.

`examples/quickstart/main.py` and the `README.md` block must stay byte-identical.

- [ ] **Step 6: Run the whole suite and the examples**

```bash
uv run python -m pytest tests -q
uv run python examples/basic_example/main.py
uv run python examples/quickstart/main.py
```

Expected: zero failures, and both examples start with every toolbar button and close with no traceback.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/view/application.py examples tests/test_feature_registration.py README.md
git commit -m "feat(shell): build a feature from its three classes in one call"
```

---

## Task 5: Assembly errors that teach

**Files:**
- Modify: `src/opaque/view/application.py` (`register`, `register_feature`)
- Test: `tests/test_feature_registration.py` (add to it)

Review 5.4 asks that a wrong call teach the caller. `register` can name exactly what went wrong, because it knows which of the three parts it was building.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_feature_registration.py`:

```python
def test_a_model_with_the_wrong_constructor_is_explained(app_window):
    class WrongModel(BaseModel):
        FEATURE_ID = "wrong_model"

        def __init__(self) -> None:  # takes no context
            pass

        def feature_name(self) -> str:
            return "Wrong"

    with pytest.raises(TypeError) as error:
        app_window.register(WrongModel, DemoView, DemoPresenter)

    message = str(error.value)
    assert "WrongModel" in message
    assert "FeatureContext" in message
    assert "model" in message


def test_a_view_with_the_wrong_constructor_is_explained(app_window):
    class WrongView(BaseView):
        def __init__(self) -> None:
            pass

    with pytest.raises(TypeError) as error:
        app_window.register(DemoModel, WrongView, DemoPresenter)

    message = str(error.value)
    assert "WrongView" in message
    assert "FeatureContext" in message


def test_a_presenter_with_the_wrong_constructor_is_explained(app_window):
    class WrongPresenter(DemoPresenter):
        def __init__(self, model) -> None:
            pass

    with pytest.raises(TypeError) as error:
        app_window.register(DemoModel, DemoView, WrongPresenter)

    message = str(error.value)
    assert "WrongPresenter" in message
    assert "model, view, context" in message


def test_a_presenter_that_is_not_a_presenter_is_refused(app_window):
    with pytest.raises(TypeError) as error:
        app_window.register_feature(object())

    assert "BasePresenter" in str(error.value)
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_feature_registration.py -q -k "explained or not_a_presenter"
```

Expected: the three `explained` tests FAIL because the raised `TypeError` is the bare Python one, and `test_a_presenter_that_is_not_a_presenter_is_refused` FAILS with `AttributeError` instead of `TypeError`.

- [ ] **Step 3: Write the implementation**

In `src/opaque/view/application.py`, replace the body of `register` with a guarded build. Keep the docstring from Task 4 and add these steps after it:

```python
        model = self._build_part("model", model_class, self._context)
        view = self._build_part("view", view_class, self._context)
        presenter = self._build_presenter(presenter_class, model, view)
        self.register_feature(presenter)
        return presenter

    def _build_part(self, role: str, part_class: type, context: FeatureContext):
        """
        Build a model or a view, and explain a wrong constructor.

        Args:
            role: "model" or "view", used in the message.
            part_class: The class to build.
            context: The context every part receives.
        """
        try:
            return part_class(context)
        except TypeError as error:
            raise TypeError(
                f"{part_class.__name__} cannot be built as the {role} of a "
                f"feature: {error}. A {role} takes one argument, a "
                f"FeatureContext. Write:\n"
                f"    def __init__(self, context: FeatureContext) -> None:\n"
                f"        super().__init__(context)") from error

    def _build_presenter(
            self,
            presenter_class: Type[BasePresenter],
            model: BaseModel,
            view: BaseView,
    ) -> BasePresenter:
        """Build the presenter, and explain a wrong constructor."""
        try:
            return presenter_class(model, view, self._context)
        except TypeError as error:
            raise TypeError(
                f"{presenter_class.__name__} cannot be built as the "
                f"presenter of a feature: {error}. A presenter takes three "
                f"arguments, model, view, context. Write:\n"
                f"    def __init__(self, model, view, context) -> None:\n"
                f"        super().__init__(model, view, context)") from error
```

Then guard `register_feature`. Add this as its first statement, before the identity is read:

```python
        if not isinstance(presenter, BasePresenter):
            raise TypeError(
                f"register_feature takes a BasePresenter, not a "
                f"{type(presenter).__name__}. Build the feature with "
                f"self.register(ModelClass, ViewClass, PresenterClass), or "
                f"pass a presenter that extends BasePresenter.")
```

`tests/test_shutdown_order.py` from Plan 06 Task 3 puts plain objects into `_registered_features` directly, not through `register_feature`, so it is unaffected.

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_feature_registration.py -q
```

Expected: `10 passed`.

- [ ] **Step 5: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 6: Commit**

```bash
git add src/opaque/view/application.py tests/test_feature_registration.py
git commit -m "feat(shell): explain a wrong feature constructor"
```

---

## Task 6: The shell is not a view

**Files:**
- Create: `src/opaque/shell.py`
- Modify: `src/opaque/view/application.py` (becomes a re-export)
- Modify: `src/opaque/__init__.py`
- Test: `tests/test_module_layout.py`

`BaseApplication` lives in `opaque/view/application.py`, and it owns the service registry, the feature registry, the toolbar, the MDI area, the settings dialog and the workspace file. It is the shell of the application, not a view of a feature, and the package name has been telling every reader the opposite. Review 4.4 asks for the name to match. The file moves; the old import path keeps working for one release, because `docs/` and any user code point at it.

- [ ] **Step 1: Write the failing test**

Create `tests/test_module_layout.py`:

```python
# This Python file uses the following encoding: utf-8
"""The package layout must say what each module is."""

import warnings


def test_the_shell_lives_in_its_own_module():
    from opaque.shell import BaseApplication

    assert BaseApplication.__module__ == "opaque.shell"


def test_the_old_import_path_still_works():
    from opaque.view.application import BaseApplication as FromView
    from opaque.shell import BaseApplication as FromShell

    assert FromView is FromShell


def test_the_old_import_path_warns():
    import importlib

    import opaque.view.application

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.reload(opaque.view.application)

    assert any(issubclass(entry.category, DeprecationWarning)
               for entry in caught)


def test_the_public_api_exports_the_shell():
    import opaque

    assert opaque.BaseApplication.__module__ == "opaque.shell"


def test_the_view_package_holds_no_service_import():
    import inspect

    from opaque.view import view

    source = inspect.getsource(view)
    assert "ServiceLocator" not in source
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_module_layout.py -q
```

Expected: `ModuleNotFoundError: No module named 'opaque.shell'`.

- [ ] **Step 3: Move the file**

```bash
git mv src/opaque/view/application.py src/opaque/shell.py
```

Then fix the module docstring of `src/opaque/shell.py`: add this paragraph under the licence block.

```python
"""
...the existing licence block...

The application shell.

BaseApplication is a QMainWindow, but it is not a view of a feature: it owns
the service registry, the feature registry, the toolbar, the MDI area, the
settings dialog and the workspace file. It used to live in opaque/view/, which
told every reader the opposite. A feature's own view is opaque.view.view.
"""
```

No import inside the file needs to change: every one of them is absolute.

- [ ] **Step 4: Leave a re-export behind**

Create `src/opaque/view/application.py` with only this:

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

Deprecated import path for the application shell.

BaseApplication moved to opaque.shell, because it is the shell and not a view.
Import it from there. This module is kept for one release so existing code and
existing documentation keep working.
"""

import warnings

from opaque.shell import BaseApplication

warnings.warn(
    "opaque.view.application is deprecated. Import BaseApplication from "
    "opaque.shell instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["BaseApplication"]
```

- [ ] **Step 5: Point every import in the repository at the new module**

```bash
grep -rn "opaque.view.application" --include=*.py --include=*.md src examples tests docs README.md CLAUDE.md
```

Change every hit to `opaque.shell`, except the two inside `src/opaque/view/application.py` itself and the test that checks the old path still works. That includes `src/opaque/__init__.py`, every `TYPE_CHECKING` block that still names it, every example and the documents.

- [ ] **Step 6: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_module_layout.py -q
```

Expected: `5 passed`.

- [ ] **Step 7: Run the whole suite with warnings as errors**

```bash
uv run python -m pytest tests -q -W error::DeprecationWarning
```

Expected: zero failures. A failure here means something in the repository still imports the old path, which Step 5 should have converted. `tests/test_module_layout.py` uses `catch_warnings`, so it is not affected by the flag.

- [ ] **Step 8: Run the examples**

```bash
uv run python examples/basic_example/main.py
uv run python examples/quickstart/main.py
```

Expected: both start with no `DeprecationWarning` printed, and close with no traceback.

- [ ] **Step 9: Commit**

```bash
git add src examples tests docs README.md CLAUDE.md
git commit -m "refactor(layout): move BaseApplication to opaque.shell"
```

---

## Task 7: Write the new recipe down

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`, `docs/QUICK_REFERENCE.md`, `docs/DEVELOPER_GUIDE.md`
- Test: `tests/test_documentation.py`, `tests/test_quickstart.py`

- [ ] **Step 1: Run the guards to see what is stale**

```bash
uv run python -m pytest tests/test_documentation.py tests/test_quickstart.py -q
```

Expected: failures naming every document that still shows the old constructors. Write the list down; you fix all of them.

- [ ] **Step 2: Update CLAUDE.md**

Replace the **Registration recipe** bullet:

```markdown
- **Registration recipe**: inside the app subclass `__init__`, after `super().__init__(config)`, call `self.register(MyModel, MyView, MyPresenter)`. The shell builds the three parts in the order the framework requires and puts the window on screen. Build them by hand and call `self.register_feature(presenter)` only when a presenter needs an extra argument; a wrong constructor raises a `TypeError` that shows the signature to write.
```

Replace the **One feature = one MVP triple** bullet so it names the context:

```markdown
- **One feature = one MVP triple.** `BaseModel` (`models/model.py`), `BaseView` (`view/view.py`, an MDI sub-window), `BasePresenter` (`presenters/presenter.py`). Each takes a `FeatureContext` (`features/context.py`), which offers the configuration, `context.service(SomeService)` and `context.show_window(view)`, and nothing else. The shell class `BaseApplication` is a `QMainWindow` in `shell.py`; it owns the service registry, the feature registry, the toolbar and the MDI area. The model must declare `FEATURE_ID` and override `feature_name()`.
```

- [ ] **Step 3: Update the three documents**

`README.md`: the quick start block, which stays byte-identical to `examples/quickstart/main.py`, and the "What the framework demands of you" table.

`docs/QUICK_REFERENCE.md`: the contract table, the registration section and the service section, which now reads `context.service(SettingsService)`.

`docs/DEVELOPER_GUIDE.md`: every code block that constructs a model, a view or a presenter.

- [ ] **Step 4: Run the guards to verify they pass**

```bash
uv run python -m pytest tests/test_documentation.py tests/test_quickstart.py -q
```

Expected: zero failures.

- [ ] **Step 5: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md README.md docs examples
git commit -m "docs(features): document the context and the one call registration"
```

---

## Verification of the whole plan

- [ ] **Check 1: no feature holds the application**

```bash
grep -rn "BaseApplication" --include=*.py src/opaque | grep -v "src/opaque/shell.py" | grep -v "src/opaque/view/application.py" | grep -v "src/opaque/__init__.py"
```

Expected: no output. No model, no view and no presenter names the shell class any more.

- [ ] **Check 2: the recipe is one call**

```bash
uv run python -c "
import inspect
from opaque.shell import BaseApplication
print(inspect.signature(BaseApplication.register))
"
```

Expected: `(self, model_class: Type[BaseModel], view_class: Type[BaseView], presenter_class: Type[BasePresenter]) -> BasePresenter`.

- [ ] **Check 3: the whole suite, the type check and the lint**

```bash
uv run python -m pytest tests -q
uv run python -m mypy src/opaque
uv run python -m pylint src/opaque
```

Expected: the suite reports zero failures. Report the mypy error count; it should be lower than after Plan 07, because the string annotations for `BaseApplication` are gone from the models and the views.

---

## What this plan does not do

| Left open | Owner |
|---|---|
| `NotificationPresenter` is still a `QObject` that takes the main window, not a feature with a context. It is a system presenter by design. | Not scheduled. Record it in the review as accepted. |
| The service registry is still a process-wide singleton behind the context, so a test still cleans it up by hand. The context is the seam that would let a test pass fakes; nothing uses that yet. | Not scheduled. |
| `opaque/view/application.py` still exists as a deprecated re-export. Delete it one release after this one. | Not scheduled. Add a note to `docs/known-issues/`. |
| The remaining polish list. | Plan 10 |
