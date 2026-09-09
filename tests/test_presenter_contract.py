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

    FEATURE_ID = "contract"

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
