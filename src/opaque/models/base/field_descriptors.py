# This Python file uses the following encoding: utf-8
"""
## @package field_descriptors
# Field descriptor classes for model attributes.
#
# This module provides various field descriptor classes that can be used
# to define typed attributes in model classes with validation and serialization support.
#
# @copyright 2025 Sandro Fadiga
# @license MIT License
"""

from typing import Any, Optional, Callable, Type, List

# @brief Base field descriptor for model attributes.
#
# This class implements the descriptor protocol to provide controlled access
# to model attributes with optional validation and serialization support.


class Field:
    """Base field descriptor for model attributes"""

    # @brief Initialize a field descriptor.
    # @param default Default value for the field
    # @param required Whether the field is required
    # @param validator Optional validation function
    # @param description Human-readable description of the field
    # @param scope Scope of the field ('global' or 'workspace')
    # @throws ValueError If scope is not 'global' or 'workspace'
    def __init__(self,
                 default: Any = None,
                 required: bool = False,
                 validator: Optional[Callable[[Any], bool]] = None,
                 description: str = "",
                 scope: str = 'global') -> None:
        if scope not in ('global', 'workspace'):
            raise ValueError("Scope must be either 'global' or 'workspace'")
        self.default: Any = default
        self.required: bool = required
        self.validator: Optional[Callable[[Any], bool]] = validator
        self.description: str = description
        self.scope: str = scope
        self.name: Optional[str] = None

    # @brief Set the name of the field when attached to a class.
    # @param owner The class that owns this descriptor
    # @param name The attribute name in the owner class
    def __set_name__(self, owner: Type[Any], name: str) -> None:
        self.name = name

    # @brief Get the field value from an instance.
    # @param obj The instance to get the value from
    # @param objtype The type of the instance
    # @return The field value or the descriptor itself if accessed on class
    def __get__(self, obj: Optional[Any], objtype: Optional[Type[Any]] = None) -> Any:
        if obj is None:
            return self
        return obj.__dict__.get(f'_{self.name}', self.default)

    # @brief Set the field value on an instance.
    # @param obj The instance to set the value on
    # @param value The value to set
    # @throws ValueError If validation fails
    def __set__(self, obj: Any, value: Any) -> None:
        if self.validator and not self.validator(value):
            raise ValueError(f"Invalid value for {self.name}: {value}")
        obj.__dict__[f'_{self.name}'] = value
        if hasattr(obj, 'mark_dirty'):
            obj.mark_dirty()

    # @brief Convert value to serializable format.
    # @param value The value to serialize
    # @return Serialized value
    def serialize(self, value: Any) -> Any:
        """Convert value to serializable format"""
        return value

    # @brief Convert from serialized format.
    # @param value The serialized value
    # @return Deserialized value
    def deserialize(self, value: Any) -> Any:
        """Convert from serialized format"""
        return value

# @brief String field with optional max length validation.
#
# Extends Field to provide string-specific validation including
# optional maximum length checking.


class StringField(Field):
    """String field with optional max length"""

    # @brief Initialize a string field.
    # @param max_length Optional maximum length for the string
    # @param kwargs Additional arguments passed to Field constructor
    def __init__(self, max_length: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.max_length: Optional[int] = max_length

# @brief Integer field with optional min/max validation.
#
# Provides integer-specific validation with optional minimum
# and maximum value constraints.


class IntField(Field):
    """Integer field with optional min/max"""

    # @brief Initialize an integer field.
    # @param min_value Optional minimum value
    # @param max_value Optional maximum value
    # @param kwargs Additional arguments passed to Field constructor
    def __init__(self, min_value: Optional[int] = None, max_value: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.min_value: Optional[int] = min_value
        self.max_value: Optional[int] = max_value

# @brief List field for collections.
#
# Handles list/array type fields with optional item type validation.


class ListField(Field):
    """List field for collections"""

    # @brief Initialize a list field.
    # @param item_type Optional type constraint for list items
    # @param kwargs Additional arguments passed to Field constructor
    def __init__(self, item_type: Optional[Type[Any]] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.item_type: Optional[Type[Any]] = item_type

# @brief Dictionary field for nested data.
#
# Handles dictionary/mapping type fields for storing key-value pairs.


class DictField(Field):
    """Dictionary field for nested data"""

    # @brief Initialize a dictionary field.
    # @param kwargs Additional arguments passed to Field constructor
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(default={}, **kwargs)

# @brief Boolean field.
#
# Simple boolean field for true/false values.


class BoolField(Field):
    """Boolean field"""

    # @brief Initialize a boolean field.
    # @param kwargs Additional arguments passed to Field constructor
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

# @brief Float field with optional min/max validation.
#
# Provides floating-point number validation with optional
# minimum and maximum value constraints.


class FloatField(Field):
    """Float field with optional min/max"""

    # @brief Initialize a float field.
    # @param min_value Optional minimum value
    # @param max_value Optional maximum value
    # @param kwargs Additional arguments passed to Field constructor
    def __init__(self, min_value: Optional[float] = None, max_value: Optional[float] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.min_value: Optional[float] = min_value
        self.max_value: Optional[float] = max_value

# @brief Choice field for selecting from predefined options.
#
# Provides a field that constrains values to a predefined list of
# valid choices, useful for dropdown/select inputs.


class ChoiceField(Field):
    """Field for selecting from a list of choices."""

    # @brief Initialize a choice field.
    # @param choices Optional list of valid choices
    # @param kwargs Additional arguments passed to Field constructor
    def __init__(self, choices: Optional[List[Any]] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.choices: List[Any] = choices if choices is not None else []
