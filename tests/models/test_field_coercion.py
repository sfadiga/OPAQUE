# This Python file uses the following encoding: utf-8
"""Tests for the widget round trip of every field kind."""

import pytest

from opaque.models.annotations import (
    BoolField,
    ChoiceField,
    Field,
    FloatField,
    IntField,
    ListField,
    StringField,
    UIType,
)


def test_a_float_field_is_drawn_with_a_double_spin_box():
    assert FloatField().ui_type == UIType.DOUBLE_SPINBOX


def test_an_int_field_is_drawn_with_a_spin_box():
    assert IntField().ui_type == UIType.SPINBOX


def test_an_int_field_reads_back_an_int():
    assert IntField().coerce("7") == 7


def test_an_int_field_refuses_text_that_is_not_a_number():
    with pytest.raises(ValueError):
        IntField().coerce("seven")


def test_a_float_field_keeps_the_fraction():
    assert FloatField().coerce("2.5") == 2.5


def test_a_bool_field_reads_back_a_bool():
    field = BoolField()
    assert field.coerce("true") is True
    assert field.coerce("false") is False
    assert field.coerce(1) is True
    assert field.coerce(0) is False


def test_a_string_field_reads_back_a_string():
    assert StringField().coerce(12) == "12"


def test_a_choice_field_reads_back_the_declared_choice_object():
    field = ChoiceField(choices=[1, 2, 3])
    value = field.coerce("2")
    assert value == 2
    assert isinstance(value, int)


def test_a_choice_field_refuses_a_value_that_is_not_a_choice():
    field = ChoiceField(choices=["a", "b"])
    with pytest.raises(ValueError):
        field.coerce("c")


def test_a_plain_field_with_choices_also_maps_back():
    field = Field(choices=[10, 20])
    assert field.coerce("20") == 20


def test_a_plain_field_without_choices_passes_the_value_through():
    marker = object()
    assert Field().coerce(marker) is marker


def test_none_passes_through_every_field_kind():
    for field in (Field(), StringField(), IntField(), FloatField(),
                  BoolField(), ListField(), ChoiceField()):
        assert field.coerce(None) is None


def test_a_list_field_reads_back_a_list_from_comma_separated_text():
    assert ListField().coerce("a, b ,c") == ["a", "b", "c"]


def test_a_list_field_passes_a_real_list_through():
    assert ListField().coerce(["a", "b"]) == ["a", "b"]


def test_an_empty_string_gives_an_empty_list():
    assert ListField().coerce("") == []


def test_a_list_field_is_displayed_comma_separated():
    assert ListField().display(["a", "b"]) == "a, b"


def test_the_display_of_a_list_field_round_trips():
    field = ListField()
    original = ["one", "two", "three"]
    assert field.coerce(field.display(original)) == original


def test_display_of_none_is_an_empty_string():
    assert Field().display(None) == ""


def test_display_of_a_number_is_its_text():
    assert IntField().display(7) == "7"


def test_a_list_field_accepts_an_explicit_ui_type():
    """A comma-text editor is a valid choice; the argument used to raise
    TypeError ('multiple values for ui_type') at class-definition time."""
    field = ListField(ui_type=UIType.TEXT)
    assert field.ui_type is UIType.TEXT


def test_a_float_field_accepts_an_explicit_ui_type():
    field = FloatField(ui_type=UIType.SLIDER)
    assert field.ui_type is UIType.SLIDER


def test_the_ui_type_defaults_are_unchanged():
    assert ListField().ui_type is UIType.LIST_VIEW
    assert FloatField().ui_type is UIType.DOUBLE_SPINBOX
