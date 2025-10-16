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
from typing import Any, List, Optional


class Field:
    """
    Configuration class for model fields.
    An instance of this class is used to define a model field with its properties.
    """

    def __init__(self,
                 default: Any = None,
                 description: str = "",
                 binding: bool = False,
                 settings: bool = False,
                 workspace: bool = False,
                 min_value: Optional[float] = None,
                 max_value: Optional[float] = None,
                 choices: Optional[List[Any]] = None,
                 ui_type: str = "text",
                 **kwargs):
        self.default = default
        self.description = description
        self.binding = binding
        self.is_setting = settings
        self.is_workspace = workspace
        self.min_value = min_value
        self.max_value = max_value
        self.choices = choices
        self.ui_type = ui_type
        self.extra_config = kwargs
        self.name: str = ""  # Will be set by the metaclass


def settings_field(**kwargs: Any) -> 'Field':
    """
    Factory function to create a Field marked as a setting.
    """
    kwargs['settings'] = True
    if 'default_value' in kwargs:
        kwargs['default'] = kwargs.pop('default_value')
    return Field(**kwargs)


def workspace_field(**kwargs: Any) -> 'Field':
    """
    Factory function to create a Field marked as a workspace state.
    """
    kwargs['workspace'] = True
    if 'default_value' in kwargs:
        kwargs['default'] = kwargs.pop('default_value')
    return Field(**kwargs)


def binding_field(**kwargs: Any) -> 'Field':
    """
    Factory function to create a Field marked for data binding.
    """
    kwargs['binding'] = True
    if 'default_value' in kwargs:
        kwargs['default'] = kwargs.pop('default_value')
    return Field(**kwargs)
