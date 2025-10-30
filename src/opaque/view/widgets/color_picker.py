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
from PySide6.QtWidgets import QWidget, QPushButton, QColorDialog, QHBoxLayout, QLineEdit
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Signal, Slot


class ColorPicker(QWidget):
    """A widget for selecting a color."""
    colorChanged = Signal(str)

    def __init__(self, initial_color: str = "#ffffff", parent=None):
        super().__init__(parent)
        self._color = QColor(initial_color)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.line_edit = QLineEdit(self._color.name())
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.layout.addWidget(self.line_edit)

        self.button = QPushButton("...")
        self.button.setFixedWidth(30)
        self.button.clicked.connect(self._on_button_clicked)
        self.layout.addWidget(self.button)

        self._update_button_color()

    def color(self) -> str:
        return self._color.name()

    def setColor(self, color: str):
        new_color = QColor(color)
        if self._color != new_color:
            self._color = new_color
            self.line_edit.setText(self._color.name())
            self._update_button_color()
            self.colorChanged.emit(self._color.name())

    @Slot()
    def _on_button_clicked(self):
        dialog = QColorDialog(self._color, self)
        if dialog.exec():
            self.setColor(dialog.selectedColor().name())

    @Slot(str)
    def _on_text_changed(self, text: str):
        new_color = QColor(text)
        if new_color.isValid() and self._color != new_color:
            self._color = new_color
            self._update_button_color()
            self.colorChanged.emit(self._color.name())

    def _update_button_color(self):
        palette = self.button.palette()
        palette.setColor(QPalette.Button, self._color)
        self.button.setPalette(palette)
        self.button.update()
