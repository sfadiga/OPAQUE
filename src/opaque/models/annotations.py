# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.
"""
from enum import Enum
from typing import Any, List, Optional, Callable


class UIType(Enum):
    TEXT = "text"
    CHECKBOX = "checkbox"
    SPINBOX = "spinbox"
    DOUBLE_SPINBOX = "doublespinbox"
    COLOR_PICKER = "color_picker"
    COMBOBOX = "combobox"
    DROPDOWN = "dropdown"
    TEXTAREA = "textarea"
    SLIDER = "slider"
    LIST_VIEW = "list_view"
    FILE_SELECTOR = "file_selector"


class Field:
    """
    Metadata for one model field. Validation, persistence and UI generation
    read it.

    A Field object is a class attribute, so one Field is shared by every
    instance of the model class. It therefore holds no per-instance state and
    no observer list. Observers live on the model instance; see
    AbstractModel.attach.
    """

    def __init__(self,
                 default: Any = None,
                 description: str = "",
                 required: bool = False,
                 validator: Optional[Callable[[Any], bool]] = None,
                 settings: bool = False,
                 workspace: bool = False,
                 min_value: Optional[float] = None,
                 max_value: Optional[float] = None,
                 choices: Optional[List[Any]] = None,
                 ui_type: Optional[UIType] = None,
                 **kwargs: Any):
        self.default = default
        self.description = description
        self.required = required
        self.validator = validator
        self.is_setting = settings
        self.is_workspace = workspace
        self.min_value = min_value
        self.max_value = max_value
        self.choices = choices
        self.ui_type = ui_type
        self.extra_config = kwargs
        self.name: str = ""  # Will be set by ModelMeta

    def __set_name__(self, owner: Any, name: str):
        self.name = name

    def validate(self, value: Any) -> bool:
        """Validate the field value."""
        if self.required and value is None:
            return False
        if self.validator and not self.validator(value):
            return False
        if self.min_value is not None and value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False
        if self.choices and value not in self.choices:
            return False
        return True

    def serialize(self, value: Any) -> Any:
        """Convert value to a serializable format."""
        return value

    def deserialize(self, value: Any) -> Any:
        """Convert value from a serializable format."""
        return value

    def coerce(self, value: Any) -> Any:
        """
        Convert a raw widget value into the type this field stores.

        The settings dialog builds a widget from ui_type and reads back
        whatever that widget produces, which is not always the type the field
        holds: a combo box gives display text, a line edit gives a string.
        The dialog calls this before it queues a value, so a round trip
        through the dialog can no longer change a type.

        The base implementation maps a value back onto the declared choice
        object, because a combo box only ever hands back text. A subclass
        calls super().coerce(value) first and then converts.

        None passes through unchanged: an unset value stays unset.

        Raises:
            ValueError: When the value is not one of the declared choices.
        """
        if value is None:
            return None

        if self.choices:
            for choice in self.choices:
                if choice == value or str(choice) == str(value):
                    return choice
            raise ValueError(
                f"{value!r} is not one of the allowed choices for "
                f"'{self.name}': {self.choices}")

        return value

    def display(self, value: Any) -> str:
        """
        Return the value as the text a line edit or a combo box shows.

        The inverse of coerce for the text widgets. Override it when str()
        gives something the user cannot edit back into the same value.
        """
        return "" if value is None else str(value)


class StringField(Field):
    """Field for string values."""

    def __init__(self, ui_type: UIType = UIType.TEXT, **kwargs: Any):
        super().__init__(ui_type=ui_type, **kwargs)

    def coerce(self, value: Any) -> Any:
        value = super().coerce(value)
        return None if value is None else str(value)


class IntField(Field):
    """Field for integer values."""

    def __init__(self, ui_type: UIType = UIType.SPINBOX, **kwargs: Any):
        super().__init__(ui_type=ui_type, **kwargs)

    def coerce(self, value: Any) -> Any:
        value = super().coerce(value)
        return None if value is None else int(value)


class FloatField(Field):
    """Field for float values."""

    def __init__(self, **kwargs: Any):
        # A float needs a widget with a fraction. It used to declare
        # UIType.SPINBOX, so the dialog drew a QSpinBox and truncated every
        # value it read back.
        super().__init__(ui_type=UIType.DOUBLE_SPINBOX, **kwargs)

    def coerce(self, value: Any) -> Any:
        value = super().coerce(value)
        return None if value is None else float(value)


class BoolField(Field):
    """Field for boolean values."""

    # The strings a check box or a settings file can hold for True.
    TRUE_WORDS = ("1", "true", "yes", "on")

    def __init__(self, **kwargs: Any):
        super().__init__(ui_type=UIType.CHECKBOX, **kwargs)

    def coerce(self, value: Any) -> Any:
        value = super().coerce(value)
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip().lower() in self.TRUE_WORDS
        return bool(value)


class ListField(Field):
    """Field for list values. Shown and edited as a list; coerce() still
    accepts comma separated text for old settings files."""

    def __init__(self, **kwargs: Any):
        super().__init__(ui_type=UIType.LIST_VIEW, **kwargs)

    def coerce(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            return list(value)
        text = str(value).strip()
        if not text:
            return []
        return [item.strip() for item in text.split(",")]

    def display(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return ", ".join(str(item) for item in value)
        return str(value)


class ChoiceField(Field):
    """Field for values from a list of choices."""

    def __init__(self, **kwargs: Any):
        super().__init__(ui_type=UIType.DROPDOWN, **kwargs)
