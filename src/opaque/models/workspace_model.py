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

from abc import abstractmethod
from typing import Any
from ..core.model import BaseModel


class WorkspaceStateModel(BaseModel):
    """Base class for feature workspace state"""

    class Meta:
        abstract: bool = True

    def __init__(self, feature_id: str = "") -> None:
        super().__init__()
        self.feature_id: str = feature_id

    @abstractmethod
    def capture_state(self, widget: Any) -> None:
        """Capture current state from widget"""
        pass

    @abstractmethod
    def restore_state(self, widget: Any) -> None:
        """Restore state to widget"""
        pass
