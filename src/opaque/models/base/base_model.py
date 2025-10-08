# This Python file uses the following encoding: utf-8
"""
## @package base_model
# Base model class for all data models.
#
# This module provides the abstract base class for all models in the system,
# implementing common functionality for serialization, validation, and field management.
#
# @copyright 2025 Sandro Fadiga
# @license MIT License
"""

from abc import ABC
from typing import Dict, Any, Type, List, Callable, TypeVar

from .field_descriptors import Field

# @var T
# Type variable for generic type hints in class methods
T = TypeVar('T', bound='BaseModel')

# @brief Abstract base class for all models.
#
# Provides common functionality for model classes including field management,
# serialization/deserialization, validation, and change tracking.


class BaseModel(ABC):
    """Abstract base class for all models"""

    # @brief Model version for migration support
    _version: int = 1

    # @brief Initialize the base model.
    #
    # Sets up the model with change tracking and observer support.
    def __init__(self) -> None:
        # @brief Flag indicating if model has unsaved changes
        self._dirty: bool = False
        # @brief List of observer callbacks for change notifications
        self._observers: List[Callable] = []

    # @brief Get all field definitions for the model class.
    #
    # Inspects the class hierarchy to collect all Field descriptors,
    # caching the result for performance.
    #
    # @return Dictionary mapping field names to Field instances
    @classmethod
    def get_fields(cls) -> Dict[str, Field]:
        """Get all field definitions by inspecting class attributes."""
        # Check for a cached version to avoid repeated inspection
        if not hasattr(cls, '_cached_fields'):
            cls._cached_fields = {}
            # Walk the Method Resolution Order to include fields from parent models
            for c in reversed(cls.__mro__):
                for name, attr in c.__dict__.items():
                    if isinstance(attr, Field):
                        cls._cached_fields[name] = attr
        return cls._cached_fields

    # @brief Serialize model to dictionary.
    #
    # Converts the model instance to a dictionary representation
    # suitable for JSON serialization or storage.
    #
    # @return Dictionary containing serialized model data
    def to_dict(self) -> Dict[str, Any]:
        """Serialize model to dictionary"""
        data: Dict[str, Any] = {
            '_version': self._version,
            '_type': self.__class__.__name__
        }
        for name, field in self.get_fields().items():
            data[name] = field.serialize(getattr(self, name))
        return data

    # @brief Deserialize model from dictionary.
    #
    # Creates a new model instance from a dictionary representation,
    # typically loaded from storage or received via API.
    #
    # @param cls The class to instantiate
    # @param data Dictionary containing serialized model data
    # @param kwargs Additional keyword arguments for model initialization
    # @return New instance of the model class
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any], **kwargs: Any) -> T:
        """Deserialize model from dictionary"""
        instance = cls(**kwargs)
        for name, field in cls.get_fields().items():
            if name in data:
                setattr(instance, name, field.deserialize(data[name]))
        return instance

    # @brief Validate all fields in the model.
    #
    # Runs validation on all fields using their configured validators.
    #
    # @return True if all fields are valid, False otherwise
    def validate(self) -> bool:
        """Validate all fields"""
        for name, field in self.get_fields().items():
            if not field.validate(getattr(self, name)):
                return False
        return True

    # @brief Mark model as having unsaved changes.
    #
    # Sets the dirty flag and notifies all registered observers
    # about the change.
    def mark_dirty(self) -> None:
        """Mark model as changed"""
        self._dirty = True
        self._notify_observers()

    # @brief Notify all registered observers of a change.
    #
    # Called internally when the model is marked as dirty.
    # Currently a placeholder for future observer pattern implementation.
    def _notify_observers(self) -> None:
        """Notify all registered observers of a change."""
        pass
