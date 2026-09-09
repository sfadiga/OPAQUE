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


def test_the_presenter_identity_comes_from_the_model(app_window):
    for presenter in app_window._registered_features.values():
        assert presenter.feature_id == presenter.model.feature_id()


def test_the_presenter_constructor_takes_no_identity_argument():
    import inspect

    from opaque.presenters.presenter import BasePresenter

    parameters = list(
        inspect.signature(BasePresenter.__init__).parameters)
    assert parameters == ["self", "model", "view", "context"]


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
