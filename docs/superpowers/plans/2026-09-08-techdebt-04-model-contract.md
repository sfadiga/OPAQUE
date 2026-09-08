# Model and Presenter Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the MVP contract behave the way the documentation claims: one observer list per model instance, one notification per field write, a close hook a subclass cannot break, feature metadata that is optional where it should be, an error that teaches when `bind_events()` runs too early, and a threading rule the code enforces instead of only stating.

**Architecture:** Six defects in this area share two root causes. The first is that state which belongs to a model instance was stored on the class: `Field._observers` lives on the `Field` object, and `Field` objects are class attributes, so every instance of one model class shares one observer list (review 3.4), and one instance cleaning up silences all of them. The fix moves the observer list onto the instance and deletes the observer machinery from `Field`, which becomes pure metadata. The second is that the framework asked the subclass to remember an order: `on_view_close()` was abstract and carried the real cleanup in its own body, so an override that forgot `super()` leaked (review 3.11), and `bind_events()` runs as the last step of `__init__`, which nothing told the subclass. The fix inverts both: the framework owns the order, and where it cannot, the error message says what to do.

**Tech Stack:** Python 3.11, PySide6 (`QIcon`, `QCoreApplication`, `QThread`), pytest, pytest-qt, `threading`.

**Closes:** review 3.4, review 3.5, review 4.5, and four items of review 3.11 (`on_view_close`, `BaseModel.feature_*`, the `bind_events()` timing trap, the spurious WARNING).

**Depends on:** Plan 01. The interpreter is `uv run python` from Plan 01 Task 6 on.

---

## Rules that apply to every task here

1. Read `docs/superpowers/plans/2026-09-08-techdebt-00-index.md` first. The rules there are binding.
2. Run every command from `C:\Users\sfadiga\sandro\opaque`.
3. The interpreter is `uv run python`.
4. `ConsoleModel` (`src/opaque/models/console_model.py`) is a `QObject` and not an `AbstractModel`. It keeps its own observer list. No task here touches it. If a change of yours breaks a console test, you changed something the task did not name.
5. `AbstractModel.notify(property_name, value)` is public and the example models call it eleven times. Do not delete it.
6. Plan 02 wrote the framework contract into `README.md`, `docs/QUICK_REFERENCE.md` and `CLAUDE.md`, and `tests/test_documentation.py` guards it. Task 3 and Task 5 change that contract, so they change the documents in the same commit. Do not leave a document describing the old rule.

---

## File structure

| File | Responsibility |
|---|---|
| Modify: `src/opaque/models/annotations.py:60-80` | `Field` becomes pure metadata. `_observers`, `attach`, `detach` and `notify` are deleted from it. |
| Modify: `src/opaque/models/abstract_model.py:29-60, 143-146, 157-220` | The observer list lives on the instance. One write gives one notification. A UI-thread check guards every write. |
| Modify: `src/opaque/models/model.py:32-49` | `feature_name()` stays required and says what to write. `feature_icon()` and `feature_description()` get real defaults. |
| Modify: `src/opaque/presenters/presenter.py:62-64, 77-78, 143-151, 186-193` | The framework owns the close order and turns an early `bind_events()` failure into a message that teaches. |
| Create: `tests/models/test_abstract_model.py` | The observer, notification and threading contract. No Qt widget needed. |
| Create: `tests/models/test_base_model.py` | The feature metadata contract. |
| Create: `tests/test_presenter_contract.py` | The close order and the `bind_events()` error. |
| Modify: `CLAUDE.md` | The Architecture bullets state the new contract. |
| Modify: `README.md`, `docs/QUICK_REFERENCE.md` | The two traps Plan 02 documented are gone; say what is true now. |

---

## Task 1: One observer list per model instance

**Files:**
- Modify: `src/opaque/models/annotations.py:60-80`
- Modify: `src/opaque/models/abstract_model.py:29-60, 157-220`
- Test: `tests/models/test_abstract_model.py`

`Field._observers` is a list on the `Field` object. A `Field` object is a class attribute, so it is one object shared by every instance of that model class. Two windows of the same feature therefore notify each other's presenters, and `cleanup()` on one window clears the observers of all of them (`abstract_model.py:219-220`). The list belongs to the instance.

- [ ] **Step 1: Write the failing test**

