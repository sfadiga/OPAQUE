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
from typing import List
from PySide6.QtWidgets import QTextEdit
from opaque.core.view import BaseView


class LoggingView(BaseView):
    """A simple feature window that displays text logs."""

    def __init__(self, feature_id: str):
        super().__init__(feature_id)

        # Create and set the central widget
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.set_content(self.log_view)

        self.log_view.append(self.tr("Logging window initialized."))

    def update_log(self, messages: List[str]):
        self.log_view.clear()
        for message in messages:
            self.log_view.append(message)
