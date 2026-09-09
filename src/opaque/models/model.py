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

from PySide6.QtGui import QIcon

from opaque.features.context import FeatureContext
from opaque.models.abstract_model import AbstractModel


class BaseModel(AbstractModel):
    """
    The model of one feature.

    It takes a FeatureContext, not the application. A model that held the
    whole application could reach the toolbar, the MDI area and the service
    registry, and one of them did reach a private attribute.
    """

    def __init__(self, context: FeatureContext) -> None:
        super().__init__()
        self._context: FeatureContext = context

    @property
    def context(self) -> FeatureContext:
        """The context this feature was built with."""
        return self._context

    # --- FEATURE API ---
    # A name is identity, so a subclass must declare it. An icon and a
    # description are decoration, so both have a default that works.

    def feature_name(self) -> str:
        """
        The display name of this feature. A subclass must override it.

        The toolbar button, the window title and the View menu all read it.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement feature_name(). Write:\n"
            f"    def feature_name(self) -> str:\n"
            f"        return self.tr(\"My Feature\")\n"
            f"The toolbar button, the window title and the View menu read it."
        )

    def feature_icon(self) -> QIcon:
        """
        The icon of this feature. Optional.

        The default is a null QIcon, which the toolbar and the window title
        both accept: they show text alone. Override it with
        QIcon.fromTheme("name") or a QIcon built from a resource path.
        """
        return QIcon()

    def feature_description(self) -> str:
        """
        One sentence about this feature. Optional.

        Shown as the tool tip of the toolbar button. The default is empty,
        which shows no tool tip.
        """
        return ""

    # ----------------------------------------------------
