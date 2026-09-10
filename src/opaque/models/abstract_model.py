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

from PySide6.QtCore import QCoreApplication, QThread

from opaque.models.annotations import Field

# Type variable for generic type hints in class methods
T = TypeVar('T', bound='AbstractModel')


def _assert_ui_thread(model_name: str, field_name: str) -> None:
    """
    Refuse a field write that does not come from the UI thread.

    A field write calls presenter.update() on the same stack, and a presenter
    touches widgets. Qt allows a widget to be touched only from the thread
    that owns the QApplication. A write from a worker thread therefore
    corrupts the UI or crashes the process at a random later point, far from
    the line that caused it. Failing here names the field instead.

    The check does nothing when no QCoreApplication exists, so a model stays
    unit testable with no Qt application at all.

    Raises:
        RuntimeError: When the calling thread is not the UI thread.
    """
    application = QCoreApplication.instance()
    if application is None:
        return
    if QThread.currentThread() is application.thread():
        return

    thread_name = QThread.currentThread().objectName() or "a worker thread"
    raise RuntimeError(
        f"{model_name}.{field_name} was written from {thread_name}, not from "
        f"the UI thread. A field write calls presenter.update() on the same "
        f"stack, and a presenter touches widgets, which is legal only on the "
        f"UI thread. Queue the value and drain it on the UI thread; "
        f"src/opaque/services/console_service.py shows the approved shape."
    )


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

                def getter(self, name=attr_name, default=attr_value.default):
                    return getattr(self, f'_{name}', default)

                def setter(self, value, name=attr_name, field=attr_value):
                    _assert_ui_thread(type(self).__name__, name)

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
                    if field.validator is not None and not field.validator(value):
                        raise ValueError(
                            f"Value '{value}' for '{name}' was rejected by "
                            f"the field's validator callable")
                    # ------------------

                    # The fallback matches the getter's default: the field
                    # has never been written, so its logical old value is
                    # the field's own default, not None.
                    old_value = getattr(self, f'_{name}', field.default)
                    if old_value != value:
                        setattr(self, f'_{name}', value)
                        # The observer list belongs to this instance, not to
                        # the Field object, which every instance shares.
                        self._notify_field_change(  # pylint: disable=protected-access
                            name, old_value, value)
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

    # ModelMeta.__new__ always rebuilds this for every subclass; the
    # declaration here is only so mypy knows the attribute exists.
    _fields: Dict[str, Field] = {}

    # The one stable identity of this feature. A subclass must declare it.
    # Empty means undeclared, which feature_id() reports.
    FEATURE_ID: str = ""

    @classmethod
    def feature_id(cls) -> str:
        """
        Return the one stable identity of this feature.

        It is the key of the feature registry, of the block in settings.json
        and of the block in a workspace file. It must not change once an
        application has shipped, because a stored file is keyed on it.

        feature_name() is a different thing: a display title, translated, free
        to change. Using the title as a key meant that translating the
        interface moved the key.

        Raises:
            NotImplementedError: When the subclass declares no FEATURE_ID.
        """
        if not cls.FEATURE_ID:
            raise NotImplementedError(
                f"{cls.__name__} must declare FEATURE_ID. Write:\n"
                f"    class {cls.__name__}(BaseModel):\n"
                f"        FEATURE_ID = 'my_feature'\n"
                f"It is the key of the feature registry, of settings.json and "
                f"of the workspace file, so keep it short, keep it in ASCII, "
                f"and never change it once your application has shipped. The "
                f"display title is feature_name(), which is free to change.")
        return cls.FEATURE_ID

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
        """
        Mark the model as having unsaved changes.

        This sets a flag and nothing more. It used to notify every observer
        with the literal field name "dirty", so one field write called every
        presenter twice. Nothing in the framework or in the examples ever
        read that notification. Ask is_dirty when you need the flag.
        """
        self._dirty = True

    @property
    def is_dirty(self) -> bool:
        """Check if the model has unsaved changes."""
        return self._dirty

    def clear_dirty(self) -> None:
        """Clear the dirty flag after saving."""
        self._dirty = False

    # ========== Observer Pattern Methods ==========

    def _observer_list(self) -> List[Any]:
        """
        Return this instance's observer list, creating it when needed.

        A subclass may write a field inside its own __init__ before it calls
        super().__init__(), and the write notifies. Building the list on
        demand keeps that legal, and keeps the list on the instance, which is
        the whole point: a list on the Field object is shared by every
        instance of the model class.
        """
        observers = self.__dict__.get("_observers")
        if observers is None:
            observers = []
            self._observers = observers
        return observers

    def attach(self, observer: Any) -> None:
        """
        Attach an observer to this model instance.

        This is the method a presenter uses. BasePresenter.__init__ calls it.

        Args:
            observer: An object with an
                update(field_name, new_value, old_value, model) method.

        Raises:
            TypeError: When the observer has no update method. Failing here
                is deliberate: a silent miss would look like a model that
                never changes.
        """
        if not callable(getattr(observer, "update", None)):
            raise TypeError(
                f"{type(observer).__name__} cannot observe "
                f"{type(self).__name__}: it has no callable update("
                f"field_name, new_value, old_value, model) method.")

        observers = self._observer_list()
        if observer not in observers:
            observers.append(observer)

    def detach(self, observer: Any) -> None:
        """
        Detach an observer from this model instance.

        Args:
            observer: The observer to detach. Detaching an observer that was
                never attached does nothing.
        """
        observers = self._observer_list()
        if observer in observers:
            observers.remove(observer)

    def _notify_field_change(
            self, field_name: str, old_value: Any, new_value: Any) -> None:
        """
        Tell every observer of this instance that one field changed.

        Called by the property setter that ModelMeta generates. The list is
        copied first, because an observer is allowed to detach itself while
        it is being told.
        """
        for observer in list(self._observer_list()):
            observer.update(field_name, new_value, old_value, self)

    def notify(self, property_name: str, value: Any) -> None:
        """
        Notify all observers of a change that is not a Field write.

        Use this for derived state that no Field holds, for example
        notify("error", message). A Field write notifies on its own; do not
        call this from a setter.

        Args:
            property_name: Name of the changed property
            value: New value of the property
        """
        for observer in list(self._observer_list()):
            observer.update(property_name, value, None, self)

    def cleanup(self) -> None:
        """
        Release this instance's observers. Override if the model owns more.

        Only this instance is affected. The previous version cleared the
        observer list on every shared Field object, which silenced every
        other instance of the same model class.
        """
        self._observer_list().clear()
