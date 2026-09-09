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


@pytest.fixture
def registration_demo_id(request, monkeypatch):
    """
    Give DemoModel a FEATURE_ID unique to the running test.

    app_window is a session scoped fixture (tests/conftest.py), shared by
    every test that asks for it, and a fixed FEATURE_ID on DemoModel would
    collide the moment a second test in this file registered it. Stable
    within one test, because test_registering_the_same_feature_twice_is_refused
    needs both of its own calls to collide with each other.
    """
    unique_id = f"registration_demo_{request.node.name}"
    monkeypatch.setattr(DemoModel, "FEATURE_ID", unique_id)
    return unique_id


def test_one_call_builds_and_registers_a_feature(app_window, registration_demo_id):
    presenter = app_window.register(DemoModel, DemoView, DemoPresenter)

    assert isinstance(presenter, DemoPresenter)
    assert app_window._registered_features[registration_demo_id] is presenter


def test_the_three_parts_get_the_shell_context(app_window, registration_demo_id):
    presenter = app_window.register(DemoModel, DemoView, DemoPresenter)

    assert presenter.context is app_window.context
    assert presenter.model.context is app_window.context
    assert presenter.view.context is app_window.context


def test_the_window_is_on_screen_after_registration(app_window, registration_demo_id):
    presenter = app_window.register(DemoModel, DemoView, DemoPresenter)

    assert presenter.view in [
        window for window in app_window.mdi_area.subWindowList()]


def test_the_toolbar_gained_a_button(app_window, registration_demo_id):
    before = len(app_window.toolbar._feature_buttons)

    app_window.register(DemoModel, DemoView, DemoPresenter)

    assert len(app_window.toolbar._feature_buttons) == before + 1


def test_registering_the_same_feature_twice_is_refused(app_window, registration_demo_id):
    app_window.register(DemoModel, DemoView, DemoPresenter)

    with pytest.raises(ValueError) as error:
        app_window.register(DemoModel, DemoView, DemoPresenter)

    assert registration_demo_id in str(error.value)


def test_the_manual_recipe_still_works(app_window):
    class OtherModel(DemoModel):
        FEATURE_ID = "registration_manual"

    model = OtherModel(app_window.context)
    view = DemoView(app_window.context)
    presenter = DemoPresenter(model, view, app_window.context)
    app_window.register_feature(presenter)

    assert app_window._registered_features["registration_manual"] is presenter


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
