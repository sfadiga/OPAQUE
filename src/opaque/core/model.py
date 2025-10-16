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

from typing import Dict, Any
from PySide6.QtGui import QIcon
from opaque.models.model import AbstractModel
from opaque.models.annotations import Field


class BaseModel(AbstractModel):

    def __init__(self, feature_id: str) -> None:
        super().__init__()
        self._feature_id = feature_id
        # Use super's setattr to avoid our override during initialization
        super().__setattr__('_fields', {})
        super().__setattr__('_values', {})

        # Collect fields from the class and its parents
        for cls in reversed(self.__class__.__mro__):
            for name, attr in cls.__dict__.items():
                if isinstance(attr, Field):
                    self._fields[name] = attr
                    # Initialize with default value
                    self._values[name] = attr.default

    def __getattribute__(self, name: str) -> Any:
        _fields = super().__getattribute__('_fields')
        if name != '_fields' and _fields and name in _fields:
            _values = super().__getattribute__('_values')
            return _values.get(name)
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: Any) -> None:
        # This check prevents the method from running during __init__ before _fields is set.
        if '_fields' not in self.__dict__ or name in ('_fields', '_values'):
            super().__setattr__(name, value)
            return

        if name in self._fields:
            _values = super().__getattribute__('_values')
            old_value = _values.get(name)
            if old_value != value:
                _values[name] = value
                if hasattr(self, 'notify'):
                    self.notify(name, value)
        else:
            super().__setattr__(name, value)


    @property
    def feature_id(self):
        return self._feature_id

    # --- FEATURE API (Override in subclasses) ---

    def feature_name(self) -> str:
        """Must be overridden in subclasses"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement feature_name()")

    def feature_icon(self) -> QIcon:
        """Override in subclasses to provide icon (can return str or QIcon)"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement feature_icon()")

    def feature_description(self) -> str:
        """Override in subclasses"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement feature_description()")

    def feature_modal(self) -> bool:
        """Override in subclasses"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement feature_modal()")

    # ----------------------------------------------------