Create `tests/models/test_abstract_model.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the observer and notification contract of AbstractModel."""

import pytest

from opaque.models.abstract_model import AbstractModel
from opaque.models.annotations import IntField, StringField


class _Recorder:
    """An observer that keeps every call it receives."""

    def __init__(self) -> None:
        self.calls: list = []

    def update(self, field_name, new_value, old_value=None, model=None):
        self.calls.append((field_name, new_value, old_value, model))


class _Counter(AbstractModel):
    """A model with two fields and nothing else."""

    count = IntField(default=0)
    label = StringField(default="")


@pytest.fixture
def counter():
    model = _Counter()
    yield model
    model.cleanup()


def test_an_observer_is_told_about_a_field_write(counter):
    recorder = _Recorder()
    counter.attach(recorder)

    counter.count = 5

    assert recorder.calls[0][0] == "count"
    assert recorder.calls[0][1] == 5
    assert recorder.calls[0][2] == 0
    assert recorder.calls[0][3] is counter


def test_two_instances_do_not_share_observers():
    first = _Counter()
    second = _Counter()
    first_recorder = _Recorder()
    second_recorder = _Recorder()
    first.attach(first_recorder)
    second.attach(second_recorder)

    first.count = 7

    assert [call[0] for call in first_recorder.calls] == ["count"]
    assert second_recorder.calls == []

    first.cleanup()
    second.cleanup()


def test_cleaning_one_instance_leaves_another_instance_observed():
    first = _Counter()
    second = _Counter()
    second_recorder = _Recorder()
    second.attach(second_recorder)

    first.cleanup()
    second.count = 3

    assert [call[0] for call in second_recorder.calls] == ["count"]

    second.cleanup()


def test_a_detached_observer_is_not_told(counter):
    recorder = _Recorder()
    counter.attach(recorder)
    counter.detach(recorder)

    counter.count = 9

    assert recorder.calls == []


def test_attaching_the_same_observer_twice_gives_one_notification(counter):
    recorder = _Recorder()
    counter.attach(recorder)
    counter.attach(recorder)

    counter.count = 1

    assert len(recorder.calls) == 1


def test_an_observer_without_update_is_refused(counter):
    with pytest.raises(TypeError) as error:
        counter.attach(object())
    assert "update" in str(error.value)


def test_the_field_object_holds_no_observer_state():
    field = _Counter.get_fields()["count"]
    assert not hasattr(field, "_observers")
    assert not hasattr(field, "attach")
    assert not hasattr(field, "notify")


def test_a_write_before_super_init_still_notifies_nobody_and_does_not_raise():
    class _Early(AbstractModel):
        value = IntField(default=0)

        def __init__(self) -> None:
            # A subclass that writes a field before the base __init__ runs
            # used to crash on a missing observer list. It must not.
            self.value = 4
            super().__init__()

    model = _Early()
    assert model.value == 4
    model.cleanup()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/models/test_abstract_model.py -q
```

Expected: `test_two_instances_do_not_share_observers` FAILS, because `second_recorder.calls` holds one entry. `test_cleaning_one_instance_leaves_another_instance_observed` FAILS with `assert [] == ["count"]`. `test_the_field_object_holds_no_observer_state` FAILS. `test_an_observer_is_told_about_a_field_write` may pass already.

- [ ] **Step 3: Make Field pure metadata**

In `src/opaque/models/annotations.py`, delete line 60 and the three methods on lines 65 to 80. Before:

```python
        self.name: str = ""  # Will be set by BaseModel
        self._observers: List[Any] = []  # All Fields are observable

    def __set_name__(self, owner: Any, name: str):
        self.name = name

    def attach(self, observer: Any) -> None:
        """Attach an observer to this field."""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Any) -> None:
        """Detach an observer from this field."""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, model_instance: Any, old_value: Any, new_value: Any) -> None:
        """Notify all observers about field change."""
        for observer in self._observers:
            if hasattr(observer, 'update'):
                observer.update(self.name, new_value,
                                old_value, model_instance)

    def validate(self, value: Any) -> bool:
```

After:

```python
        self.name: str = ""  # Will be set by ModelMeta

    def __set_name__(self, owner: Any, name: str):
        self.name = name

    def validate(self, value: Any) -> bool:
```

Then replace the class docstring, because the old one states the behaviour that just moved:

```python
class Field:
    """
    Metadata for one model field. Validation, persistence and UI generation
    read it.

    A Field object is a class attribute, so one Field is shared by every
    instance of the model class. It therefore holds no per-instance state and
    no observer list. Observers live on the model instance; see
    AbstractModel.attach.
    """
```

- [ ] **Step 4: Move the observer list onto the instance**

In `src/opaque/models/abstract_model.py`, replace the setter body inside `ModelMeta.__new__`. Before, lines 34 to 57:

```python
                private_name = f'_{attr_name}'

                def getter(self, name=attr_name, default=attr_value.default):
                    return getattr(self, f'_{name}', default)

                def setter(self, value, name=attr_name, field=attr_value):
```

After (`private_name` was never read, so it goes):

```python
                def getter(self, name=attr_name, default=attr_value.default):
                    return getattr(self, f'_{name}', default)

                def setter(self, value, name=attr_name, field=attr_value):
```

And in the same setter, replace the notification lines. Before:

```python
                    old_value = getattr(self, f'_{name}', None)
                    if old_value != value:
                        setattr(self, f'_{name}', value)
                        # All Field attributes are automatically observable
                        field.notify(self, old_value, value)
                        self.mark_dirty()
```

After:

```python
                    old_value = getattr(self, f'_{name}', None)
                    if old_value != value:
                        setattr(self, f'_{name}', value)
                        # The observer list belongs to this instance, not to
                        # the Field object, which every instance shares.
                        self._notify_field_change(name, old_value, value)
                        self.mark_dirty()
```

Then replace the whole observer section of `AbstractModel`, lines 157 to 220. Before it starts at the `# ========== Observer Pattern Methods ==========` comment and runs to the end of the file. After:

