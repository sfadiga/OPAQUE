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

from abc import ABC, ABCMeta
from typing import Dict, Any, Type, List, TypeVar

from opaque.models.annotations import Field

# Type variable for generic type hints in class methods
T = TypeVar('T', bound='AbstractModel')


class ModelMeta(ABCMeta):
    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)
        cls._fields = {}
        for base in reversed(bases):
            if hasattr(base, '_fields'):
                cls._fields.update(base._fields)

        for attr_name, attr_value in attrs.items():
            if isinstance(attr_value, Field):
                attr_value.name = attr_name
                cls._fields[attr_name] = attr_value

                private_name = f'_{attr_name}'

                def getter(self, name=attr_name, default=attr_value.default):
                    return getattr(self, f'_{name}', default)

                def setter(self, value, name=attr_name, field=attr_value):
                    # --- Validation ---
                    if field.choices is not None and value not in field.choices:
                        raise ValueError(
                            f"Value '{value}' for '{name}' is not in the allowed choices: {field.choices}")
                    if field.min_value is not None and value < field.min_value:
                        raise ValueError(
                            f"Value '{value}' for '{name}' is less than the minimum allowed value: {field.min_value}")
                    if field.max_value is not None and value > field.max_value:
                        raise ValueError(
                            f"Value '{value}' for '{name}' is greater than the maximum allowed value: {field.max_value}")
                    # ------------------

                    old_value = getattr(self, f'_{name}', None)
                    if old_value != value:
                        setattr(self, f'_{name}', value)
                        if field.binding:
                            self.notify(name, value)
                        self.mark_dirty()

                setattr(cls, attr_name, property(getter, setter))
        return cls


class AbstractModel(ABC, metaclass=ModelMeta):
    """
    Abstract base class for all models.

    Provides common functionality for model classes including:
    - Field management for settings/persistence
    - Serialization/deserialization
    - Validation
    - Observer pattern for MVP
    - Change tracking
    """

    _version = "1.0.0"

    def __init__(self) -> None:
        """Initialize the base model with change tracking and observer support."""
        # Flag indicating if model has unsaved changes
        self._dirty: bool = False
        # List of observers (presenters) for MVP pattern
        self._observers: List[Any] = []  # Any to avoid circular import

    # ========== Field Descriptor Methods (for Settings/Persistence) ==========

    @classmethod
    def get_fields(cls) -> Dict[str, Field]:
        """
        Get all field definitions.

        Returns:
            Dictionary mapping field names to Field instances
        """
        return cls._fields

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize model to dictionary.

        Returns:
            Dictionary containing serialized model data
        """
        data: Dict[str, Any] = {
            '_version': self._version,
            '_type': self.__class__.__name__
        }
        for name, field in self.get_fields().items():
            data[name] = field.serialize(getattr(self, name))
        return data

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any], **kwargs: Any) -> T:
        """
        Deserialize model from dictionary.

        Args:
            data: Dictionary containing serialized model data
            kwargs: Additional keyword arguments for model initialization

        Returns:
            New instance of the model class
        """
        instance = cls(**kwargs)
        for name, field in cls.get_fields().items():
            if name in data:
                setattr(instance, name, field.deserialize(data[name]))
        return instance

    def validate(self) -> bool:
        """
        Validate all fields in the model.

        Returns:
            True if all fields are valid, False otherwise
        """
        for name, field in self.get_fields().items():
            if not field.validate(getattr(self, name)):
                return False
        return True

    # ========== State Management ==========

    def mark_dirty(self) -> None:
        """Mark model as having unsaved changes."""
        self._dirty = True
        self.notify("dirty", True)

    @property
    def is_dirty(self) -> bool:
        """Check if the model has unsaved changes."""
        return self._dirty

    def clear_dirty(self) -> None:
        """Clear the dirty flag after saving."""
        self._dirty = False

    # ========== Observer Pattern Methods ==========

    def attach(self, observer: Any) -> None:
        """
        Attach an observer (typically a presenter) to this model.

        Args:
            observer: The observer to attach
        """
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Any) -> None:
        """
        Detach an observer from this model.

        Args:
            observer: The observer to detach
        """
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, property_name: str, value: Any) -> None:
        """
        Notify all observers of a property change.

        Args:
            property_name: Name of the changed property
            value: New value of the property
        """
        for observer in self._observers:
            if hasattr(observer, 'update'):
                observer.update(property_name, value)

    def cleanup(self) -> None:
        """Clean up model resources. Override if needed."""
        self._observers.clear()

    @property
    def feature_id(self) -> str:
        """
        Return the feature ID.
        This is used to uniquely identify the feature in the application.
        """
        if hasattr(self, 'FEATURE_NAME'):
            return self.FEATURE_NAME
        return self.__class__.__name__.lower().replace("model", "")
