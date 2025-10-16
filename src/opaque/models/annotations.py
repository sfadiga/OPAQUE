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
    """Enumeration for standard UI widget types for settings generation."""
    TEXT = "text"
    SPINBOX = "spinbox"
    CHECKBOX = "checkbox"
    COLOR_PICKER = "color_picker"
    DROPDOWN = "dropdown"
    TEXTAREA = "textarea"
    SLIDER = "slider"
    FILE_SELECTOR = "file_selector" # TODO TBD


class Field:
    """
    Configuration class for model fields. It provides metadata for validation,
    persistence, and UI generation.
    """

    def __init__(self,
                 default: Any = None,
                 description: str = "",
                 required: bool = False,
                 validator: Optional[Callable[[Any], bool]] = None,
                 binding: bool = False,
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
        self.binding = binding
        self.is_setting = settings
        self.is_workspace = workspace
        self.min_value = min_value
        self.max_value = max_value
        self.choices = choices
        self.ui_type = ui_type
        self.extra_config = kwargs
        self.name: str = ""  # Will be set by BaseModel

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


class StringField(Field):
    """Field for string values."""
    def __init__(self, ui_type: UIType = UIType.TEXT, **kwargs: Any):
        super().__init__(ui_type=ui_type, **kwargs)


class IntField(Field):
    """Field for integer values."""
    def __init__(self, **kwargs: Any):
        super().__init__(ui_type=UIType.SPINBOX, **kwargs)


class FloatField(Field):
    """Field for float values."""
    def __init__(self, **kwargs: Any):
        super().__init__(ui_type=UIType.SPINBOX, **kwargs)


class BoolField(Field):
    """Field for boolean values."""
    def __init__(self, **kwargs: Any):
        super().__init__(ui_type=UIType.CHECKBOX, **kwargs)


class ListField(Field):
    """Field for list values."""
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)


class ChoiceField(Field):
    """Field for values from a list of choices."""
    def __init__(self, **kwargs: Any):
        super().__init__(ui_type=UIType.DROPDOWN, **kwargs)