```python
    # ========== Observer Pattern Methods ==========

    def _observer_list(self) -> List[Any]:
        """
        Return this instance's observer list, creating it when needed.

        A subclass may write a field inside its own __init__ before it calls
        super().__init__(), and the write notifies. Building the list on
        demand keeps that legal, and keeps the list on the instance, which is
        the whole point: a list on the Field object is shared by every
        instance of the model class.
        """
        observers = self.__dict__.get("_observers")
        if observers is None:
            observers = []
            self._observers = observers
        return observers

    def attach(self, observer: Any) -> None:
        """
        Attach an observer to this model instance.

        This is the method a presenter uses. BasePresenter.__init__ calls it.

        Args:
            observer: An object with an
                update(field_name, new_value, old_value, model) method.

        Raises:
            TypeError: When the observer has no update method. Failing here
                is deliberate: a silent miss would look like a model that
                never changes.
        """
        if not callable(getattr(observer, "update", None)):
            raise TypeError(
                f"{type(observer).__name__} cannot observe "
                f"{type(self).__name__}: it has no callable update("
                f"field_name, new_value, old_value, model) method.")

        observers = self._observer_list()
        if observer not in observers:
            observers.append(observer)

    def detach(self, observer: Any) -> None:
        """
        Detach an observer from this model instance.

        Args:
            observer: The observer to detach. Detaching an observer that was
                never attached does nothing.
        """
        observers = self._observer_list()
        if observer in observers:
            observers.remove(observer)

    def _notify_field_change(
            self, field_name: str, old_value: Any, new_value: Any) -> None:
        """
        Tell every observer of this instance that one field changed.

        Called by the property setter that ModelMeta generates. The list is
        copied first, because an observer is allowed to detach itself while
        it is being told.
        """
        for observer in list(self._observer_list()):
            observer.update(field_name, new_value, old_value, self)

    def notify(self, property_name: str, value: Any) -> None:
        """
        Notify all observers of a change that is not a Field write.

        Use this for derived state that no Field holds, for example
        notify("error", message). A Field write notifies on its own; do not
        call this from a setter.

        Args:
            property_name: Name of the changed property
            value: New value of the property
        """
        for observer in list(self._observer_list()):
            observer.update(property_name, value, None, self)

    def cleanup(self) -> None:
        """
        Release this instance's observers. Override if the model owns more.

        Only this instance is affected. The previous version cleared the
        observer list on every shared Field object, which silenced every
        other instance of the same model class.
        """
        self._observer_list().clear()
```

`attach_to_all_fields` and `detach_from_all_fields` are deleted. Nothing outside `abstract_model.py` called them; Step 6 proves it.

- [ ] **Step 5: Run the test to verify it passes**

```bash
uv run python -m pytest tests/models/test_abstract_model.py -q
```

Expected: `8 passed`.

- [ ] **Step 6: Prove nothing called the deleted methods**

```bash
grep -rn "attach_to_all_fields\|detach_from_all_fields\|field.notify\|_observers" --include=*.py src examples tests | grep -v "src/opaque/models/console_model.py" | grep -v "src/opaque/models/abstract_model.py"
```

Expected: no output. `console_model.py` keeps its own `_observers` and is out of scope.

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 8: Commit**

```bash
git add src/opaque/models/annotations.py src/opaque/models/abstract_model.py tests/models/test_abstract_model.py
git commit -m "fix(models): keep the observer list on the model instance"
```

---

## Task 2: One field write gives one notification

**Files:**
- Modify: `src/opaque/models/abstract_model.py:143-146` (`mark_dirty`)
- Test: `tests/models/test_abstract_model.py` (add to it)

Every field write calls the presenter twice: once with the field name, then once with the literal `"dirty"`, because `mark_dirty()` notifies. The review checked every `update()` implementation in the repository: `"dirty"` has one producer and no consumer at all. A presenter that switches on `field_name` runs its default branch twice per write for nothing.

- [ ] **Step 1: Write the failing test**

Add to `tests/models/test_abstract_model.py`:

```python
def test_one_field_write_gives_exactly_one_notification(counter):
    recorder = _Recorder()
    counter.attach(recorder)

    counter.count = 2

    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "count"


def test_no_notification_carries_the_literal_dirty(counter):
    recorder = _Recorder()
    counter.attach(recorder)

    counter.count = 2
    counter.label = "hello"

    assert [call[0] for call in recorder.calls] == ["count", "label"]


def test_a_field_write_still_marks_the_model_dirty(counter):
    assert counter.is_dirty is False
    counter.count = 2
    assert counter.is_dirty is True


def test_clear_dirty_clears_the_flag(counter):
    counter.count = 2
    counter.clear_dirty()
    assert counter.is_dirty is False


def test_writing_the_same_value_notifies_nobody(counter):
    recorder = _Recorder()
    counter.attach(recorder)

    counter.count = 0

    assert recorder.calls == []
    assert counter.is_dirty is False


def test_notify_still_reaches_observers_for_state_no_field_holds(counter):
    recorder = _Recorder()
    counter.attach(recorder)

    counter.notify("error", "the file is gone")

    assert recorder.calls == [("error", "the file is gone", None, counter)]
```

The last test protects a real caller. The example models call `self.notify(...)` eleven times for state that no `Field` holds.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/models/test_abstract_model.py -q -k "one_notification or literal_dirty"
```

Expected: `test_one_field_write_gives_exactly_one_notification` FAILS with `assert 2 == 1`. `test_no_notification_carries_the_literal_dirty` FAILS with a list that reads `['count', 'dirty', 'label', 'dirty']`.

- [ ] **Step 3: Write the implementation**

In `src/opaque/models/abstract_model.py`, replace `mark_dirty`. Before:

```python
    def mark_dirty(self) -> None:
        """Mark model as having unsaved changes."""
        self._dirty = True
        self.notify("dirty", True)
