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

from typing import Dict

from PySide6.QtGui import QIcon

from opaque.models.model import AbstractModel

class BaseModel(AbstractModel):

    def __init__(self) -> None:
        super().__init__()

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

    def feature_visibility(self) -> bool:
        """Override in subclasses"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement feature_visibility()")

    # ----------------------------------------------------
