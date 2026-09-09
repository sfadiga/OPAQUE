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


def test_the_context_the_model_was_given_is_readable(qapp):
    marker = object()
    model = _NamedModel(marker)
    assert model.context is marker