```

After:

```python
    def mark_dirty(self) -> None:
        """
        Mark the model as having unsaved changes.

        This sets a flag and nothing more. It used to notify every observer
        with the literal field name "dirty", so one field write called every
        presenter twice. Nothing in the framework or in the examples ever
        read that notification. Ask is_dirty when you need the flag.
        """
        self._dirty = True
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/models/test_abstract_model.py -q
```

Expected: `14 passed`.

- [ ] **Step 5: Prove nothing read the dirty notification**

```bash
grep -rn "\"dirty\"\|'dirty'" --include=*.py src examples tests
```

Expected: no output, apart from lines inside `tests/models/test_abstract_model.py` that name the test itself. If a presenter appears, it read the notification; report the line and stop.

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/models/abstract_model.py tests/models/test_abstract_model.py
git commit -m "fix(models): notify once per field write"
```

---

## Task 3: The framework owns the close order

**Files:**
- Modify: `src/opaque/presenters/presenter.py:62-64, 143-151, 186-193`
- Modify: `CLAUDE.md`, `README.md`, `docs/QUICK_REFERENCE.md`
- Test: `tests/test_presenter_contract.py`

`on_view_close()` is decorated `@abstractmethod`, so every subclass must write it, and it carries the real cleanup in its own body, so every subclass must also call `super().on_view_close()`. Six of the eight overrides in the repository are one line long, and the framework has no way to tell whether one of them forgot. It also logs `logger.warning("presenter cleanup")` on every close, which puts a WARNING in the log for normal work.

The fix separates the hook from the cleanup. The signal reaches a private method the framework owns, which runs the subclass hook and then the cleanup. A subclass can no longer get the order wrong, because it no longer owns the order.

- [ ] **Step 1: Write the failing test**

Create `tests/test_presenter_contract.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the BasePresenter lifecycle contract."""

import logging

import pytest

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon

from opaque.models.annotations import IntField
from opaque.models.model import BaseModel
from opaque.presenters.presenter import BasePresenter


class _FakeView(QObject):
    """The smallest object BasePresenter can drive as a view."""

    window_opened = Signal()
    window_closed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.state: dict = {}

    def setWindowTitle(self, title: str) -> None:
        self.title = title

    def setWindowIcon(self, icon) -> None:
        pass

    def get_geometry_state(self) -> dict:
        return self.state

    def set_geometry_state(self, state: dict) -> None:
        self.state = state


class _FakeModel(BaseModel):
    """A model with one field and the required feature name."""

    value = IntField(default=0)

    def feature_name(self) -> str:
        return "Contract"

    def feature_icon(self) -> QIcon:
        return QIcon()


class _RecordingPresenter(BasePresenter):
    """A presenter that records the order of its own lifecycle calls."""

    def __init__(self, model, view, app=None) -> None:
        self.events: list = []
        super().__init__(model, view, app)

    def bind_events(self) -> None:
        self.events.append("bind_events")

    def update(self, field_name, new_value, old_value=None, model=None):
        self.events.append(("update", field_name))

    def on_view_show(self) -> None:
        self.events.append("on_view_show")

    def on_view_close(self) -> None:
        self.events.append("on_view_close")

    def cleanup(self) -> None:
        self.events.append("cleanup")
        super().cleanup()


class _ForgetfulPresenter(_RecordingPresenter):
    """A presenter whose close hook does not call super(). This is legal."""

    def on_view_close(self) -> None:
        self.events.append("on_view_close")


@pytest.fixture
def presenter(qapp):
    model = _FakeModel(None)
    view = _FakeView()
    return _RecordingPresenter(model, view)


def test_on_view_close_is_not_abstract():
    assert "on_view_close" not in BasePresenter.__abstractmethods__


def test_closing_the_view_runs_the_hook_then_the_cleanup(presenter):
    presenter.view.window_closed.emit()

    assert presenter.events[-2:] == ["on_view_close", "cleanup"]


def test_a_hook_that_does_not_call_super_is_still_cleaned_up(qapp):
    model = _FakeModel(None)
    view = _FakeView()
    forgetful = _ForgetfulPresenter(model, view)

    view.window_closed.emit()
    forgetful.events.clear()
    model.value = 11

    # The presenter was detached, so the write reaches nobody. Before this
    # task, an override without super() left the presenter attached for ever.
    assert forgetful.events == []


def test_closing_the_view_twice_cleans_up_once(presenter):
    presenter.view.window_closed.emit()
    presenter.events.clear()

    presenter.view.window_closed.emit()

    assert presenter.events == []


def test_a_normal_close_logs_no_warning(presenter, caplog):
    with caplog.at_level(logging.WARNING, logger="opaque.presenters.presenter"):
        presenter.view.window_closed.emit()

    from_presenter = [
        record for record in caplog.records
        if record.name == "opaque.presenters.presenter"
    ]
    assert from_presenter == []


def test_showing_the_view_reaches_the_hook(presenter):
    presenter.view.window_opened.emit()

    assert "on_view_show" in presenter.events
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_presenter_contract.py -q
```

