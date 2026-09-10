# This Python file uses the following encoding: utf-8
"""Tests for the observer and notification contract of AbstractModel."""

import threading

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


def test_the_validator_callable_rejects_a_write():
    from opaque.models.abstract_model import AbstractModel
    from opaque.models.annotations import IntField

    class EvenModel(AbstractModel):
        FEATURE_ID = "even"
        value = IntField(default=0, validator=lambda v: v % 2 == 0)

    model = EvenModel()
    model.value = 4
    assert model.value == 4
    with pytest.raises(ValueError, match="validator"):
        model.value = 3
    assert model.value == 4
