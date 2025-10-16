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

from .settings_model import SettingsModel
from .field_descriptors import ChoiceField


class ApplicationSettings(SettingsModel):
    """
    Global application settings that apply to the entire application.

    This is the default global settings model provided by the framework.
    Applications can extend this class to add custom global settings.
    """

    # Theme selection
    theme = ChoiceField(
        choices=[],  # This will be populated dynamically by the framework
        default='Default',
        description="Application visual theme"
    )

    # Language selection (for future internationalization support)
    language = ChoiceField(
        choices=['en_US', 'es_ES', 'fr_FR',
                 'de_DE', 'pt_BR', 'ja_JP', 'zh_CN'],
        default='en_US',
        description="User interface language"
    )

    def __init__(self, **kwargs):
        # Global settings don't need a feature_id, but we accept it for consistency
        if 'feature_id' in kwargs:
            kwargs.pop('feature_id')
        super().__init__(feature_id='global')