Expected: `test_on_view_close_is_not_abstract` FAILS. `test_closing_the_view_runs_the_hook_then_the_cleanup` FAILS, because the recorded order is `["on_view_close"]` with no cleanup after it. `test_a_hook_that_does_not_call_super_is_still_cleaned_up` FAILS with `assert [('update', 'value')] == []`. `test_a_normal_close_logs_no_warning` FAILS with one WARNING record.

- [ ] **Step 3: Write the implementation**

In `src/opaque/presenters/presenter.py`, change the connection. Before, line 63 and line 64:

```python
        self._view.window_opened.connect(self.on_view_show)
        self._view.window_closed.connect(self.on_view_close)
```

After:

```python
        self._view.window_opened.connect(self.on_view_show)
        self._view.window_closed.connect(self._handle_view_closed)
```

Replace `on_view_close`, lines 143 to 151. Before:

```python
    @abstractmethod
    def on_view_close(self) -> None:
        """
        Called when the view is closed.
        Override this to perform cleanup or save state.
        """
        logger.warning("presenter cleanup")
        self.cleanup()
```

After:

```python
    def _handle_view_closed(self) -> None:
        """
        Run the subclass hook, then release the presenter.

        The framework owns this order on purpose. on_view_close() used to be
        abstract and to carry the cleanup in its own body, so a subclass that
        overrode it without calling super() stayed attached to its model and
        stayed connected to its view for the rest of the process. A subclass
        cannot forget an order it does not own.
        """
        if self._closed:
            return
        self._closed = True
        # DEBUG, not WARNING. Closing a window is normal work. The previous
        # version logged a WARNING on every close.
        logger.debug("closing the presenter %s", self.feature_id)
        self.on_view_close()
        self.cleanup()

    def on_view_close(self) -> None:
        """
        Called when the view is closed. Override to save state.

        Do not call cleanup() here and do not call super(). The framework
        calls cleanup() straight after this method returns.
        """
```

Set the guard flag in `__init__`. Add this line directly after `self._view: BaseView = view` (line 60):

```python
        # True after the close sequence has run once. A sub-window can emit
        # window_closed more than once, and cleanup must not run twice.
        self._closed: bool = False
```

Then fix the disconnect in `cleanup`, lines 186 to 193. Before:

```python
        # Disconnect from view events
        try:
            self._view.window_closed.disconnect(self.on_view_close)
            self._view.window_opened.disconnect(self.on_view_show)
        except RuntimeError:
            # Already disconnected
            pass
```

After:

```python
        # Disconnect from view events
        try:
            self._view.window_closed.disconnect(self._handle_view_closed)
            self._view.window_opened.disconnect(self.on_view_show)
        except RuntimeError:
            # Already disconnected
            pass
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_presenter_contract.py -q
```

Expected: `6 passed`.

- [ ] **Step 5: Remove the now pointless super() calls in the framework**

`src/opaque/presenters/app_presenter.py:83-84` reads:

```python
    def on_view_close(self) -> None:
        super().on_view_close()
```

The whole override now does nothing, and the base method is no longer abstract, so delete both lines. Check `src/opaque/presenters/console_presenter.py:300` and `src/opaque/presenters/notification_presenter.py` the same way: if the override body is only `super().on_view_close()` or only `pass`, delete the override. If it does real work, leave the work and delete only the `super().on_view_close()` line.

Do not touch the overrides under `examples/`. Task 4 of Plan 02 already made the examples import correctly, and an override that calls `super()` still works; a separate sweep is Plan 10 Task 5.

- [ ] **Step 6: Update the three documents**

In `CLAUDE.md`, in `## Architecture`, replace the whole `on_view_close()` bullet. Before:

```markdown
- **`on_view_close()` is abstract but carries the real cleanup in its body.** An override must call `super().on_view_close()` or the presenter never cleans up.
```

After:

```markdown
- **`on_view_close()` is a plain hook.** Override it to save state. Do not call `super()` and do not call `cleanup()`; `BasePresenter._handle_view_closed()` owns the order and calls `cleanup()` straight after the hook returns. It runs once even if the view emits `window_closed` twice.
```

In `README.md` and in `docs/QUICK_REFERENCE.md`, find the same claim. Plan 02 Task 2 wrote it into the README section "What the framework demands of you" and into the two documented traps, and Plan 02 Task 3 wrote it into the `QUICK_REFERENCE.md` contract table. Replace every statement that an override must call `super().on_view_close()` with the sentence above. Find them with:

```bash
grep -rn "on_view_close" README.md docs/*.md CLAUDE.md
```

Every line the command prints must state the new rule when you are done.

- [ ] **Step 7: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. `tests/test_documentation.py` from Plan 02 Task 1 also runs; it fails if a document you edited names something that does not exist.

- [ ] **Step 8: Look at the running application**

```bash
uv run python examples/basic_example/main.py
```

Open a feature window, then close it. Expected: no WARNING in the console and no traceback. Open it again and close the application. Record what you saw.

- [ ] **Step 9: Commit**

```bash
git add src/opaque/presenters/presenter.py src/opaque/presenters/app_presenter.py src/opaque/presenters/console_presenter.py src/opaque/presenters/notification_presenter.py tests/test_presenter_contract.py CLAUDE.md README.md docs/QUICK_REFERENCE.md
git commit -m "fix(presenters): let the framework own the view close order"
```

---

## Task 4: Feature metadata that is optional where it should be

**Files:**
- Modify: `src/opaque/models/model.py:32-49`
- Test: `tests/models/test_base_model.py`

