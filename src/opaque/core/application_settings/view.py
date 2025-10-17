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
from opaque.core.view import BaseView


class ApplicationView(BaseView):
    """
    A view for application-wide settings.
    This view does not have a UI component, but it is used to
    integrate the application settings into the settings dialog.
    """

    def __init__(self, feature_id: str):
        super().__init__(feature_id)
