# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.

A file path entry for the settings dialog: a line edit plus a browse button.
The settings dialog builds one for every field declared with
UIType.FILE_SELECTOR.
"""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

from opaque.view.theme import MINIMUM_HIT_TARGET


class FileSelector(QWidget):
    """One file path, editable by hand or through the platform dialog."""

    pathChanged = Signal(str)

    def __init__(self, initial_path: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.path_edit = QLineEdit(initial_path)
        self.path_edit.setAccessibleName(self.tr("File path"))
        self.path_edit.textChanged.connect(self.pathChanged.emit)
        layout.addWidget(self.path_edit)

        self.browse_button = QPushButton(self.tr("Browse..."))
        self.browse_button.setMinimumHeight(MINIMUM_HIT_TARGET)
        self.browse_button.clicked.connect(self._browse)
        layout.addWidget(self.browse_button)

    def path(self) -> str:
        """The current path text."""
        return self.path_edit.text()

    def _browse(self) -> None:
        """Open the platform file dialog and take its answer."""
        chosen, _selected_filter = QFileDialog.getOpenFileName(
            self, self.tr("Select a file"), self.path_edit.text())
        if chosen:
            self.path_edit.setText(chosen)