All three `feature_*` methods raise `NotImplementedError` at call time, and `BasePresenter.__init__` calls two of them. A feature with no icon therefore cannot start, and the message names the method without saying what to write. A name is identity, so it stays required. An icon and a description are decoration, so they get defaults.

- [ ] **Step 1: Write the failing test**

Create `tests/models/test_base_model.py`:

```python
# This Python file uses the following encoding: utf-8
"""Tests for the feature metadata contract of BaseModel."""

import pytest

from PySide6.QtGui import QIcon

from opaque.models.model import BaseModel


class _NamedModel(BaseModel):
    """A model that declares only what the framework requires."""

    def feature_name(self) -> str:
        return "Bench"


class _NamelessModel(BaseModel):
    """A model that declares nothing."""


def test_a_model_that_declares_only_a_name_is_enough(qapp):
    model = _NamedModel(None)
    assert model.feature_name() == "Bench"


def test_the_icon_defaults_to_a_null_icon(qapp):
    model = _NamedModel(None)
    icon = model.feature_icon()
    assert isinstance(icon, QIcon)
    assert icon.isNull() is True


def test_the_description_defaults_to_an_empty_string(qapp):
    model = _NamedModel(None)
    assert model.feature_description() == ""


def test_a_missing_feature_name_names_the_class_and_the_method(qapp):
    model = _NamelessModel(None)
    with pytest.raises(NotImplementedError) as error:
        model.feature_name()
    message = str(error.value)
    assert "_NamelessModel" in message
    assert "feature_name" in message


def test_the_message_shows_the_code_to_write(qapp):
    model = _NamelessModel(None)
    with pytest.raises(NotImplementedError) as error:
        model.feature_name()
    assert "def feature_name" in str(error.value)


def test_the_app_the_model_was_given_is_readable(qapp):
    marker = object()
    model = _NamedModel(marker)
    assert model.app is marker
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/models/test_base_model.py -q
```

Expected: `test_the_icon_defaults_to_a_null_icon` FAILS with `NotImplementedError`. `test_the_description_defaults_to_an_empty_string` FAILS with `NotImplementedError`. `test_the_message_shows_the_code_to_write` FAILS.

- [ ] **Step 3: Write the implementation**

In `src/opaque/models/model.py`, replace the feature API block, lines 32 to 49. Before:

```python
    # --- FEATURE API (Override in subclasses) ---

    def feature_name(self) -> str:
        """Must be overridden in subclasses"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement feature_name()")

    def feature_icon(self) -> QIcon:
        """Override in subclasses to provide icon (can return str or QIcon)"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement feature_icon()")

    def feature_description(self) -> str:
        """Override in subclasses"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement feature_description()")

    # ----------------------------------------------------
```

After:

```python
    # --- FEATURE API ---
    # A name is identity, so a subclass must declare it. An icon and a
    # description are decoration, so both have a default that works.

    def feature_name(self) -> str:
        """
        The display name of this feature. A subclass must override it.

        The toolbar button, the window title and the View menu all read it.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement feature_name(). Write:\n"
            f"    def feature_name(self) -> str:\n"
            f"        return self.tr(\"My Feature\")\n"
            f"The toolbar button, the window title and the View menu read it."
        )

    def feature_icon(self) -> QIcon:
        """
        The icon of this feature. Optional.

        The default is a null QIcon, which the toolbar and the window title
        both accept: they show text alone. Override it with
        QIcon.fromTheme("name") or a QIcon built from a resource path.
        """
        return QIcon()

    def feature_description(self) -> str:
        """
        One sentence about this feature. Optional.

        Shown as the tool tip of the toolbar button. The default is empty,
        which shows no tool tip.
        """
        return ""

    # ----------------------------------------------------
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/models/test_base_model.py -q
```

Expected: `6 passed`.

- [ ] **Step 5: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 6: Update CLAUDE.md**

In `## Architecture`, in the **One feature = one MVP triple** bullet, add this sentence at the end:

```markdown
The model must override `feature_name()`; `feature_icon()` and `feature_description()` have working defaults (a null icon and an empty string).
```

- [ ] **Step 7: Commit**

```bash
git add src/opaque/models/model.py tests/models/test_base_model.py CLAUDE.md
git commit -m "feat(models): give the feature icon and description real defaults"
```

---

## Task 5: An error that teaches when bind_events runs too early

**Files:**
- Modify: `src/opaque/presenters/presenter.py:77-78`
- Modify: `CLAUDE.md`, `README.md`
- Test: `tests/test_presenter_contract.py` (add to it)

`BasePresenter.__init__` calls `bind_events()` as its last step. Anything the subclass creates after `super().__init__(...)` does not exist yet, so the subclass gets a bare `AttributeError` naming an attribute it can see three lines further down in its own file. The call order stays, because it is the documented recipe and every existing subclass depends on it. The message changes.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_presenter_contract.py`:

```python
class _LatePresenter(BasePresenter):
    """A presenter that binds an attribute it creates after super()."""

    def __init__(self, model, view) -> None:
        super().__init__(model, view, None)
        self.widget = object()

    def bind_events(self) -> None:
        _ = self.widget

    def update(self, field_name, new_value, old_value=None, model=None):
        pass

    def on_view_show(self) -> None:
        pass


