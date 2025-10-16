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

from abc import ABC
from typing import Dict, Any, Type, List, Optional, TypeVar

from opaque.models.field_descriptors import Field

# Type variable for generic type hints in class methods
T = TypeVar('T', bound='AbstractModel')


class AbstractModel(ABC):
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
        Get all field definitions by inspecting class attributes.
        
        Returns:
            Dictionary mapping field names to Field instances
        """
        # Check for a cached version to avoid repeated inspection
        if not hasattr(cls, '_cached_fields'):
            cls._cached_fields = {}
            # Walk the Method Resolution Order to include fields from parent models
            for c in reversed(cls.__mro__):
                for name, attr in c.__dict__.items():
                    if isinstance(attr, Field):
                        cls._cached_fields[name] = attr
        return cls._cached_fields

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

    def create_property(self, name: str, initial_value: Any = None) -> None:
        """
        Helper method to create an observable property.
        This should be called in the model's initialize() method.
        
        Args:
            name: Property name
            initial_value: Initial value for the property
        """
        private_name = f'_{name}_value'
        setattr(self, private_name, initial_value)

        def getter(self):
            return getattr(self, private_name)

        def setter(self, value):
            old_value = getattr(self, private_name)
            if old_value != value:
                setattr(self, private_name, value)
                self.notify(name, value)
                self.mark_dirty()

        # Create property and attach to class
        prop = property(getter, setter)
        setattr(self.__class__, name, prop)

    # ========== State Management ==========

    def mark_dirty(self) -> None:
        """Mark model as having unsaved changes."""
        self._dirty = True
        self._notify_observers()


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

    def _notify_observers(self) -> None:
        """Notify all registered observers of a change."""
        for observer in self._observers:
            if hasattr(observer, 'on_model_changed'):
                observer.on_model_changed()

    def cleanup(self) -> None:
        """Clean up model resources. Override if needed."""
        self._observers.clear()
