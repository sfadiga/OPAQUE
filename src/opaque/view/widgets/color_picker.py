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
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal, Slot

from opaque.view.theme import (
    StatusRole,
    interactive,
    outline,
    readable_foreground,
    status_colors,
)


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

    def _update_button_color(self) -> None:
        """
        Paint the swatch with a style sheet.

        The palette cannot be used here. Every theme this framework ships
        installs an application wide style sheet, and a style sheet beats the
        palette for every property it names, so a swatch set through
        QPalette.Button never appeared on the screen.
        """
        self.button_text_colour = readable_foreground(self._color.name())
        self.button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color.name()};
                color: {self.button_text_colour};
                border: 1px solid {outline()};
                border-radius: 3px;
            }}
            QPushButton:focus {{
                border: 2px solid {interactive()};
            }}
        """)
