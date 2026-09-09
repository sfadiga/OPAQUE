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
| `BaseModel` | `opaque.models.model` | State plus feature identity | `FEATURE_ID`, `feature_name()`, `feature_icon()`, `feature_description()` |
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
