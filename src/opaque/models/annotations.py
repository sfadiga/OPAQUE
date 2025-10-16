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

from typing import Any, Optional, List, Callable


class AnnotatedField:
    """Base class for annotated fields with descriptor protocol."""

    def __init__(self, default_value: Any = None, description: str = ""):
        self.default_value = default_value
        self.description = description
        self.name = None
        self._is_settings_field = False
        self._is_workspace_field = False

    def __set_name__(self, owner, name):
        """Called when the descriptor is assigned to a class attribute."""
        self.name = name

    def __get__(self, obj, objtype=None):
        """Get the field value from an instance."""
        if obj is None:
            return self
        return obj.__dict__.get(f'_{self.name}', self.default_value)

    def __set__(self, obj, value):
        """Set the field value on an instance."""
        obj.__dict__[f'_{self.name}'] = value
        # Notify observers if the model has that capability
        if hasattr(obj, 'notify_observers'):
            obj.notify_observers(f'{self.name}_changed', value)


class SettingsField(AnnotatedField):
    """Field descriptor for settings that are persisted globally."""

    def __init__(self,
                 default_value: Any = None,
                 description: str = "",
                 min_value: Optional[float] = None,
                 max_value: Optional[float] = None,
                 choices: Optional[List[Any]] = None,
                 validator: Optional[Callable] = None):
        super().__init__(default_value, description)
        self.min_value = min_value
        self.max_value = max_value
        self.choices = choices
        self.validator = validator
        self._is_settings_field = True
        self.default = default_value  # Alias for compatibility

    def __set__(self, obj, value):
        """Set with optional validation."""
        if self.validator and not self.validator(value):
            raise ValueError(f"Invalid value for {self.name}: {value}")

        if self.min_value is not None and value < self.min_value:
            raise ValueError(
                f"Value for {self.name} must be >= {self.min_value}")

        if self.max_value is not None and value > self.max_value:
            raise ValueError(
                f"Value for {self.name} must be <= {self.max_value}")

        if self.choices and value not in self.choices:
            raise ValueError(
                f"Value for {self.name} must be one of {self.choices}")

        super().__set__(obj, value)


class WorkspaceField(AnnotatedField):
    """Field descriptor for workspace state that is persisted per session."""

    def __init__(self,
                 default_value: Any = None,
                 description: str = "",
                 serialize_name: Optional[str] = None,
                 serializer: Optional[Callable] = None,
                 deserializer: Optional[Callable] = None):
        super().__init__(default_value, description)
        self.serialize_name = serialize_name
        self.serializer = serializer
        self.deserializer = deserializer
        self._is_workspace_field = True
        self.default = default_value  # Alias for compatibility

    def serialize(self, value: Any) -> Any:
        """Serialize the value for storage."""
        if self.serializer:
            return self.serializer(value)
        return value

    def deserialize(self, value: Any) -> Any:
        """Deserialize the value from storage."""
        if self.deserializer:
            return self.deserializer(value)
        return value


def settings_field(default_value: Any = None,
                   description: str = "",
                   min_value: Optional[float] = None,
                   max_value: Optional[float] = None,
                   choices: Optional[List[Any]] = None,
                   validator: Optional[Callable] = None) -> SettingsField:
    """
    Create a settings field descriptor.

    Args:
        default_value: Default value for the field
        description: Description for UI/documentation
        min_value: Minimum value for numeric fields
        max_value: Maximum value for numeric fields
        choices: List of valid choices
        validator: Optional validation function

    Returns:
        SettingsField descriptor instance

    Example:
        class MyModel(BaseModel):
            threshold = settings_field(default_value=0.5, description="Processing threshold")
    """
    return SettingsField(
        default_value=default_value,
        description=description,
        min_value=min_value,
        max_value=max_value,
        choices=choices,
        validator=validator
    )


def workspace_field(default_value: Any = None,
                    description: str = "",
                    serialize_name: Optional[str] = None,
                    serializer: Optional[Callable] = None,
                    deserializer: Optional[Callable] = None) -> WorkspaceField:
    """
    Create a workspace field descriptor.

    Args:
        default_value: Default value for the field
        description: Description for UI/documentation
        serialize_name: Custom name in workspace file
        serializer: Custom serialization function
        deserializer: Custom deserialization function

    Returns:
        WorkspaceField descriptor instance

    Example:
        class MyModel(BaseModel):
            current_value = workspace_field(default_value="0", description="Current display value")
    """
    return WorkspaceField(
        default_value=default_value,
        description=description,
        serialize_name=serialize_name,
        serializer=serializer,
        deserializer=deserializer
    )


def get_settings_fields(model_instance) -> dict:
    """
    Extract all settings fields from a model instance.

    Args:
        model_instance: Model instance to inspect

    Returns:
        Dictionary mapping field names to their SettingsField descriptors
    """
    settings_fields = {}

    for attr_name in dir(model_instance.__class__):
        if not attr_name.startswith('_'):
            try:
                attr = getattr(model_instance.__class__, attr_name)
                if isinstance(attr, SettingsField):
                    settings_fields[attr_name] = attr
            except AttributeError:
                continue

    return settings_fields


def get_workspace_fields(model_instance) -> dict:
    """
    Extract all workspace fields from a model instance.

    Args:
        model_instance: Model instance to inspect

    Returns:
        Dictionary mapping field names to their WorkspaceField descriptors
    """
    workspace_fields = {}

    for attr_name in dir(model_instance.__class__):
        if not attr_name.startswith('_'):
            try:
                attr = getattr(model_instance.__class__, attr_name)
                if isinstance(attr, WorkspaceField):
                    workspace_fields[attr_name] = attr
            except AttributeError:
                continue

    return workspace_fields