def test_an_early_bind_events_explains_the_order(qapp):
    with pytest.raises(AttributeError) as error:
        _LatePresenter(_FakeModel(None), _FakeView())

    message = str(error.value)
    assert "bind_events" in message
    assert "super().__init__" in message
    assert "_LatePresenter" in message


def test_the_original_attribute_name_survives_in_the_message(qapp):
    with pytest.raises(AttributeError) as error:
        _LatePresenter(_FakeModel(None), _FakeView())

    assert "widget" in str(error.value)
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/test_presenter_contract.py -q -k "early_bind or original_attribute"
```

Expected: both FAIL. The raised message is `'_LatePresenter' object has no attribute 'widget'`, which contains neither `bind_events` nor `super().__init__`.

- [ ] **Step 3: Write the implementation**

In `src/opaque/presenters/presenter.py`, replace the last two lines of `__init__`. Before:

```python
        # Bind events
        self.bind_events()
```

After:

```python
        # Bind events. This is the last step of __init__ on purpose: the
        # model and the view are both ready by now. It also means the
        # subclass cannot bind an attribute it creates after its own
        # super().__init__(...) call, so translate that failure into a
        # message that says so.
        try:
            self.bind_events()
        except AttributeError as error:
            raise AttributeError(
                f"{type(self).__name__}.bind_events() used an attribute that "
                f"does not exist yet: {error}. BasePresenter.__init__ calls "
                f"bind_events() as its last step, so anything your __init__ "
                f"creates after super().__init__(...) is not there yet. "
                f"Create it before the super() call, or move the connection "
                f"into on_view_show()."
            ) from error
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/test_presenter_contract.py -q
```

Expected: `8 passed`.

- [ ] **Step 5: Update the two documents**

In `CLAUDE.md`, in `## Architecture`, replace the whole `bind_events` bullet. Before:

```markdown
- **`BasePresenter.__init__` calls `bind_events()` at its end.** Anything a subclass creates after `super().__init__(...)` does not exist yet inside `bind_events()`. Create widgets/attributes before the `super()` call or guard for `None`.
```

After:

```markdown
- **`BasePresenter.__init__` calls `bind_events()` at its end.** Anything a subclass creates after `super().__init__(...)` does not exist yet inside `bind_events()`. Create the attribute before the `super()` call, or connect it in `on_view_show()`. Getting it wrong raises an `AttributeError` whose message states this rule.
```

In `README.md`, find the trap that Plan 02 Task 2 documented under the quick start and add the last sentence to it:

```bash
grep -n "bind_events" README.md docs/*.md
```

Every line the command prints must state that the framework explains the failure.

- [ ] **Step 6: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors.

- [ ] **Step 7: Commit**

```bash
git add src/opaque/presenters/presenter.py tests/test_presenter_contract.py CLAUDE.md README.md
git commit -m "feat(presenters): explain the bind_events call order when it fails"
```

---

## Task 6: The threading rule is enforced, not only stated

**Files:**
- Modify: `src/opaque/models/abstract_model.py` (the import block and the generated setter)
- Modify: `CLAUDE.md`
- Test: `tests/models/test_abstract_model.py` (add to it)

`CLAUDE.md` states the rule: a model field write synchronously calls presenter code that touches widgets, so a field must never be written from a worker thread. Nothing enforces it. Breaking it corrupts the UI or crashes the process at a random later point, far from the line that caused it. The check costs one call per write and names the field.

- [ ] **Step 1: Write the failing test**

Add to `tests/models/test_abstract_model.py`, and add `import threading` to the import block at the top of the file:

```python
def test_a_field_write_on_the_ui_thread_is_allowed(qapp, counter):
    counter.count = 12
    assert counter.count == 12


def test_a_field_write_from_a_worker_thread_is_refused(qapp):
    model = _Counter()
    failures: list = []

    def write() -> None:
        try:
            model.count = 3
        except RuntimeError as error:
            failures.append(error)

    worker = threading.Thread(target=write, name="test-worker")
    worker.start()
    worker.join(timeout=5)

    assert len(failures) == 1
    assert "UI thread" in str(failures[0])
    assert "count" in str(failures[0])
    assert model.count == 0

    model.cleanup()


def test_the_check_is_skipped_when_no_qt_application_exists(monkeypatch):
    from opaque.models import abstract_model

    class _NoApplication:
        @staticmethod
        def instance():
            return None

    monkeypatch.setattr(abstract_model, "QCoreApplication", _NoApplication)

    model = _Counter()
    model.count = 6
    assert model.count == 6
    model.cleanup()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run python -m pytest tests/models/test_abstract_model.py -q -k "worker_thread or no_qt_application"
```

Expected: `test_a_field_write_from_a_worker_thread_is_refused` FAILS with `assert 0 == 1`, because the write succeeds today. `test_the_check_is_skipped_when_no_qt_application_exists` FAILS with `AttributeError: module 'opaque.models.abstract_model' has no attribute 'QCoreApplication'`.

- [ ] **Step 3: Write the implementation**

In `src/opaque/models/abstract_model.py`, add to the import block, after the `from typing import ...` line:

```python
from PySide6.QtCore import QCoreApplication, QThread
```

Then add this function directly after the `T = TypeVar(...)` line and before `class ModelMeta`:

