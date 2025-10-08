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

from opaque.models.settings.settings_model import SettingsModel
from opaque.models.base.field_descriptors import BoolField, IntField, StringField


class LoggingSettings(SettingsModel):
    """Settings for the Logging feature"""

    show_timestamps = BoolField(
        default=True, description="Prepend a timestamp to each log message.")
    log_level = StringField(
        default="INFO", description="The minimum level of message to display.")
    max_lines = IntField(default=1000, min_value=100, max_value=10000,
                         description="Maximum number of lines to keep in the log.")