```python
def _assert_ui_thread(model_name: str, field_name: str) -> None:
    """
    Refuse a field write that does not come from the UI thread.

    A field write calls presenter.update() on the same stack, and a presenter
    touches widgets. Qt allows a widget to be touched only from the thread
    that owns the QApplication. A write from a worker thread therefore
    corrupts the UI or crashes the process at a random later point, far from
    the line that caused it. Failing here names the field instead.

    The check does nothing when no QCoreApplication exists, so a model stays
    unit testable with no Qt application at all.

    Raises:
        RuntimeError: When the calling thread is not the UI thread.
    """
    application = QCoreApplication.instance()
    if application is None:
        return
    if QThread.currentThread() is application.thread():
        return

    thread_name = QThread.currentThread().objectName() or "a worker thread"
    raise RuntimeError(
        f"{model_name}.{field_name} was written from {thread_name}, not from "
        f"the UI thread. A field write calls presenter.update() on the same "
        f"stack, and a presenter touches widgets, which is legal only on the "
        f"UI thread. Queue the value and drain it on the UI thread; "
        f"src/opaque/services/console_service.py shows the approved shape."
    )
```

Then add one line as the first statement of the generated setter. Before:

```python
                def setter(self, value, name=attr_name, field=attr_value):
                    # --- Validation ---
```

After:

```python
                def setter(self, value, name=attr_name, field=attr_value):
                    _assert_ui_thread(type(self).__name__, name)

                    # --- Validation ---
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run python -m pytest tests/models/test_abstract_model.py -q
```

Expected: `17 passed`.

If `test_a_field_write_from_a_worker_thread_is_refused` still fails, Qt did not adopt the Python thread as a separate `QThread` on this platform. In that case replace the second guard with an identity comparison that does not depend on adoption: record `threading.get_ident()` of the thread that created the application, and compare against it. Report that you had to do this.

- [ ] **Step 5: Run the whole suite**

```bash
uv run python -m pytest tests -q
```

Expected: zero failures and zero errors. Watch for a failure in `tests/view/test_console_widget.py` or any console test: `console_service.py` drains its queue on the UI thread, so it must stay legal. If a console test fails, the drain is running on the wrong thread and that is a real defect; report it and stop.

- [ ] **Step 6: Update CLAUDE.md**

In `## Architecture`, replace the whole **Threading** bullet. Before:

```markdown
- **Threading**: everything runs on the UI thread. A model field write synchronously calls presenter code that touches widgets — never write model fields from a worker thread. The queue-and-drain pattern in `services/console_service.py` is the approved shape for cross-thread data.
```

After:

```markdown
- **Threading**: everything runs on the UI thread. A model field write synchronously calls presenter code that touches widgets, so a write from a worker thread raises `RuntimeError` naming the model and the field (`_assert_ui_thread` in `models/abstract_model.py`). The check is skipped when no `QCoreApplication` exists, so a model stays unit testable. The queue-and-drain pattern in `services/console_service.py` is the approved shape for cross-thread data.
```

- [ ] **Step 7: Commit**

```bash
git add src/opaque/models/abstract_model.py tests/models/test_abstract_model.py CLAUDE.md
git commit -m "feat(models): refuse a field write from a worker thread"
```

---

## Verification of the whole plan

- [ ] **Check 1: the contract tests all pass**

```bash
uv run python -m pytest tests/models/test_abstract_model.py tests/models/test_base_model.py tests/test_presenter_contract.py -q
```

Expected: `31 passed`.

- [ ] **Check 2: two windows of one feature are independent**

```bash
uv run python examples/basic_example/main.py
```

Open the same feature twice, if the example allows it, and change a value in one window. Expected: the other window does not change. Close one window. Expected: the other window still reacts to its own controls. Record what you saw.

- [ ] **Check 3: the whole suite, the type check and the lint**

```bash
uv run python -m pytest tests -q
uv run python -m mypy src/opaque/models src/opaque/presenters
uv run python -m pylint src/opaque/models src/opaque/presenters
```

Expected: the suite reports zero failures. mypy reports no error in the four files this plan changed. pylint reports no error and no warning in them. `ModelMeta.__new__` may report `too-many-locals` or a `protected-access` note on the generated setter; if it does, add the narrowest `# pylint: disable=` comment on the offending line and say which one you added.

- [ ] **Check 4: no document still states an old rule**

```bash
grep -rn "super().on_view_close\|must call super" README.md docs/*.md CLAUDE.md
```

Expected: no output.

---

## What this plan does not do

| Left open | Owner |
|---|---|
| A feature still has three identity keys: `model.feature_name()`, `presenter.feature_id` and the presenter class name. `FEATURE_ID` on the model replaces all three. | Plan 06 Task 4, Task 5 |
| `BasePresenter.__init__` still takes the optional fourth argument `feature_id`, and `ConsolePresenter` still passes `"console"` positionally. | Plan 06 Task 5 |
| `save_workspace` and `load_workspace` still key on `self.__class__.__name__`. | Plan 06 Task 4 |
| A presenter still receives the whole application object. | Plan 08 Task 1 to Task 4 |
| `ApplicationPresenter` writes `theme_field.choices` onto a class-level `Field` object, so it changes the field for every instance of `ApplicationModel`. `Field` is now documented as shared, which makes the write visibly wrong, but there is only one application model per process, so it is not a live defect. | Plan 08 Task 5 |
| The settings dialog still corrupts typed values on the round trip. | Plan 05 Task 1 to Task 3 |
